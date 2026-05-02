---
title: "RAG in Production: What Breaks, What to Measure, and How I Monitor It"
description: "Building RAG is the easy part. Keeping it reliable in production requires observability, automated testing, and alerting. Here's the full monitoring stack I built for Jarvis."
date: 2026-04-26
tags: ["rag", "observability", "langchain", "langfuse", "langsmith", "llm", "production", "monitoring"]
categories: ["Technology", "AI", "Engineering"]
draft: false
---

*Everyone can build RAG. Keeping it honest in production is a different problem.*

A pattern I keep seeing: teams ship a RAG pipeline, it works beautifully in testing, and three months later users are quietly losing trust in the answers. No alarms fired. No errors logged. The system just drifted. I've been building Jarvis, a production AI assistant on Google Cloud Run, and the RAG pipeline - Jarvis Vault - is its most technically demanding component. This post is about every monitoring, alerting, and testing decision I made, and why.

---

## The failure modes nobody shows in tutorials

RAG demos work because the demo corpus is static, the questions are cherry-picked, and nobody asks what happens three weeks later. Production breaks differently:

**Retrieval quality drifts.** Your documents get updated. Chunks become stale. The top-k results that worked at launch return off-context noise by week eight. The system still responds - confidently, but wrongly. No 500 error. No alert. Silent degradation.

**Context-answer misalignment.** The LLM receives irrelevant context and still generates an answer. Hallucination is invisible unless you measure citation grounding explicitly.

**Cost creeps.** Long context windows, expensive embedding calls, multiple LLM hops - costs compound. Without per-query cost tracking, you discover the problem on your cloud bill.

**Error patterns go unclassified.** A retrieval timeout looks the same in logs as a parsing failure unless you build a taxonomy. Fixing "RAG is broken" requires knowing *how* it's broken.

**Users don't complain - they leave.** Without an explicit feedback mechanism wired to your pipeline, you have no signal that answers are getting worse until users stop using the feature.

These are not theoretical risks. They are the reasons I built a full observability layer before shipping Jarvis Vault to real users.

---

## The architecture: four observability layers

![Architecture Section](/images/RAG_Query.png)

At a high level, the pipeline does three things: retrieve → filter → answer. Everything else is instrumentation on top of that.
The entire monitoring stack sits on top of a single pipeline. Before diving into each section, here is how the four layers relate:

```
┌─────────────────────────────────────────────────────────────────┐
│  User query                                                     │
│      │                                                          │
│      ▼                                                          │
│  rag.retrieve.fuse  ──────── Layer 1: Span emitted              │
│    ├─ rag.retrieve.vector  (HyDE embedding → pgvector)          │
│    └─ rag.retrieve.bm25   (tsvector full-text)                  │
│      │                                                          │
│      ▼                                                          │
│  rag.filter  ─────────────── Layer 1: Span emitted              │
│  (contextual compression)                                       │
│      │                                                          │
│      ▼                                                          │
│  rag.answer.llm  ─────────── Layer 1: Span emitted              │
│  (structured output + citations)                                │
│      │                                                          │
│      ▼                                                          │
│  Streaming response to user                                     │
│      │                                                          │
│      ▼  (background, off critical path)                         │
│  faithfulness judge  ─────── Layer 1: Score ingested            │
│                                                                 │
│  Every span →  Layer 2: Aggregator (per-user, in-memory)        │
│             →  Layer 3: Langfuse / LangSmith (if opted in)      │
│                                                                 │
│  Every 5 min →  Firestore flush  →  Layer 4: SRE alerter        │
└─────────────────────────────────────────────────────────────────┘
```

The four layers are runtime observability. Dashboard and CI sit outside the runtime path.

### Layer 1 - Span tracing (the C2 contract)

Every operation in the RAG pipeline emits a span. The contract is frozen: `trace_id`, `span_id`, `name`, `start_ts`, `end_ts`, `duration_ms`, `input`, `output`, `metadata`, `error`. Never renamed. Additive only.

Each span captures not just duration but the *substance* of what happened:

- `rag.retrieve.vector`: `{query, k, n_results, similarity_threshold, mode: "hyde"}`
- `rag.retrieve.bm25`: `{query, k, n_results}`
- `rag.retrieve.fuse`: `{query, k, mode: "hybrid-rrf-hyde"}` - parent span for the full retrieval pass
- `rag.filter`: `{n_chunks_in, n_to_filter, n_pinned, n_llm_kept}`
- `rag.answer.llm`: `{n_chunks, sufficient, n_citations, tokens_in, tokens_out, cost_usd}`
- `rag.answer.validate`: `{sufficient, n_citations, answer_chars}` - or error type on refusal/invalid citation

On every span exit, the span is routed to three destinations simultaneously: the in-process metrics aggregator, and (if the user has opted in) either Langfuse or LangSmith for detailed trace inspection.

### Layer 2 - Per-user metrics aggregation

Spans flow into an in-process aggregator that buffers raw samples per user. Every five minutes it flushes a merged snapshot to Firestore under `jarvis-metrics/{date}/users/{user_id}`.

The flush uses a read-then-merge strategy: the aggregator reads whatever was already written today, adds the in-memory buffer to it, and writes the merged result back. This means a Cloud Run scale-to-zero restart - which wipes all in-memory state - does not discard the day's earlier data. After a confirmed write, in-memory buffers are cleared so samples are never double-counted on the next flush.

All metrics are tracked per user from the start. Different users' data never mingles.

### Layer 3 - Deep trace backends (Langfuse / LangSmith)

The aggregator tells you *that* something degraded. Langfuse or LangSmith tell you *which query* caused it. Users opt in per-account via the Profile page. The dashboard shows a tracing banner linking directly to the chosen backend, so a spike on a metric card has a one-click path to the individual trace.

### Layer 4 - SRE alerting with cooldown

After each flush, the alerting module checks four thresholds and fires a Gmail SMTP email on any breach. A per-day cooldown - keyed on the combination of date, user, and breach pattern - prevents alert fatigue on repeated flushes. Different breach patterns on the same day each trigger exactly once.

| Threshold | Default | Override env var |
|---|---|---|
| P95 latency | > 10,000 ms | `ALERT_P95_LATENCY_MS` |
| Refusal rate | > 5% | `ALERT_ERROR_RATE` |
| Error rate | > 5% | `ALERT_ERROR_RATE` |
| Daily cost | > $1.00 | `ALERT_DAILY_COST_USD` |

The alerter fails silently if credentials are absent - it never crashes the flush loop.

---

## The observability dashboard

![Observability Section](/images/rag_dashboard.png)

The dashboard lives at `/admin/observability`. Every metric card uses consistent colour semantics so you can scan the page in two seconds and know whether anything needs attention. Clicking any card opens a 10-day trend chart in a modal - giving you direction, not just a snapshot.

The dashboard fetches from `/api/admin/metrics`, which flushes the in-process buffer before reading Firestore, so the view reflects the current minute's queries rather than the last scheduled flush.

The rest of this post walks through each of the seven sections in dashboard order, with the metrics, what they mean, and what action each signal points to.

---

## Section 1 - Performance

*Screenshot: Performance section showing P50, P95, and stage breakdown bar*

![Performance Section](/images/rag_performance.png)

This section answers: *how long are users waiting?*

| Metric | What it tells you |
|---|---|
| `rag.latency.p50_ms` | Typical response time - the experience for the median user |
| `rag.latency.p95_ms` | Tail latency - the worst 5% that drive support tickets |
| `rag.latency.sample_size` | Number of vault queries today - context for interpreting the above |
| `rag.latency.breakdown.retrieval_ms` | Mean time in the retrieval stage |
| `rag.latency.breakdown.filter_ms` | Mean time in contextual compression |
| `rag.latency.breakdown.llm_ms` | Mean time in LLM answer generation |

**Colour thresholds:** green below 3 s, yellow below 8 s, red above 8 s.

Below the P50/P95 cards, an inline stage breakdown bar shows retrieval, filter, and LLM time as proportional coloured segments. This is the fastest way to diagnose where latency is being spent - if the LLM bar dominates, your context window is too large or your model is slow; if retrieval dominates, your pgvector index may need tuning.

The span tree for a hybrid+HyDE query looks like this:

```
rag.retrieve.fuse          (parent: full retrieval pass)
  ├─ rag.retrieve.vector   (HyDE embedding → cosine similarity on pgvector)
  └─ rag.retrieve.bm25     (raw query → tsvector full-text on PostgreSQL)
rag.filter                  (contextual compression: LLM re-ranks chunks)
rag.answer.llm              (structured output generation with citations)
```

HyDE generation and BM25 search run concurrently via `asyncio.gather`, so the latency cost of generating a hypothetical passage is amortised - it runs in parallel with BM25, which uses the raw query text.

---

## Section 2 - Retrieval Quality

*Screenshot: Retrieval Quality section showing Top-1 Similarity and Cited Chunk Rank cards*

![Retrieval Quality Section](/images/rag_retrieval.png)

This section answers: *are the right chunks being found and ranked correctly?*

| Metric | What it tells you |
|---|---|
| `rag.retrieval.top1_similarity` | Average cosine similarity of the best-ranked chunk - measures how well the corpus matches query space |
| `rag.retrieval.cited_rank_avg` | Average rank of chunks the LLM actually cited - 1 is ideal; high values mean the best chunk was buried |

**Colour thresholds:**
- Top-1 similarity: green above 0.65, yellow above 0.40, red below 0.40
- Cited chunk rank: green at rank ≤ 2, yellow at rank ≤ 3.5, red above 3.5

`top1_similarity` is computed from the raw query embedding (not the HyDE embedding) so it reflects how close the retrieval system actually got to the question, independent of the hypothetical passage. A declining `top1_similarity` over the 10-day trend chart is a leading indicator of corpus drift - documents are aging away from the query distribution before the refusal rate has time to climb.

`cited_rank_avg` measures whether the LLM is using the chunks the retriever ranked highest. If the LLM consistently cites chunks ranked 3–5 rather than 1–2, your retrieval ordering is wrong. This metric is tracked by recording the 1-based citation indices the LLM actually used in its structured output, then computing the mean.

The retrieval system uses hybrid search: cosine similarity on pgvector combined with BM25 full-text search on PostgreSQL's native `tsvector`, fused via Reciprocal Rank Fusion:

```
RRF score = 1/(60 + vector_rank) + 1/(60 + bm25_rank)
```

Pure vector search fails on proper nouns, product codes, dates, and any token where semantic similarity is a poor proxy for lexical relevance. The BM25 arm catches those cases. The `rag.retrieve.fuse` span records candidate pool sizes from both arms before fusion - if BM25 is returning zero candidates consistently, something is wrong with your `tsvector` indexing.

---

## Section 3 - Answer Quality

*Screenshot: Answer Quality section showing Citation Coverage, Refusal Rate, and Grounded Score cards*

![Answer Quality Section](/images/rag_answer_quality.png)

This section answers: *did the LLM actually use the retrieved context, and did it stay within it?*

| Metric | What it tells you |
|---|---|
| `rag.citation.coverage` | Fraction of answers with at least one grounded citation |
| `rag.refusal.rate` | Fraction of queries where context was insufficient to answer |
| `rag.answer.grounded_score` | LLM judge score measuring whether answers stay within retrieved context |

**Colour thresholds:**
- Citation coverage: green above 85%, yellow above 65%, red below 65%
- Refusal rate: green below 10%, yellow below 25%, red above 25%
- Grounded score: green above 85%, yellow above 65%, red below 65%

The answer LLM returns a structured object parsed with Pydantic:

```python
class VaultAnswer(BaseModel):
    answer: str           # Text with [n] citation markers
    citations: List[int]  # 1-based indices of chunks actually used
    sufficient: bool      # False triggers a soft refusal
```

`validate_citations()` strips any indices that do not exist in the retrieved set. Citation hallucination is a real failure mode - the model fabricates `[7]` when only chunks 1–4 were retrieved. Each stripped citation logs a `citation_validation_fail` error and records a span so it is traceable in Langfuse/LangSmith.

A `sufficient=False` response increments `rag.refusal.rate`. Citations are suppressed on refusals - showing sources when the context was judged insufficient would be misleading. A rising refusal rate often means your corpus has drifted from the query distribution: the document that should answer the question is either not indexed or the chunks are stale.

**The faithfulness judge.** After each vault answer is streamed to the user, a background task fires an LLM judge call: *"Does this answer make only claims directly supported by the retrieved excerpts?"* The judge returns a score from 0.0 to 1.0. This runs entirely off the critical path - `asyncio.create_task()`, never awaited by the streaming response - so it adds zero latency to the user experience. Enable it with `RAG_ENABLE_FAITHFULNESS_JUDGE=true` (on by default; disable to avoid judge costs on very low-volume deployments).

The three metrics triangulate on answer quality from different angles:
- `citation.coverage` measures *whether* context was cited.
- `answer.grounded_score` measures *how faithfully* it was used.
- `refusal.rate` measures *when* the model judged the context too weak to answer at all.

---

## Section 4 - Contextual Compression (the chunk filter)

![Answer Quality Section](/images/rag_filter.png)

Vector search retrieves a candidate set. Not all of it is relevant. A naive pipeline sends everything to the answer LLM, burning tokens and injecting noise. Jarvis Vault runs a contextual compression step - `chunk_filter.py` - between retrieval and answer generation.

The algorithm:

1. Extract keywords (4+ characters, after stopword removal) from the question.
2. **Pin** any chunk containing a keyword - these always survive, regardless of LLM verdict.
3. Send remaining chunks to the LLM in one batch: "Which of these are relevant to answering this question?"
4. Merge pinned + LLM-kept chunks, preserving original order.

The filter span records `{n_chunks_in, n_to_filter, n_pinned, n_llm_kept}`. Over time this gives you a picture of how much noise is entering the pipeline and how much the compressor is catching. The filter latency in the stage breakdown bar reflects this step. If the filter is consuming most of your latency budget, you are retrieving too many candidate chunks - reduce `RAG_MAX_CHUNKS_PER_QUERY`.

If the filter LLM call fails, the pipeline falls back to all chunks. Never fail closed on retrieval - a degraded answer beats no answer.

---

## Section 5 - Cost & Efficiency

*Screenshot: Cost & Efficiency section showing all four cost cards*

![Cost & Efficiency Section](/images/rag_cost_efficiency.png)

This section answers: *what are you paying, and are you getting value for it?*

| Metric | What it tells you |
|---|---|
| `rag.cost.daily_usd` | Total daily spend - budget tracking |
| `rag.cost.per_query_usd` | Unit economics - average cost per vault answer |
| `rag.cost.per_successful_usd` | Cost per sufficient answer - what you actually pay for a useful response |
| `rag.cost.per_grounded_usd` | Cost per cited and sufficient answer - the tightest quality bar |

Cost ratios (`per_successful`, `per_grounded`) are OpenAI only - they rely on the OpenAI callback that captures per-call spend, which does not fire for Gemini models. These cards show `-` when a Gemini model is in use. Cost metrics depend on provider-level callbacks; some are unavailable on Gemini.

The distinction between `per_query`, `per_successful`, and `per_grounded` is intentional. If your `per_query` cost is $0.003 but your `per_successful` cost is $0.012, it means only one in four queries produces a sufficient answer - the other three are refusals that still consumed retrieval and filter costs. That gap is the signal to fix your corpus, not to optimise prompts.

---

## Section 6 - Token Volume

*Screenshot: Token Volume section showing Tokens In, Tokens Out, and Tokens/Successful*

![Token Volume Section](/images/rag_token_volume.png)

| Metric | What it tells you |
|---|---|
| `rag.tokens.daily_in` | Total prompt tokens today - context window and capacity planning |
| `rag.tokens.daily_out` | Total completion tokens today - capacity planning |
| `rag.tokens.per_successful` | Average total tokens per sufficient answer - token efficiency signal |

Token growth is the leading indicator of future cost growth. Token counts are available across all model providers (OpenAI and Gemini). `tokens.per_successful` is the token equivalent of `cost.per_successful` and works even when cost tracking is unavailable.

A rising `tokens_in` with a flat or falling `tokens.per_successful` is a good sign - you are handling more queries without inflating context per query. The reverse - rising `tokens_in` with rising `tokens.per_successful` - means your retrieved contexts are getting longer, which usually points to chunks being too large or too many chunks surviving the filter.

---

## Section 7 - User Feedback

*Screenshot: User Feedback section showing Satisfaction score and Follow-up Rate, with 👍👎 buttons visible in a chat below*

![User Feedback Section](/images/rag_user_feedback.png)

This section answers: *did the user find the answer useful?*

All the metrics above are derived from the pipeline itself. They tell you how the system behaved. They do not tell you whether the user found the answer useful. Two signals close that gap.

| Metric | What it tells you |
|---|---|
| `rag.user.satisfaction_score` | Fraction of 👍 from explicit ratings - direct quality signal |
| `rag.user.rated_count` | Number of responses rated today |
| `rag.query.follow_up_rate` | Fraction of vault queries semantically similar to the previous one - implicit retry signal |

**Colour thresholds:**
- Satisfaction: green above 80%, yellow above 60%, red below 60%
- Follow-up rate: green below 15%, yellow below 35%, red above 35% (high follow-up = users are not getting complete answers)

**Explicit ratings.** After every vault response, 👍/👎 buttons appear inline, tied to the specific trace ID. A click fires `POST /chat/feedback`, which records the score in Firestore against the matching message and feeds it into the aggregator. A satisfaction score below 60% is a red flag even if citation coverage looks healthy - the system is producing grounded answers that users still find unhelpful.

**Implicit follow-up detection.** If a user immediately asks a closely related question, it is a soft signal the previous answer was incomplete. The system computes cosine similarity between successive query embeddings (reusing embeddings already generated for retrieval - zero extra API cost). A similarity score at or above 0.70 flags the query as a follow-up. Time windows are deliberately ignored: voice users and fast typists would produce false positives with any time-based threshold. 0.70 was empirically chosen to balance semantic similarity vs false positives.

---

## Section 8 - Errors Today

*Screenshot: Errors Today section showing the error taxonomy table with counts*

![Errors Today Section](/images/rag_errors.png)

Unclassified errors are useless for debugging. Jarvis Vault uses a typed enum:

```python
class RagErrorType(str, Enum):
    embedding_failure              # Embedding model unreachable
    retrieval_timeout              # pgvector query timed out
    llm_timeout                   # LLM inference timed out
    llm_rate_limit                # OpenAI 429
    structured_output_parse_fail  # Pydantic validation of LLM output failed
    citation_validation_fail      # LLM cited a non-existent chunk index
    refusal_due_to_insufficient_context  # Out-of-distribution query
    ingest_extraction_fail        # Document reader failed at upload time
    unknown
```

Each error type tells you *where* in the pipeline the problem is. A spike in `structured_output_parse_fail` means the answer LLM is not following its output schema - inspect the prompt. A spike in `citation_validation_fail` means the model is hallucinating citation indices - that warrants a retrieval quality audit, not a prompt fix.

The dashboard shows a green checkmark when there are no errors today, and a sorted list by count when there are.

---

## The 10-day trend view

*Screenshot: Trend modal open on a metric card, showing a Chart.js line chart*

![10-day Trend Chart](/images/rag_latency_p50.png)
![10-day Trend Chart](/images/rag_latency_p95.png)

Every metric card on the dashboard is clickable. Clicking opens a modal with a 10-day line chart for that metric, pre-fetched in the background so the first click is instant.

This is the difference between a snapshot and a monitoring tool. A P95 of 6,800 ms in isolation is ambiguous - is that good or bad relative to last week? The trend chart answers immediately: flat, climbing, or falling.

The chart uses the same colour semantics as the card. A declining `top1_similarity` trend is worth more attention than a single-day reading below threshold - it means retrieval is getting structurally worse, not just noisy.

Trend data is read directly from Firestore across the past 10 days' per-user metric documents. Days with no vault queries show as gaps in the chart.

---

## Testing: hard gates in CI

Observability means nothing if the code that produces the signals is wrong. The CI pipeline has two hard gates on every pull request.

![CI](/images/rag_ci.png)

**Unit test gate (T0).** Runs `pytest` with no live API calls - everything is mocked. Covers:

- `test_alerting.py`: 11 tests across threshold checks, SMTP emission, cooldown logic, and Firestore failure handling
- `test_chunk_filter.py`: keyword extraction, pinning logic, LLM fallback on failure
- `test_retriever.py`: 1-based citation index assignment, prompt format, citations payload serialisation
- `test_answer.py`: structured output parsing, citation validation (valid / partial / fully invalid)

If any unit test fails, the PR cannot merge.

**Eval regression gate.** A separate job runs a checked-in golden evaluation set against the actual retrieval and answer pipeline. If the accuracy drops by more than 3 percentage points relative to the main branch baseline, the job fails and posts a detailed report as a PR comment. This catches regressions that unit tests can't - changes to chunking parameters, prompt rewrites, similarity threshold adjustments that look correct in isolation but degrade end-to-end quality.

The eval gate comment on every PR makes retrieval quality a visible, reviewable artefact rather than an invisible assumption.

---

## What I would add next

The current stack covers the full lifecycle from retrieval through user feedback. A few items are on the roadmap:

**Chunk freshness tracking.** Tag each chunk with its ingest timestamp. Track the age distribution of chunks appearing in the top-k. Rising mean chunk age for a user's corpus is a leading indicator of stale retrieval - it will surface here before it shows up in the refusal rate.

**Query length distribution.** Short queries (under 50 characters) tend to have lower retrieval quality - they are ambiguous and resist HyDE expansion. Bucketing queries by length and correlating with satisfaction and citation coverage would reveal whether short-query handling needs targeted improvement.

**Embedding drift score.** Compare the centroid of today's query embeddings against a stored baseline. Statistical drift (Mahalanobis distance or cosine divergence) is a leading indicator that the query distribution has shifted away from the corpus. Meaningful only over weeks of data.

**Per-document retrieval heatmap.** Track which documents are being retrieved and cited most frequently. Documents that are retrieved often but cited rarely are low-quality matches - candidates for re-chunking or removal.

---

## The core lesson

Building RAG for a demo takes an afternoon. The retrieval works. The answers look reasonable. Everyone is impressed.

Building RAG for production means accepting that retrieval quality is a continuous variable, not a switch. It drifts. Context relevance slips. Costs compound. Errors accumulate without classification. None of these announce themselves - they require instrumentation.

The stack described here - span tracing with a frozen contract, per-user metrics aggregation with a read-then-merge flush, structured error taxonomy, SRE alerting with cooldown, a seven-section dashboard with 10-day trend charts, explicit user feedback wired to trace IDs, semantic follow-up detection, and an LLM-as-judge faithfulness scorer - did not emerge all at once. It emerged because each production incident taught me exactly which signal I was missing.

If you are shipping RAG beyond a demo, build the instrumentation before the incidents teach you why you need it.

---

*Jarvis is a personal AI assistant I have been building on Google Cloud Run, with integrations for Gmail, Google Calendar, OneDrive, and a full RAG pipeline. The observability stack described here is live and handling real queries.*

#RAG #LLMOps #Observability #AIEngineering #LangChain #Langfuse #ProductionAI #MLOps #TechLeadership
