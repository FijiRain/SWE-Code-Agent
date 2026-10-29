
# Consignes :

You must produce a benchmark report comparing at least 5 models across at least 2 providers on the same set of at least 3 SWE-bench tasks.

## Setup: 

Which models/providers were compared, which tasks were used, and why those tasks were selected

## Results table: 

For each model × task combination:
• Pass/Fail
• Iterations used
• Total input tokens
• Total output tokens
• Wall-clock time

## Provider reliability: 

For each model/provider:
• Average response time per request
• Number of retries needed (rate limits, timeouts, errors)
• Overall availability during benchmark runs

## Intermediary metrics (at least 2 of the following):

• Step at which the agent first reads/edits the file that appears in the final patch
(exploration efficiency)
• Step at which test failures first decrease vs baseline (partial progress)
• Iterations between “tests first pass” and final_answer (submission discipline — zero is ideal)

These metrics can be measured manually by inspecting your solution.json files
— automation is not required. What matters is the analysis, not the tooling.

## Ablation study: 

At least one before/after comparison of a change to your agent
(prompt, tools, parameters) on the same tasks with the same model

## Conclusions: 

Which model(s) you selected for your final pipeline and why. Which
models can be disregarded and why. Based on your data.

The backing solution.json files must be present in your repository.


_______________________

Groq: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://api.groq.com/openai/v1/"

OpenRouter: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://openrouter.ai/api/v1"

Google AI Studio: uv run python3 -m agent_mbpp --task-file tests/test_mbpp_task.json --output tests/mbpp_solution.json --model-name "" --provider-url "https://generativelanguage.googleapis.com/v1beta/openai/"

# MBPP (task 128):

## Google:

gemini-3-flash-preview : 

  "iterations": 3,
  "total_requests": 3,
  "total_input_tokens": 4282,
  "total_output_tokens": 650,
  "total_time_seconds": 7.871476888656616,

gemini-3.1-flash-lite-preview :

  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2448,
  "total_output_tokens": 262,
  "total_time_seconds": 4.348650932312012,

## Groq

qwen/qwen3.8-27b :

  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2380,
  "total_output_tokens": 219,
  "total_time_seconds": 1.775547981262207,

openai/gpt-oss-20b :

"error": "Unrecoverable client error (400): {\"error\":{\"message\":\"Tool choice is none, but model called a tool\",\"type\":\"invalid_request_error\",\"code\":\"tool_use_failed\",\"failed_generation

openai/gpt-oss-120b (top swe)

  "iterations": 2,
  "total_requests": 2,
  "total_input_tokens": 2398,
  "total_output_tokens": 518,
  "total_time_seconds": 5.684346914291382,



## OpenRouter


