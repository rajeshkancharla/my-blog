---
title: "RAG in Production, Part 2: The User-Facing Half - Cost, Feedback, Errors, and Test Gates"
description: "Part 2 of the RAG monitoring deep-dive: cost-quality tradeoffs, token efficiency, explicit and implicit user feedback, the error taxonomy, 10-day trend charts, and the CI test gates that keep the signals honest."
date: 2026-05-09
tags: ["rag", "observability", "langchain", "langfuse", "langsmith", "llm", "production", "monitoring"]
categories: ["Technology", "AI", "Engineering"]
draft: false
---

<br>

## Part 2 of 2 - Pipeline metrics show how the system behaved. The signals here show whether it mattered.

*Cost compounds quietly. Users don't explain why they stopped asking questions. Errors without a taxonomy are just noise. These are the observability layers that most RAG dashboards skip.*

---

### Picking up from Part 1

[Part 1](/posts/rag-monitoring-production-part1) covered the architecture, span tracing, and the four pipeline sections of the Vault dashboard: Performance, Retrieval Quality, Answer Quality, and Contextual Compression.

Those sections cover what the system did - how fast it responded, how well retrieval ranked, whether the LLM stayed within its evidence. They are about the pipeline's behaviour.

This part covers what that behaviour cost, what users thought of it, and what broke. Then the 10-day trend view that turns a snapshot dashboard into a real monitoring tool, and the CI gates that ensure the signals themselves stay correct.

---

### Section 5 - Cost & Efficiency

*Screenshot: Cost & Efficiency section showing all four cost cards*

![Cost & Efficiency Section](/images/rag_cost_efficiency.png)

Raw cost is straightforward to track. The more useful question is cost *per useful answer*.

| Metric | What it tells you |
|---|---|
| `rag.cost.daily_usd` | Total daily spend - shown alongside yesterday's cost for comparison |
| `rag.cost.per_query_usd` | Average cost per vault query |
| `rag.cost.per_successful_usd` | Cost per sufficient answer - what is actually paid for a useful response |
| `rag.cost.per_grounded_usd` | Cost per cited and sufficient answer - the tightest quality bar |

Cost ratios (`per_successful`, `per_grounded`) are OpenAI only - they rely on the OpenAI callback that captures per-call spend, which does not fire for Gemini models. These cards show `-` when a Gemini model is in use. `rag.cost.daily_usd` is the one card that also shows yesterday's spend as a sub-label, giving an immediate day-over-day comparison without opening the trend chart.

The distinction between `per_query`, `per_successful`, and `per_grounded` is intentional.

> *A `per_query` cost of $0.003 with a `per_successful` cost of $0.012 means only one in four queries is producing a sufficient answer. The other three are refusals that still consumed retrieval and filter costs. That gap points to a corpus problem - not a prompt problem.*

---

### Section 6 - Token Volume

*Screenshot: Token Volume section showing Tokens In, Tokens Out, and Tokens/Successful*

![Token Volume Section](/images/rag_token_volume.png)

Token growth is the leading indicator of future cost growth. Token counts are available across all model providers - OpenAI and Gemini both.

| Metric | What it tells you |
|---|---|
| `rag.tokens.daily_in` | Total prompt tokens today - context window and capacity planning |
| `rag.tokens.daily_out` | Total completion tokens today - capacity planning |
| `rag.tokens.per_successful` | Average total tokens per sufficient answer - token efficiency signal |

`tokens.per_successful` is the token equivalent of `cost.per_successful`. It works even when cost tracking is unavailable - useful during Gemini deployments where the per-call cost callback does not fire.

Two patterns worth watching:

A rising `tokens_in` with a flat or falling `tokens.per_successful` is a healthy sign - more queries are being handled without inflating context per query.

The reverse - rising `tokens_in` with rising `tokens.per_successful` - means retrieved contexts are getting longer. That usually points to chunks being too large, or too many chunks surviving the filter.

---

### Section 7 - User Feedback

*Screenshot: User Feedback section showing Satisfaction score and Follow-up Rate, with 👍👎 buttons visible in a chat below*

![User Feedback Section](/images/rag_user_feedback.png)

Everything in Sections 1–6 comes from the pipeline itself. Those metrics cover how the system behaved. They do not cover whether the user found the answer useful.

Three signals close that gap.

| Metric | What it tells you |
|---|---|
| `rag.user.satisfaction_score` | Fraction of 👍 from explicit ratings - direct quality signal |
| `rag.user.rated_count` | Number of responses rated today - low count means users aren't engaging with the buttons at all |
| `rag.query.follow_up_rate` | Fraction of vault queries semantically similar to the previous one - implicit retry signal |

**Colour thresholds:**
- Satisfaction: green above 80%, yellow above 60%, red below 60%
- Follow-up rate: green below 15%, yellow below 35%, red above 35%

**Explicit ratings.** After every vault response, 👍/👎 buttons appear inline, tied to the specific trace ID. A click fires `POST /chat/feedback`, which records the score in Firestore against the matching message and feeds it into the aggregator.

A satisfaction score below 60% is a red flag even if citation coverage looks healthy - the system is producing grounded answers that users still find unhelpful. A very low `rated_count` is also a signal in itself. When users are not engaging with the feedback buttons at all, responses may be getting abandoned before they are read.

**Implicit follow-up detection.** A closely related follow-up question immediately after a response is a soft signal the previous answer was incomplete. The system computes cosine similarity between successive query embeddings - reusing embeddings already generated for retrieval, so there is zero extra API cost. A similarity score at or above 0.70 flags the query as a follow-up. Time windows are deliberately ignored: voice users and fast typists would produce false positives with any time-based threshold. 0.70 was empirically chosen to balance semantic sensitivity against false positives.

**LLM-as-judge faithfulness.** The `rag.answer.grounded_score` covered in Section 3 of Part 1 belongs to Answer Quality, not User Feedback - but it is the third signal in the triangulation. Explicit ratings measure *whether users agreed*. Follow-up rate measures *whether users needed more*. Grounded score measures *whether the answer earned their agreement by staying within the evidence*.

---

### Section 8 - Errors Today

*Screenshot: Errors Today section showing the error taxonomy table with counts*

![Errors Today Section](/images/rag_errors.png)

Unclassified errors are useless for debugging. An error logged as "something went wrong" gives no indication of where in the pipeline to look or what to change. The Vault uses a typed enum:

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

Each error type identifies *where* in the pipeline the problem is. A spike in `structured_output_parse_fail` means the answer LLM is not following its output schema - the prompt needs inspection. A spike in `citation_validation_fail` means the model is hallucinating citation indices - that warrants a retrieval quality audit, not a prompt fix.

The dashboard shows a green checkmark when there are no errors today, and a sorted list by count when there are. Error counts also trigger SRE alerts - a sustained error rate above 5% fires a Gmail notification with the full metrics snapshot, as described in the alerting layer in Part 1.

---

### The 10-day trend view

*Screenshot: Trend modal open on a metric card, showing a Chart.js line chart*

![10-day Latency Trend - P50](/images/rag_latency_p50.png)
![10-day Latency Trend - P95](/images/rag_latency_p95.png)

Every metric card on the dashboard is clickable. Clicking opens a modal with a 10-day line chart for that metric, pre-fetched in the background so the first click is instant.

A single-day reading is a snapshot. Ten days of readings is a monitoring tool. A P95 of 6,800 ms in isolation is ambiguous - the trend chart shows immediately whether that number is flat, climbing, or recovering from a spike.

The chart uses the same colour semantics as the card. A declining `top1_similarity` trend carries more diagnostic weight than a single-day reading below threshold - it means retrieval is getting structurally worse, not just experiencing a noisy day. A `satisfaction_score` falling week over week - even if still in the yellow band - is a stronger signal than a single low reading.

Trend data is read directly from Firestore across the past 10 days' per-user metric documents. Days with no vault queries show as gaps in the chart, making it immediately obvious whether a metric dropped or whether the system simply was not used that day.

---

### Testing - hard gates in CI

Observability means nothing if the code producing the signals is wrong.

![CI gates](/images/rag_ci.png)

The CI pipeline has two hard gates on every pull request.

**Unit test gate.** Runs `pytest` with no live API calls - everything is mocked. Covers:

- `test_alerting.py`: 11 tests across threshold checks, SMTP emission, cooldown logic, and Firestore failure handling
- `test_chunk_filter.py`: keyword extraction, pinning logic, LLM fallback on failure
- `test_retriever.py`: 1-based citation index assignment, prompt format, citations payload serialisation
- `test_answer.py`: structured output parsing, citation validation (valid / partial / fully invalid)

If any unit test fails, the PR cannot merge.

**Eval regression gate.** A separate job runs a checked-in golden evaluation set against the actual retrieval and answer pipeline. If accuracy drops by more than 3 percentage points relative to the main branch baseline, the job fails and posts a detailed report as a PR comment.

This catches regressions that unit tests cannot - changes to chunking parameters, prompt rewrites, similarity threshold adjustments that look correct in isolation but degrade end-to-end quality. The eval gate comment on every PR makes retrieval quality a visible, reviewable artefact rather than an invisible assumption.

---

### What I would add next

The current stack covers the full lifecycle from retrieval through user feedback. A few items are on the roadmap.

**Chunk freshness tracking.** Tag each chunk with its ingest timestamp. Track the age distribution of chunks appearing in the top-k. Rising mean chunk age is a leading indicator of stale retrieval - it surfaces before the refusal rate has time to climb.

**Query length distribution.** Short queries (under 50 characters) tend to have lower retrieval quality - they are ambiguous and resist HyDE expansion. Bucketing queries by length and correlating with satisfaction and citation coverage would reveal whether short-query handling needs targeted work.

**Embedding drift score.** Compare the centroid of today's query embeddings against a stored baseline. Statistical drift is a leading indicator that the query distribution has shifted away from the corpus. Only meaningful over weeks of data.

**Per-document retrieval heatmap.** Track which documents are retrieved and cited most frequently. Documents retrieved often but cited rarely are low-quality matches - candidates for re-chunking or removal.

**Explicit Δ% on every card.** Currently, `rag.cost.daily_usd` shows yesterday's cost as a sub-label. Extending that pattern to every card would surface trend signals directly on the dashboard without needing to open the trend modal.

---

### The core lesson

Building RAG for a demo takes an afternoon. The retrieval works. The answers look reasonable. The demo goes well.

Building RAG for production means accepting that retrieval quality is a continuous variable, not a switch. It drifts. Context relevance slips. Costs compound. Errors accumulate without classification. None of these announce themselves - they require instrumentation to surface.

The stack described across these two posts - span tracing with a frozen contract, per-user metrics aggregation with a read-then-merge flush, structured error taxonomy, SRE alerting with cooldown, an eight-section dashboard with 10-day trend charts, explicit user feedback wired to trace IDs, semantic follow-up detection, an LLM-as-judge faithfulness scorer, and CI gates on both unit correctness and end-to-end retrieval quality - did not emerge all at once. It emerged because each production incident revealed exactly which signal was missing.

> *Build the instrumentation before the incidents make it obvious why it was needed. By then, the trust is already harder to recover than the signal would have been to build.*

---

*This is a personal AI assistant I have been building on Google Cloud Run, with integrations for Gmail, Google Calendar, OneDrive, and a full RAG pipeline. The observability stack described here is live and handling real queries.*

#RAG #LLMOps #Observability #AIEngineering #LangChain #Langfuse #ProductionAI #MLOps #TechLeadership
