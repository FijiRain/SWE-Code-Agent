# Agent Smith — SWE-bench Model Benchmark Report

## Quick Reference: Agent Execution Commands

```bash
# Groq
uv run python3 -m agent_mbpp \
  --task-file tests/test_mbpp_task.json \
  --output tests/mbpp_solution.json \
  --model-name "<model_name>" \
  --provider-url "https://api.groq.com/openai/v1/"

uv run python3 -m agent_swebench \
  --task-file cache/swebench_task.json \
  --output cache/swebench_solution.json \
  --model-name "<model_name>" \
  --provider-url "https://api.groq.com/openai/v1/"

# OpenRouter
uv run python3 -m agent_swebench \
  --task-file cache/swebench_task.json \
  --output cache/swebench_solution.json \
  --model-name "<model_name>" \
  --provider-url "https://openrouter.ai/api/v1"

# Google AI Studio
uv run python3 -m agent_swebench \
  --task-file cache/swebench_task.json \
  --output cache/swebench_solution.json \
  --model-name "<model_name>" \
  --provider-url "https://generativelanguage.googleapis.com/v1beta/openai/"
```

---

## 1. Experimental Setup & Methodology

### 1.1 Providers and Models Evaluated

To evaluate raw solve rate alongside iteration efficiency, token economy, and free-tier API stability, we tested **9 distinct LLMs** across **3 free-tier providers** (**Groq**, **OpenRouter**, and **Google AI Studio**) with multi-key rotation enabled (`KeyManager`).

Following an initial qualification phase on `sympy__sympy-14711`, non-viable models that failed the simplest task (due to format violations, tool refusal, or hard timeouts) were eliminated so as not to waste daily free-tier quotas on harder tasks. Since 4 models passed Task 1 and the benchmark requires comparing **at least 5 models across at least 2 providers on the same 3 SWE-bench tasks**, we retained **`gemini-3.5-flash-lite`** as our 5th candidate thanks to its sub-1.5s inference speed.

**Final 5-Model Cohort (Evaluated Across All 3 SWE-bench Tasks):**
1. **`openai/gpt-oss-120b`** — *Groq*
2. **`qwen/qwen3.8-27b`** — *Groq*
3. **`gemini-3.1-flash-lite-preview`** — *Google AI Studio*
4. **`nvidia/nemotron-3.5-super-vl:free`** — *OpenRouter*
5. **`gemini-3.5-flash-lite`** — *Google AI Studio*

**Additional Candidate Models Screened in Task 1:**
- `nvidia/nemotron-3-ultra-550b-a55b:free` (*OpenRouter*)
- `dots-studio/dots-3-note-preview:free` (*OpenRouter*)
- `cohere/north-mini-code:free` (*OpenRouter*)
- `gemini-3-flash-preview` (*Google AI Studio*)

---

### 1.2 Selected SWE-bench Tasks & Rationale

We selected **3 SWE-bench Verified tasks** spanning three distinct Python ecosystems and increasing engineering complexity:

| # | Instance ID | Repository / Domain | Selection Rationale |
| :-: | :--- | :--- | :--- |
| **1** | `sympy__sympy-14711` | `sympy/sympy` *(Symbolic Math)* | Recommended by the project specification as one of the simplest baseline tasks. Ideal as an initial screening filter to test a broad pool of models and select the strongest candidates. |
| **2** | `pydata__xarray-4629` | `pydata/xarray` *(Data Analysis)* | Challenges the agent on a completely different paradigm: scientific data structures and dictionary attribute merging (`merge_attrs`), testing generalization beyond symbolic algebra. |
| **3** | `django__django-11066` | `django/django` *(Web Backend / ORM)* | Advanced production-grade backend bug (`RenameContentType._rename` multi-database routing during migrations). Representative of a real-world bug in a large production codebase. |

---

### 1.3 Evaluation Limits & Metric Definitions

All SWE-bench runs were executed under the strict hard limits enforced by the evaluation harness:

| Hard Limit | Threshold |
| :--- | :--- |
| **Maximum Iterations** | `30` steps |
| **Maximum Cumulative Input Tokens** | `300,000` tokens |
| **Maximum Cumulative Output Tokens** | `10,000` tokens |
| **Wall-Clock Timeout** | `900.0` seconds (15 min) |

**Benchmark & Intermediary Metrics Tracked:**
- **Exploration Efficiency (`First Read/Edit`)**: The 1-indexed iteration (`@ Step N`) at which the agent first reads or edits the target file modified in the final patch. Lower values reflect faster codebase localization via `search_code` and `read_file`.
- **Submission Discipline**: Once the evaluation test suite (`run_tests()`) passes, how many extra or superfluous iterations occur before the agent submits `final_answer(get_patch())`. **`0` is ideal** (immediate submission without wasted steps).
- **Provider Availability**: Defined as `iterations / (iterations + total_retries)`, measuring the proportion of LLM API calls that succeeded without rate-limit (`429`/`413`) or transient server retries.

### 1.4 Backing Execution Traces (`benchmark_datas/`)

> **Note on Backing `SolutionOutput` Files:** Rather than overwriting a single `solution.json` file at the repository root across 20+ benchmark runs, all individual `SolutionOutput` JSON traces backing this report are organized **by task** inside the [`benchmark_datas/`](./benchmark_datas/) directory:
> - [`benchmark_datas/sympy__sympy-14711/`](./benchmark_datas/sympy__sympy-14711/)
> - [`benchmark_datas/pydata__xarray-4629/`](./benchmark_datas/pydata__xarray-4629/)
> - [`benchmark_datas/django__django-11066/`](./benchmark_datas/django__django-11066/)
>
> Each file (`<provider>_<model>_<task_id>.json`) follows the exact `SolutionOutput` / `StepMetrics` schema produced by our agent.

---

## 2. Global SWE-bench Results Matrix (5 Qualified Models × 3 Tasks)

### 2.1 High-Level Summary Across the 3 Tasks

| Model | Provider | Tasks Solved | Avg Iterations | Total Input Tokens (3 Tasks) | Total Output Tokens (3 Tasks) | Total Wall-Clock Time |
| :--- | :--- | :-: | :-: | --: | --: | --: |
| **`openai/gpt-oss-120b`** | Groq | **3 / 3 (100%)** | **6.0** | 94,332 | 3,864 | 403.3s |
| **`qwen/qwen3.8-27b`** *(post-413 patch)* | Groq | **3 / 3 (100%)**\* | **6.7** | 104,532 | 1,314 | 1,100.4s |
| **`gemini-3.1-flash-lite-preview`** | Google AI Studio | **3 / 3 (100%)** | 11.3 | 225,872 | 3,661 | **121.4s** |
| **`nvidia/nemotron-3.5-super-vl:free`** | OpenRouter | **3 / 3 (100%)** | 11.0 | 211,461 | 7,649 | 277.6s |
| **`gemini-3.5-flash-lite`** | Google AI Studio | **2 / 3 (66.7%)** | 15.0 | 380,442 | 5,612 | **85.3s** |

*\*Note: On Task 3 (`django__django-11066`), `qwen/qwen3.8-27b` applied the valid fix in `/testbed` before hitting Groq API rate/token limits at Step 11; the orchestrator's `force_swe_patch()` recovery mechanism automatically extracted and saved the passing git diff.*

---

### 2.2 Detailed Model × Task Results Table

| Task | Model | Provider | Status | Iterations (`/ 30`) | Input Tokens (`/ 300k`) | Output Tokens (`/ 10k`) | Wall Time (`/ 900s`) | First Read/Edit | Submission Discipline |
| :--- | :--- | :--- | :-: | :-: | --: | --: | --: | :-: | :-: |
| **`sympy__sympy-14711`** | `openai/gpt-oss-120b` | Groq | **PASSED** | 4 | 16,243 | 1,389 | 55.7s | Step 2 | **0** |
| **`sympy__sympy-14711`** | `qwen/qwen3.8-27b` *(Run 3)* | Groq | **PASSED** | 4 | 15,645 | 289 | 77.4s | Step 1 | **0** |
| **`sympy__sympy-14711`** | `nvidia/nemotron-3.5-super-vl:free` | OpenRouter | **PASSED** | 24 | 167,037 | 6,454 | 132.1s | Step 1 | **0** |
| **`sympy__sympy-14711`** | `gemini-3.1-flash-lite-preview` | Google AI Studio | **PASSED** | 19 | 135,416 | 1,606 | 44.0s | Step 1 | **0** |
| **`sympy__sympy-14711`** | `gemini-3.5-flash-lite` | Google AI Studio | **FAILED** | 30 *(EXCEEDED)* | 293,575 | 4,743 | 53.1s | Step 2 | N/A |
| **`pydata__xarray-4629`** | `openai/gpt-oss-120b` | Groq | **PASSED** | 8 | 44,983 | 1,028 | 138.9s | Step 2 | **0** |
| **`pydata__xarray-4629`** | `qwen/qwen3.8-27b` | Groq | **PASSED** | 5 | 26,993 | 348 | 361.0s | Step 1 | **0** |
| **`pydata__xarray-4629`** | `nvidia/nemotron-3.5-super-vl:free` | OpenRouter | **PASSED** | 5 | 23,724 | 642 | 69.8s | Step 1 | **0** |
| **`pydata__xarray-4629`** | `gemini-3.1-flash-lite-preview` | Google AI Studio | **PASSED** | 8 | 46,059 | 1,121 | 28.4s | Step 1 | **0** |
| **`pydata__xarray-4629`** | `gemini-3.5-flash-lite` | Google AI Studio | **PASSED** | 6 | 34,700 | 360 | 17.7s | Step 1 | **0** |
| **`django__django-11066`** | `openai/gpt-oss-120b` | Groq | **PASSED** | 6 | 33,106 | 1,447 | 208.7s | Step 2 | **0** |
| **`django__django-11066`** | `qwen/qwen3.8-27b` | Groq | **PASSED**\*\* | 11 | 61,894 | 677 | 662.0s | Step 2 | N/A |
| **`django__django-11066`** | `nvidia/nemotron-3.5-super-vl:free` | OpenRouter | **PASSED** | 4 | 20,700 | 553 | 75.7s | Step 1 | **0** |
| **`django__django-11066`** | `gemini-3.1-flash-lite-preview` | Google AI Studio | **PASSED** | 7 | 44,397 | 934 | 49.0s | Step 1 | **0** |
| **`django__django-11066`** | `gemini-3.5-flash-lite` | Google AI Studio | **PASSED** | 9 | 52,167 | 509 | 14.5s | Step 3 | 1 |

*\*\*Patch recovered and validated via `force_swe_patch()` after API key rate-limit exhaustion at Step 11.*

---

## 3. Task-by-Task Breakdown & Qualitative Observations

### 3.1 Task 1 — `sympy__sympy-14711` (Initial Screening Across 9 Models)

This task was chosen first because the project specification identifies it as one of the easiest SWE-bench problems, making it ideal to benchmark a wide range of free-tier models and filter out unreliable candidates early.

| Provider | Model | Status | Iter (`/ 30`) | Input Tok (`/ 300k`) | Output Tok (`/ 10k`) | Time (`/ 900s`) | Avg Resp. Time | Retries | Availability | First Read/Edit | Subm. Disc. |
| :--- | :--- | :-: | :-: | --: | --: | --: | --: | :-: | :-: | :-: | :-: |
| **Groq** | `openai/gpt-oss-120b` | **PASSED** | 4 | 16,243 | 1,389 | 55.7s | 12,203.7 ms (12.20s) | 0 | 100.0% (4+0) | Step 2 | 0 |
| **Groq** | `qwen/qwen3.8-27b` *(Test 1)* | **PASSED** *(rescued)* | 10 | 46,075 | 896 | 342.7s | 33,406.9 ms (33.41s) | 0 | 100.0% (10+0) | Step 1 | N/A |
| **Groq** | `qwen/qwen3.8-27b` *(Test 3 — 413 patch)* | **PASSED** | 4 | 15,645 | 289 | 77.4s | 17,885.7 ms (17.89s) | 0 | 100.0% (4+0) | Step 1 | 0 |
| **OpenRouter** | `nvidia/nemotron-3-ultra-550b-a55b:free` | **FAILED** | 30 *(EXCEEDED)* | 211,860 | 3,339 | 122.8s | 3,672.7 ms (3.67s) | 1 | 96.8% (30+1) | Step 2 | N/A |
| **OpenRouter** | `dots-studio/dots-3-note-preview:free` | **FAILED** | 25 | 92,499 | 23,303 *(EXCEEDED)* | 270.8s | 10,712.9 ms (10.71s) | 1 | 96.2% (25+1) | Never | N/A |
| **OpenRouter** | `nvidia/nemotron-3.5-super-vl:free` | **PASSED** | 24 | 167,037 | 6,454 | 132.1s | 4,891.4 ms (4.89s) | 1 | 96.0% (24+1) | Step 1 | 0 |
| **OpenRouter** | `cohere/north-mini-code:free` | **FAILED** | 1 | 2,834 | 21,088 *(EXCEEDED)* | 205.8s | 200,664.5 ms (200.66s) | 2 | 33.3% (1+2) | N/A | N/A |
| **Google AI** | `gemini-3.1-flash-lite-preview` | **PASSED** | 19 | 135,416 | 1,606 | 44.0s | 1,667.5 ms (1.67s) | 1 | 95.0% (19+1) | Step 1 | 0 |
| **Google AI** | `gemini-3-flash-preview` | **FAILED** *(TIMEOUT)* | — | — | — | >900s | — | — | 0.0% | N/A | N/A |
| **Google AI** | `gemini-3.5-flash-lite` | **FAILED** | 30 *(EXCEEDED)* | 293,575 | 4,743 | 53.1s | 1,422.6 ms (1.42s) | 1 | 96.8% (30+1) | Step 2 | N/A |

#### Qualitative Notes on Task 1 Runs:
- **`qwen/qwen3.8-27b` (Groq — Tests 1, 2 & 3)**:
  - *Test 1 & Test 2*: **Our orchestrator architecture saved these runs!** Qwen correctly diagnosed and edited the codebase, but Groq interrupted the loop at Step 10 (and Step 8 in Test 2) with an **`HTTP 413`** error because the growing message history exceeded Groq's strict input-tokens-per-minute (`ITPM = 7,000`) ceiling. Because our `Orchestrator` calls `force_swe_patch()` whenever a SWE-bench loop exits early without `final_answer()`, it automatically retrieved the uncommitted `git diff` inside `/testbed` and validated the task!
  - *Test 3*: After updating `orchestrator.py` to handle `HTTP 413` errors properly instead of crashing on a single oversized payload, Qwen completed the task cleanly in just **4 / 30 iterations** (`15,645` input tokens, `289` output tokens, `77.4s`, `Submission discipline: 0`).
- **`nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter)**: Failed **atrociously** on the simplest SWE-bench task (`30 / 30` iterations exceeded). It first attempted to craft a patch using an incompatible Python version, then convinced itself that the SymPy installation itself was broken and **uninstalled SymPy** inside the container, before ultimately patching the wrong file.
- **`dots-studio/dots-3-note-preview:free` (OpenRouter)**: Failed (`25 / 30` iterations, `23,303 / 10,000` output tokens exceeded). The model kept hallucinating and remained extremely stubborn: it never once invoked `read_file` to inspect the repository and spammed `<think>` brackets everywhere until blowing past the cumulative output token limit.
- **`cohere/north-mini-code:free` (OpenRouter)**: Failed immediately on Iteration 1 (`21,088 / 10,000` output tokens exceeded, `200.66s` single-call latency, `33.3%` availability). The model completely refused to follow the `Thought -> Code` turn protocol and hallucinated fake `Observation:` results on its own.
- **`gemini-3-flash-preview` (Google AI Studio)**: Timed out without ever submitting a solution.
- **`gemini-3.5-flash-lite` (Google AI Studio)**: Failed (`30 / 30` iterations exceeded in just `53.1s`, `1.42s` avg response time). The model suffered from **exploration paralysis syndrome**: it kept reading and inspecting files over and over without ever committing to an `edit_file()` call, exhausting all 30 allowed iterations.

---

### 3.2 Task 2 — `pydata__xarray-4629` (Data Analysis Paradigm — 5 Qualified Models)

This task challenges the agent on a scientific data analysis library (`xarray`), requiring it to identify and fix shallow-reference mutation in `merge_attrs(..., combine_attrs="override")`. All **5 qualified models solved the task (`100%` pass rate)**.

| Provider | Model | Status | Iter (`/ 30`) | Input Tok (`/ 300k`) | Output Tok (`/ 10k`) | Time (`/ 900s`) | Avg Resp. Time | Retries | Availability | First Read/Edit | Subm. Disc. |
| :--- | :--- | :-: | :-: | --: | --: | --: | --: | :-: | :-: | :-: | :-: |
| **Groq** | `openai/gpt-oss-120b` | **PASSED** | 8 | 44,983 | 1,028 | 138.9s | 15,073.6 ms (15.07s) | 0 | 100.0% (8+0) | Step 2 | 0 |
| **Groq** | `qwen/qwen3.8-27b` | **PASSED** | 5 | 26,993 | 348 | 361.0s | 32,728.1 ms (32.73s) | 0 | 100.0% (5+0) | Step 1 | 0 |
| **OpenRouter** | `nvidia/nemotron-3.5-super-vl:free` | **PASSED** | 5 | 23,724 | 642 | 69.8s | 1,814.5 ms (1.81s) | 2 | 71.4% (5+2) | Step 1 | 0 |
| **Google AI** | `gemini-3.1-flash-lite-preview` | **PASSED** | 8 | 46,059 | 1,121 | 28.4s | 2,717.7 ms (2.72s) | 0 | 100.0% (8+0) | Step 1 | 0 |
| **Google AI** | `gemini-3.5-flash-lite` | **PASSED** | 6 | 34,700 | 360 | **17.7s** | **1,338.6 ms (1.34s)** | 0 | 100.0% (6+0) | Step 1 | 0 |

#### Qualitative Notes on Task 2 Runs:
- Every single model pinpointed the exact target file at **Step 1 or Step 2** and achieved an ideal **Submission Discipline of `0`** (submitting `final_answer(get_patch())` immediately once tests passed).
- Notably, **`gemini-3.5-flash-lite`** overcame its Task 1 exploration paralysis and solved the issue in just **6 iterations and 17.7s total wall-clock time** (`360` output tokens).

---

### 3.3 Task 3 — `django__django-11066` (Production Web Backend Paradigm — 5 Qualified Models)

This advanced task pushes our models onto a production web backend codebase (`django/django`), reproducing a realistic multi-database migration bug where `RenameContentType._rename()` failed to pass `using=db` to `content_type.save(...)`. All **5 models produced a passing patch (`100%` pass rate)**.

| Provider | Model | Status | Iter (`/ 30`) | Input Tok (`/ 300k`) | Output Tok (`/ 10k`) | Time (`/ 900s`) | Avg Resp. Time | Retries | Availability | First Read/Edit | Subm. Disc. |
| :--- | :--- | :-: | :-: | --: | --: | --: | --: | :-: | :-: | :-: | :-: |
| **Groq** | `openai/gpt-oss-120b` | **PASSED** | 6 | 33,106 | 1,447 | 208.7s | 28,193.9 ms (28.19s) | 0 | 100.0% (6+0) | Step 2 | 0 |
| **Groq** | `qwen/qwen3.8-27b` | **PASSED** *(rescued)* | 11 | 61,894 | 677 | 662.0s | 37,590.9 ms (37.59s) | 1 | 91.7% (11+1) | Step 2 | N/A |
| **OpenRouter** | `nvidia/nemotron-3.5-super-vl:free` | **PASSED** | 4 | 20,700 | 553 | 75.7s | 2,336.0 ms (2.34s) | 2 | 66.7% (4+2)\* | Step 1 | 0 |
| **Google AI** | `gemini-3.1-flash-lite-preview` | **PASSED** | 7 | 44,397 | 934 | 49.0s | 5,061.4 ms (5.06s) | 0 | 100.0% (7+0) | Step 1 | 0 |
| **Google AI** | `gemini-3.5-flash-lite` | **PASSED** | 9 | 52,167 | 509 | **14.5s** | **1,200.4 ms (1.20s)** | 0 | 100.0% (9+0) | Step 3 | 1 |

*\*Note: `nvidia/nemotron-3.5-super-vl:free` completed all 4 agent steps without task failure after 2 transparent API key rotations (`4 / (4 + 2) = 66.7%` per-request availability, `100%` task completion).*

#### Qualitative Notes on Task 3 Runs:
- **`qwen/qwen3.8-27b` (Groq)**: Once again, **our agent architecture saved the solution!** After Qwen had already applied the valid fix via `edit_file()`, the loop encountered an `"All provider API keys have been exhausted"` error at Step 11 due to Groq's strict free-tier token ceiling on large Django test outputs. The fallback `force_swe_patch()` hook in `Orchestrator.complete_task()` automatically harvested the `git diff` from `/testbed`, allowing the solution to pass official validation.
- **`nvidia/nemotron-3.5-super-vl:free` (OpenRouter)**: Solved the Django bug in just **4 iterations** (`20,700` input tokens) — the lowest token footprint on Task 3.
- **`gemini-3.5-flash-lite` (Google AI Studio)**: Solved the issue in **14.5 seconds** end-to-end (`1.20s` per LLM request), with only `1` extra verification step after tests passed (`Submission discipline: 1`).

---

## 4. Provider Reliability Analysis

Aggregating all requests across the benchmark runs highlights stark operational trade-offs between the three free-tier providers:

| Provider | Model | Total Steps | Total Retries | Weighted Avg Response Time | Overall Availability | Operational Assessment |
| :--- | :--- | :-: | :-: | --: | :-: | :--- |
| **Groq** | `openai/gpt-oss-120b` | 18 | **0** | 18,809.3 ms (18.81s) | **100.0%** | Rock-solid reasoning; higher per-step latency due to strict `8,000` TPM free-tier ceiling requiring context window management. |
| **Groq** | `qwen/qwen3.8-27b` *(3-task cohort)* | 20 | 1 | 32,434.2 ms (32.43s) | **95.2%** | Ultra-compact output tokens (`1,314` across 3 tasks), but heavily constrained by Groq's `7,000` ITPM single-request payload cap (`HTTP 413`). |
| **Google AI Studio** | `gemini-3.1-flash-lite-preview` | 34 | 1 | 2,613.4 ms (2.61s) | **97.1%** | Best balance of speed (`2.61s`/req), high token allowance, and reliability (`3/3` tasks solved). |
| **Google AI Studio** | `gemini-3.5-flash-lite` | 45 | 1 | **1,367.0 ms (1.37s)** | **97.8%** | Fastest provider/model combination tested (`1.20s–1.42s`/req) with near-zero rate-limit friction. |
| **Google AI Studio** | `gemini-3-flash-preview` *(Task 1)* | 0 | — | Timeout | **0.0%** | Unusable during testing due to request hangs / hard timeout. |
| **OpenRouter** | `nvidia/nemotron-3.5-super-vl:free` | 33 | 5 | 4,115.5 ms (4.12s) | **86.8%** | Fast inference when routed, but OpenRouter free endpoints frequently trigger `429` rate limits (`1–2` key rotations per task). |
| **OpenRouter** | `nvidia/nemotron-3-ultra-550b-a55b:free` *(Task 1)* | 30 | 1 | 3,672.7 ms (3.67s) | 96.8% | Stable endpoint, but poor code-agent reasoning on SWE-bench. |
| **OpenRouter** | `dots-studio/dots-3-note-preview:free` *(Task 1)* | 25 | 1 | 10,712.9 ms (10.71s) | 96.2% | Unusable due to unconstrained `<think>` token explosion. |
| **OpenRouter** | `cohere/north-mini-code:free` *(Task 1)* | 1 | 2 | 200,664.5 ms (200.66s) | 33.3% | Severe latency (`>200s`) and frequent upstream errors. |

---

## 5. Intermediary Metrics Analysis

To look beyond binary pass/fail outcomes, we manually inspected the per-run `SolutionOutput` JSON traces in [`benchmark_datas/`](./benchmark_datas/) across all 15 runs of the 5-model cohort on two behavioral metrics:

| Model | Task 1 First Read/Edit | Task 2 First Read/Edit | Task 3 First Read/Edit | Avg Exploration Step | Submission Discipline (Task 1 / Task 2 / Task 3) |
| :--- | :-: | :-: | :-: | :-: | :-: |
| **`openai/gpt-oss-120b`** | Step 2 | Step 2 | Step 2 | **2.0** | `0 / 0 / 0` (**0.0 avg**) |
| **`qwen/qwen3.8-27b`** | Step 1 | Step 1 | Step 2 | **1.3** | `0 / 0 / N/A` (**0.0 avg**) |
| **`nvidia/nemotron-3.5-super-vl:free`** | Step 1 | Step 1 | Step 1 | **1.0** | `0 / 0 / 0` (**0.0 avg**) |
| **`gemini-3.1-flash-lite-preview`** | Step 1 | Step 1 | Step 1 | **1.0** | `0 / 0 / 0` (**0.0 avg**) |
| **`gemini-3.5-flash-lite`** | Step 2 | Step 1 | Step 3 | **2.0** | `N/A / 0 / 1` (**0.5 avg**) |

1. **High Exploration Efficiency (`Step 1.0 – 2.0`)**: Every qualified model reached the target source file within the first 1 to 3 steps. Explicitly documenting `search_code` and `search_function_or_class_definition_in_code` in `PROMPT_SWE` prevented blind directory traversal. By contrast, eliminated models like `dots-3-note-preview:free` never called `read_file` at all.
2. **Near-Perfect Submission Discipline (`0` Wasted Steps)**: Across 12 of the 13 non-interrupted passing runs, agents called `final_answer(get_patch())` on the **exact next turn (`0` extra iterations)** after `run_tests()` passed. Only `gemini-3.5-flash-lite` took `1` extra verification step on `django__django-11066`.

---

## 6. Ablation Study

### 6.1 Ablation #1 — Multi-Turn Stop Sequences (`stop=["...", "```Thought", "```\nThought"]`) on `openai/gpt-oss-120b`

- **Hypothesis & Problem Observed**: During early SWE-bench testing on `sympy__sympy-14711` with **`openai/gpt-oss-120b`** (Groq), configuring only `stop=["Observation:"]` proved insufficient. Instead of writing `"Observation:"` after closing its first Python code block, `openai/gpt-oss-120b` immediately concatenated ```` ```Thought: ... ```` and entered an **infinite-style multi-turn monologue of ~3,000+ output tokens** inside a single API response — hallucinating 8–9 consecutive `Thought` / `Code` turns (including imaginary searches, edits, test runs, and a premature `final_answer(get_patch())`) before the sandbox had executed a single line of code. Because no real `edit_file()` had run yet, the agent exited with an **empty git patch (`FAILED`)**.
- **Modification Applied**: We added `"```Thought"` and `"```\nThought"` to the `stop` sequence parameter in `Orchestrator.call_api()`, paired with automatic closing-fence restoration (`if content.count("```") % 2 == 1`) when the provider strips the stop delimiter.

| Configuration (`openai/gpt-oss-120b` on `sympy__sympy-14711`) | Outcome | Iterations | Output Tokens | Patch Quality |
| :--- | :-: | :-: | --: | :--- |
| **Before** (`stop=["Observation:"]` only) | **FAILED** | Hallucinated multi-turn in 1 response | ~3,000+ tokens in a single turn | Empty patch (premature `final_answer` before real edit) |
| **After** (`stop=["Observation:", "Observation\n", "```Thought", "```\nThought"]`) | **PASSED** | **4 / 30** | **1,389** *(cumulative across all 4 steps)* | Clean minimal 1-hunk git diff (`Submission discipline: 0`) |

### 6.2 Ablation #2 — `HTTP 413` Context-Ceiling Handling & `force_swe_patch()` Recovery on `qwen/qwen3.8-27b`

- **Modification Applied**: On `sympy__sympy-14711`, `qwen/qwen3.8-27b` initially hit Groq's `HTTP 413` per-request token limit (`ITPM = 7,000`) at Step 10 (`Test 1`) and Step 8 (`Test 2`), surviving only thanks to `force_swe_patch()`. Handling `HTTP 413` and bounding stale conversation history in `orchestrator.py` (`Test 3`) eliminated mid-run interruptions:

| Configuration (`qwen/qwen3.8-27b` on `sympy__sympy-14711`) | Outcome | Iterations | Input Tokens | Output Tokens | Wall-Clock Time |
| :--- | :-: | :-: | --: | --: | --: |
| **Before** *(Test 1 — crashes at Step 10 on `HTTP 413`, rescued by `force_swe_patch()`)* | **PASSED** *(rescued)* | 10 / 30 | 46,075 | 896 | 342.7s |
| **After** *(Test 3 — `HTTP 413` handling in `orchestrator.py`)* | **PASSED** *(clean)* | **4 / 30** | **15,645 (-66%)** | **289 (-68%)** | **77.4s (-77%)** |

---

## 7. Conclusions & Final Pipeline Selection

### 7.1 Models Selected for the Final Pipeline

Based on our quantitative results across all 3 SWE-bench paradigms, the top models selected for our final pipeline are:

1. **`openai/gpt-oss-120b` (Groq — Primary Reasoning Model)**:
   - Achieved a **100% pass rate (3/3)** with the lowest average iteration count (**6.0 steps/task**: `4`, `8`, and `6` iterations), **100% API availability (`0` retries)**, and **perfect `0` submission discipline** across every task.
2. **`qwen/qwen3.8-27b` (Groq — Token-Frugal Specialist)**:
   - Achieved a **100% pass rate (3/3)** while generating remarkably concise, surgical code (`1,314` cumulative output tokens across all 3 tasks combined — nearly **3× fewer output tokens** than any other 3/3 model), paired seamlessly with our `force_swe_patch()` and sliding-context safeguards.
3. **`gemini-3.5-flash-lite` (Google AI Studio — High-Speed / Low-Latency Runner)** *(alongside `gemini-3.1-flash-lite-preview` as 3/3 Google fallback)*:
   - Delivered unmatched execution speed (**`1.20s–1.42s` average latency per request**, solving `pydata__xarray-4629` in **`17.7s`** and `django__django-11066` in **`14.5s`** with `100%` availability on both), making Google AI Studio ideal when strict wall-clock timeouts (`120s` MBPP / `900s` SWE-bench) or Groq TPM quotas are tight. Meanwhile, `gemini-3.1-flash-lite-preview` (`3/3`, `121.4s` total time) and `nvidia/nemotron-3.5-super-vl:free` (`3/3` on OpenRouter) provide reliable cross-provider redundancy.

### 7.2 Disregarded Models & Justification

Based on our Task 1 empirical data, the following 4 models are permanently disregarded from our pipeline:

- **`nvidia/nemotron-3-ultra-550b-a55b:free` (OpenRouter)**: Disregarded due to destructive reasoning failures (`30/30` iterations exceeded on the easiest task, uninstalling core dependencies inside `/testbed` and editing the wrong files).
- **`dots-studio/dots-3-note-preview:free` (OpenRouter)**: Disregarded due to complete tool-use refusal (`0` `read_file` calls) and uncontrolled `<think>` token generation (`23,303 > 10,000` max output tokens).
- **`cohere/north-mini-code:free` (OpenRouter)**: Disregarded due to severe latency (`200.66s` for 1 request), poor availability (`33.3%`), and hallucinating `Observation:` blocks instead of yielding control to the sandbox (`21,088 > 10,000` max output tokens on Step 1).
- **`gemini-3-flash-preview` (Google AI Studio)**: Disregarded due to hard request timeouts exceeding the evaluation limit without producing any output.
