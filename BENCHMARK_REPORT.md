
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

