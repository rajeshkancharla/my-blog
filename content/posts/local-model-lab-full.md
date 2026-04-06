---
title: "Systematic Comparison of Small Language Models"
date: 2026-04-06
draft: false
tags: ["AI", "Cloud Architecture", "Data Engineering", "Tech Leadership", "AI Bias"]
description: "Part 1 of the 3 part engineering journey that performs a systematic comparison of small language models on consumer hardware"
---



<br>

## Part 1 of 3 - I built a personal AI assistant. The API bill sent me down a rabbit hole.

*How a billing problem with Jarvis led to a rigorous offline benchmarking study of four small language models - and the infrastructure battle I did not expect to fight.*

---

### The origin

I have been building Jarvis - a personal AI assistant that connects to my Google Calendar, Gmail, OneDrive, and Google Drive. One interface. Ask it anything about your schedule, your files, your contacts. No switching apps. No copy-pasting context.

The centrepiece of Jarvis is a RAG pipeline - Retrieval-Augmented Generation. It lets me upload documents to a personal knowledge base and query them conversationally. Financial statements. Medical records. Work documents. Travel bookings. All of it searchable through a single assistant.

It worked beautifully. And it was quietly burning money.

> *"Every document I uploaded to test a feature, every query I ran while debugging - even the broken ones - was generating API calls to a paid embedding model. The meter ran whether the code worked or not."*

Every chunk of text processed, every semantic search during development, every iteration on retrieval quality - all of it hitting a commercial embedding API at cost-per-token. For production use serving real users, this is a justified expense. But during development, when you are uploading the same test files repeatedly and running dozens of queries to tune chunking strategies, it becomes an engineering tax on iteration speed.

Beyond cost, there was a more uncomfortable realisation. Jarvis is designed to work with personal files. Every test with real documents meant that data was leaving my machine and travelling to a commercial API endpoint. Even with strong data processing agreements in place, that is a privacy exposure during development that compounds with every run.

The question became obvious: could I run inference entirely locally? No API calls. No tokens leaving my machine. No bill for development work.

---

### The model selection problem

A quick search turned up dozens of Small Language Models in the 3B to 7B parameter range - compact enough to run on consumer hardware, capable enough to handle real tasks. Meta's Llama. Microsoft's Phi. Google's Gemma. Alibaba's Qwen. Each with different architectures, training philosophies, and benchmark claims.

I had seen this pattern before at work. When evaluating any technical component, you do not pick the one with the best marketing page. You define your requirements, build a test harness, and measure. Language models should be no different. That thinking became the foundation of **local-model-lab**.

---

### The hardware reality check

The test machine is a Lenovo Yoga - a consumer laptop. Intel Arc GPU with 6.7GB available VRAM, 15.4GB system RAM. The kind of hardware a knowledge worker carries, a clinic deploys at a reception desk, or a field engineer takes on-site. Not an A100. Not a developer workstation. A realistic edge deployment device.

Getting GPU-accelerated inference working on this machine was the first engineering problem - and the most instructive one. Intel Arc is not NVIDIA. The standard path - CUDA - does not apply. Ollama has no Intel Arc backend on Windows. The only viable path was Vulkan, an open graphics API that Ollama supports experimentally.

> **Finding #1 - The silent failure that shapes all benchmarking**
>
> Ollama silently falls back to CPU if the Vulkan flag is not set before the server process starts. No error message. No warning. Just a 10x performance penalty with no explanation. The fix: set `OLLAMA_VULKAN=1` as a Windows User environment variable - not a Bash alias, not a VS Code setting - so the Windows tray app picks it up at login. This became a core methodological rule: **always verify GPU utilisation via `ollama ps` before recording a single benchmark number.** A model that appears to be running may be silently on CPU.

---

### Model selection - four companies, one constraint

The original brief suggested Llama 3.2, Phi-4, and Mistral 7B. Hardware reality forced a more disciplined selection process. Phi-4 at 14B parameters requires approximately 9GB of VRAM - more than available. Mistral 7B sits at the boundary and would cause a CPU/GPU split that contaminates benchmark comparisons. Qwen3.5:4b, initially selected, produced consistent timeouts on CPU even for simple prompts. Each elimination was documented as an engineering decision rather than treated as a failure.

The final four represent genuinely different organisations and training philosophies - all confirmed running at 100% GPU:

| Model | Company | Parameters | Size on disk |
|-------|---------|-----------|-------------|
| Llama 3.2:3b | Meta | 3B | 1.9 GB |
| Phi 3.5:3.8b | Microsoft | 3.8B | 2.0 GB |
| Gemma 3:4b | Google | 4B | 3.1 GB |
| Qwen 3:4b | Alibaba | 4B | 2.3 GB |

---

### Phase 1 - what the speed numbers revealed

The benchmark harness was built from scratch using `httpx` talking directly to the Ollama REST API - no SDK wrapper. Direct HTTP control gives nanosecond-precision server-side timing. Each model ran 8 prompts across 6 categories, repeated 3 times at temperature 0.0. Warmup inferences were excluded. Models were explicitly unloaded between runs using `keep_alive=0` - without this, two models resident simultaneously on constrained RAM degrades both.

<table>
  <thead>
    <tr>
      <th>Model</th>
      <th>Avg Tokens/s</th>
      <th>TTFT (ms)</th>
      <th>Latency (ms)</th>
      <th>Avg Tokens Generated</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background-color: #e6f4ea; font-weight: bold;">
      <td>🏆 llama3.2:3b</td>
      <td>13.4</td>
      <td>1,261</td>
      <td>13,072</td>
      <td>147</td>
    </tr>
    <tr>
      <td>gemma3:4b</td>
      <td>10.6</td>
      <td>1,647</td>
      <td>23,066</td>
      <td>216</td>
    </tr>
    <tr>
      <td>qwen3:4b</td>
      <td>10.2</td>
      <td>4,023</td>
      <td>36,434</td>
      <td>353</td>
    </tr>
    <tr>
      <td>phi3.5:3.8b</td>
      <td>9.8</td>
      <td>1,467</td>
      <td>32,814</td>
      <td>301</td>
    </tr>
  </tbody>
</table>

<br>

**Key findings:**

- **Llama wins every speed metric** - 40% faster token generation and 2.5x lower end-to-end latency than the slowest model, despite comparable parameter counts.

- **Qwen's 4-second TTFT does not improve with warmup.** It enters a thinking mode by default - generating internal chain-of-thought reasoning before responding. Powerful for hard problems. A UX dealbreaker for real-time applications where users expect immediate feedback.

- **Verbosity inflates latency independently of speed.** Qwen generates 353 tokens on average - 2.4x more than Llama's 147. A model that writes an essay when you asked for a sentence is not slower in the engineering sense - it is less controlled. Tokens-per-second and total latency must both be reported.

- **Temperature=0 is genuinely deterministic.** Token counts were bitwise identical across completely independent runs. This confirms the measurement apparatus is working and establishes the reproducibility baseline needed before any variance analysis.

- **Thermal throttling is real and cloud benchmarks never show it.** Under sustained CPU load, tokens/sec degraded 10–15% across all models. Edge hardware benchmarks must capture throttled performance, not peak performance.

---

> **Coming in Part 2:** Speed is necessary but not sufficient. Phase 2 tested whether these models can reliably produce valid JSON - the requirement for any production pipeline. The edge cases that emerged were more instructive than any benchmark table. Phi outputs JavaScript-style comments inside JSON. Qwen exhausts its token budget before closing the object. One model delivered 100% success across all schemas at all temperatures with zero retries.

`#LocalAI #MachineLearning #LLM #Python #EdgeAI #OpenSource #AIEngineering #Ollama #DataEngineering`

---

<br>
<br>

## Part 2 of 3 - Speed is not enough. I tested whether these models can actually be trusted in a production pipeline.

*Phase 2 of local-model-lab: structured JSON output enforcement, retry mechanisms, temperature variance, and the engineering surprises that no model card warns you about.*

---

### The context

In Part 1, I benchmarked four open-source Small Language Models on inference speed across 8 prompts and 3 repeats. Llama was the clear winner at 13.4 tokens/second. But for Jarvis - the personal AI assistant that motivated this project - raw speed is only one axis of evaluation.

Jarvis needs to parse structured data from documents. Extract entities. Return results in a predictable format that downstream code can consume. A model that generates fluent prose but cannot reliably return valid JSON is not a component I can trust in a production pipeline. Phase 2 tested exactly this - and the engineering surprises along the way were more valuable than the final success rate numbers.

---

### What was built

A JSON enforcement engine with four moving parts:

1. A **Pydantic v2 schema validation layer** that checks every model response against a defined output structure
2. A **retry mechanism** - if the model returns invalid JSON, it is reprompted once with the specific validation error included in the feedback
3. A **structured extraction pipeline** that handles real model misbehaviour, not just textbook cases
4. A **temperature sweep** across 0.0, 0.3, 0.7, and 1.0 with 5 repeats per cell to quantify how reliability changes as stochasticity increases

Four schemas of increasing structural complexity:

| Schema | Description |
|--------|-------------|
| `sentiment` | Flat - label + confidence score |
| `entities` | Named entity list with types |
| `code_review` | Nested - issues array with enums |
| `summary` | Structured - key points + metadata |

---

### The edge cases that required real engineering

These are not hypothetical edge cases. Every one appeared in production runs and required a specific fix.

**Phi 3.5 outputs JavaScript-style inline comments inside JSON.**
Responses like `{"label": "positive" // sentiment}` are not valid JSON - `json.loads()` throws immediately. A naive regex fix that strips `//.*` breaks on string literals containing `//`, such as URLs. The correct fix is a brace-depth and string-aware parser that only strips comments outside string boundaries.

**JSON Schema alone does not instruct small models.**
Providing a Pydantic schema definition in the prompt is insufficient. Models in the 3–4B range cannot reliably infer required fields from schema notation alone. Every field must be enumerated in plain English in the prompt alongside the schema. Schema is validation - it is not a substitute for a clear task description.

**Qwen's thinking mode consumes the entire token budget.**
By default, Qwen 3 generates internal chain-of-thought reasoning before its answer. At a 1,200 token budget, this internal monologue exhausts the allocation - the response field arrives empty or truncated before the JSON object closes. The `/no_think` prompt directive is unreliable when followed by other instructions. The correct fix is the `think: False` Ollama API parameter - not a prompt hack.

**Non-greedy regex destroys nested JSON.**
The pattern `r"\{.*?\}"` stops at the first closing brace - correct for flat objects but destroys nested structure. The correct implementation is a brace-depth scanner that increments on `{`, decrements on `}`, and respects string literals and escape sequences. This is not a minor optimisation - it is the difference between a JSON extractor that works and one that silently corrupts nested data.

---

### The temperature variance results

Five repeats per temperature per schema:

| Temperature | Description |
|-------------|-------------|
| 0.0 | Deterministic baseline |
| 0.3 | Light variance |
| 0.7 | Moderate stochasticity |
| 1.0 | High variance |

**Temperature effect on success rate:**

| Temperature | gemma3:4b | llama3.2:3b | phi3.5:3.8b |
|-------------|-----------|-------------|-------------|
| 0.0 | 100% | 100% | 100% |
| 0.3 | 100% | 100% | 100% |
| 0.7 | 100% | 95% | 100% |
| 1.0 | 100% | 100% | 100% |

*↻ = retry was needed. Temperature 0.0 consistently produced the highest structured output reliability.*

---

### Structured output success rates

**Success rates by model and schema:**

| Schema | gemma3:4b | llama3.2:3b | phi3.5:3.8b |
|--------|-----------|-------------|-------------|
| sentiment | 100% | 100% (1↻) | 100% |
| entities | 100% | 100% | 100% |
| code_review | 100% | 95% (4↻) | 100% (1↻) |
| summary | 100% | 100% | 100% |

<br>

<table>
  <thead>
    <tr>
      <th>Model</th>
      <th>Overall Success Rate</th>
      <th>Retries Needed</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background-color: #e6f4ea; font-weight: bold;">
      <td>🏆 gemma3:4b</td>
      <td>100%</td>
      <td>Zero</td>
      <td>All schemas · All temperatures</td>
    </tr>
    <tr>
      <td>phi3.5:3.8b</td>
      <td>100%</td>
      <td>0–1 per run</td>
      <td>All schemas · Well-understood quirk</td>
    </tr>
    <tr>
      <td>llama3.2:3b</td>
      <td>95%</td>
      <td>4 on code_review</td>
      <td>Drops at temperature 0.7</td>
    </tr>
    <tr style="background-color: #fce8e8;">
      <td>❌ qwen3:4b</td>
      <td>Eliminated</td>
      <td>N/A</td>
      <td>Token budget exhausted before JSON closes</td>
    </tr>
  </tbody>
</table>

<br>

**Key findings:**

- **Gemma 3:4b maintained 100% success across all schemas at all four temperatures with zero retries.** For a production pipeline where the output format must be machine-readable every time, this reliability profile is the decision-making data point.

- **Phi 3.5:3.8b achieved 100% with occasional single retries.** The inline comment issue is real but predictable - once handled in the extraction layer, Phi produces valid structured output consistently.

- **Llama 3.2:3b dropped to 95% on the code_review schema at temperature 0.7.** The nested enum structure in code_review is the most demanding schema - at higher temperatures, Llama occasionally produces structurally valid but schema-non-compliant output that a single retry did not recover.

- **Qwen 3:4b was eliminated.** Its verbose generation style exhausts the token allocation before consistently closing complex JSON objects. An architectural characteristic, not a bug - but one that makes it unsuitable for structured extraction pipelines.

---

### What this means practically

The split between Phase 1 and Phase 2 results is the most actionable finding of the project so far. Llama wins on speed. Gemma wins on structured output reliability. Phi sits in the middle - fast enough, reliable enough, with one well-understood quirk to engineer around.

> *"The interesting engineering insight is that model selection is not a single decision. Different components of the same pipeline may warrant different models, chosen for different properties."*

For Jarvis specifically, the RAG pipeline's retrieval step needs to return structured results every time - chunk text, similarity score, source filename, metadata. A 5% failure rate on that step introduces unreliability into the user experience. Gemma's 100% reliability profile makes it the candidate for structured extraction components. Llama's speed advantage makes it the candidate for conversational and summarisation tasks.

---

> **Coming in Part 3:** The final comparison study - 40 standardised prompts across 7 categories, 360 total inferences, quality scoring across 4 dimensions. Which model wins on summarisation? Which dominates code generation? Where do all three converge? And the final use-case recommendations with the full benchmark dataset published on GitHub.

`#LocalAI #MachineLearning #LLM #Python #Pydantic #AIEngineering #EdgeAI #OpenSource #Ollama`

---

<br>
<br>

## Part 3 of 3 - 40 prompts. 360 inferences. One clear answer - and several surprises.

*The final phase of local-model-lab: a systematic quality comparison across three models, seven categories, and a heuristic scoring methodology designed for fully offline evaluation. Here are the numbers.*

---

### The context

In Part 1, I benchmarked four SLMs on raw inference speed on CPU-only constrained hardware. Llama 3.2:3b won every speed metric. In Part 2, I tested structured JSON output reliability across four schemas and four temperature settings. Gemma 3:4b delivered 100% success with zero retries - Qwen was eliminated on token budget grounds. Three models - Llama, Phi, Gemma - entered Phase 3.

Phase 3 answers the question that actually matters: across a broad, representative set of tasks, which model produces the best output?

---

### Methodology - scoring without an LLM judge

Most model evaluation frameworks use an LLM-as-judge - a larger model that scores the outputs of the smaller ones. That is not an option here. The system is entirely offline. Using a cloud API to evaluate local models would defeat the purpose of the project entirely.

The scoring system is deterministic and fully offline - four dimensions on a 0 to 5 scale, maximum 20 points:

| Dimension | How it is measured |
|-----------|-------------------|
| **Relevance** (0–5) | Proportion of expected domain keywords present in the response |
| **Completeness** (0–5) | Response length vs minimum expected length; structural depth for multi-step tasks |
| **Format Compliance** (0–5) | JSON validity for structured prompts; code fences for code prompts |
| **Coherence** (0–5) | No repetition loops, no refusals, no mid-sentence truncation |

**40 prompts across 7 categories:**

- Factual Recall
- Reasoning
- Summarisation
- Code Generation
- Creative Writing
- Multi-step Instructions
- Structured Output

Each prompt run 3 times per model. **360 total inferences.** Temperature fixed at 0.0 - variance effects were already characterised in Phase 2.

---

### The overall results

<table>
  <thead>
    <tr>
      <th>Model</th>
      <th>Avg T/s</th>
      <th>TTFT (ms)</th>
      <th>Latency (ms)</th>
      <th>Quality / 20</th>
      <th>Timeouts</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background-color: #e6f4ea; font-weight: bold;">
      <td>🏆 llama3.2:3b</td>
      <td>13.1</td>
      <td>6,467</td>
      <td>26,638</td>
      <td>16.8</td>
      <td>0</td>
    </tr>
    <tr style="background-color: #e6f4ea; font-weight: bold;">
      <td>🏆 phi3.5:3.8b</td>
      <td>10.4</td>
      <td>5,739</td>
      <td>37,428</td>
      <td>16.8</td>
      <td>0</td>
    </tr>
    <tr>
      <td>gemma3:4b</td>
      <td>10.4</td>
      <td>7,156</td>
      <td>37,640</td>
      <td>16.2</td>
      <td>0</td>
    </tr>
  </tbody>
</table>

<br>

The headline number - Llama and Phi tied at 16.8/20, Gemma at 16.2/20 - understates how differentiated the results are by category. The averages converge precisely because each model has distinct strengths in different task types. Choosing based on overall score alone would be the wrong conclusion.

---

### Quality by category

| Category | gemma3:4b | llama3.2:3b | phi3.5:3.8b |
|----------|-----------|-------------|-------------|
| Factual Recall | 16.5 | 16.3 | 16.0 |
| Reasoning | 17.2 | 17.5 | 17.3 |
| **Summarisation** | 16.2 | **17.8** | 17.2 |
| **Code Generation** | 16.5 | 16.2 | **18.0** |
| Creative Writing | 15.5 | 15.8 | 16.0 |
| Multi-step Instructions | 15.3 | 16.5 | 16.0 |
| Structured Output | 16.3 | 17.1 | 16.6 |

---

### Where each model wins

**Summarisation → Llama (17.8/20)**
Concise, focused, structured. Consistently produces summaries that hit the key points without padding. This is the task type most directly relevant to Jarvis's document knowledge base - and it is where Llama's lower verbosity becomes an asset rather than a limitation.

**Code generation → Phi (18.0/20)**
The highest single-category score across the entire study. Microsoft's training philosophy - high-quality synthetic data over raw corpus scale - pays visible dividends here. Phi produces cleaner, more correct code with better fence formatting than either competitor. For any deployment where code generation is a primary task, Phi is the clear choice.

**Reasoning → effectively tied**
All three models scored within 0.3 points of each other across reasoning prompts. At 3–4B parameters, reasoning capability has largely converged across training approaches and organisations. The differences that exist are within measurement noise at this scale.

**Structured JSON reliability → Gemma (confirmed from Phase 2)**
Phase 3 reinforced Phase 2's finding. Gemma's format compliance score is the most consistent across all schema types. When the output must be machine-readable every time, Gemma's determinism is the differentiating property.

---

### Quality dimension breakdown

| Dimension | gemma3:4b | llama3.2:3b | phi3.5:3.8b |
|-----------|-----------|-------------|-------------|
| Relevance | 3.9 | 4.0 | 4.1 |
| Completeness | 5.0 | 5.0 | 5.0 |
| Format Compliance | 4.0 | 4.0 | 4.0 |
| **Coherence** | 3.4 | **3.8** | 3.6 |

Coherence is where the gap is largest. Llama scored 3.8/5 against Gemma's 3.4/5. Gemma showed occasional repetition in longer responses - sentences restating the same point with slight rewording. This affects user experience on longer-form generation tasks and is a known characteristic of models trained on heavily filtered corpora.

---

### Final recommendations by use case

| Use case | Recommended model | Reason |
|----------|-------------------|--------|
| Latency-sensitive / real-time assistant | `llama3.2:3b` | Fastest at 13.1 T/s, best overall quality |
| Code generation and review | `phi3.5:3.8b` | Highest code quality score (18.0/20) |
| Structured JSON pipelines | `gemma3:4b` | 100% reliability, zero retries |
| Document summarisation | `llama3.2:3b` | Highest summarisation score (17.8/20) |
| Memory-constrained deployment | `phi3.5:3.8b` | Smallest memory footprint |
| General quality + speed balance | `llama3.2:3b` | Best all-round across speed and quality |

---

### Back to where this started - what it means for Jarvis

The problem that triggered this entire project was practical: API embedding costs and data privacy during development of a personal AI assistant. Three phases and 360 inferences later, the answer is more nuanced than I expected when I started.

For Jarvis's conversational and summarisation components - local inference with Llama 3.2:3b is viable. Fast enough, coherent enough, zero ongoing cost. For structured extraction from documents - Gemma is the right component, chosen specifically for its JSON reliability profile, not its overall benchmark score. For any future code-aware features - Phi is the candidate.

> *"Model selection is not a single decision across an entire system. It is a series of component-level decisions, each driven by the specific performance property that matters most for that component."*

The broader significance extends beyond a personal project. The same constraints that motivated this work - data that cannot leave the building, inference cost at scale, offline environments - are blocking AI adoption in every regulated industry today. Healthcare providers cannot send clinical notes to commercial APIs. Law firms processing privileged documents have the same restriction. Defence and financial services operate under stricter constraints still.

The 3–4B parameter models from Meta, Microsoft, and Google now run at production-viable speeds on consumer hardware. The capability is here. The engineering work - understanding which model to choose, on what hardware, verified under what conditions, for which specific task - is what makes that capability real and deployable. That is what this project documents.

---

### Full source and data

The complete benchmark dataset, prompt suite, scoring methodology, raw JSONL results, and generated comparison report are published and fully reproducible.

**GitHub:** [github.com/rajeshkancharla/local-model-lab](https://github.com/rajeshkancharla/local-model-lab)

**Stack:** Python 3.13 · httpx · Pydantic v2 · FastAPI · Typer · Rich · psutil · pytest · Ollama v0.20.0

---

*This is Part 3 of a 3-part series. Part 1 covered infrastructure setup and inference speed benchmarking. Part 2 covered structured output reliability and temperature variance.*

`#LocalAI #MachineLearning #LLM #Python #EdgeAI #OpenSource #AIEngineering #Ollama #DataEngineering #Portfolio`
