---
title: "Local AI in Practice - Part 2 of 3"
date: 2026-04-10
draft: false
tags: ["AI", "Cloud Architecture", "Data Engineering", "Tech Leadership", "AI Bias"]
description: "Part 2 of the 3 part engineering journey that performs a systematic comparison of small language models on consumer hardware"
---


<br>

## Part 2 of 3 - One model returned invalid JSON every single time. Here is what I had to engineer to make local AI production-ready.

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

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 1rem 0;">

  <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px 16px;">
    <div style="font-size: 14px; color: #888; margin-bottom: 4px;"><code>sentiment</code></div>
    <div style="font-size: 14px; color: #333;"><strong>Flat - label + confidence score</strong></div>
  </div>

  <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px 16px;">
    <div style="font-size: 14px; color: #888; margin-bottom: 4px;"><code>entities</code></div>
    <div style="font-size: 14px; color: #333;"><strong>Named entity list with types</strong></div>
  </div>

  <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px 16px;">
    <div style="font-size: 14px; color: #888; margin-bottom: 4px;"><code>code review</code></div>
    <div style="font-size: 14px; color: #333;"><strong>Nested - issues array with enums</strong></div>
  </div>

  <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px 16px;">
    <div style="font-size: 14px; color: #888; margin-bottom: 4px;"><code>summary</code></div>
    <div style="font-size: 14px; color: #333;"><strong>Structured - key points + metadata</strong></div>
  </div>

</div>

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
