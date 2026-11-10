# AGENT TESTER

## Prerequisites

- Python 3.10+ and uv (https://docs.astral.sh/uv/).
- A running Docker daemon (needed for `validate`/`validate_metrics`/`warmup`, and for
  your own agent when it evaluates SWE-bench solutions).
- Network access on first use: `dump swebench`/`select` download the SWE-bench
  dataset from Hugging Face, and Docker images are pulled from Docker Hub on demand.

## Installation

```bash
cd agent_tester
uv sync
```

## Quickstart

```bash
./quickstart.sh mbpp --student-path ../student --model-name "model/name" --provider-url "https://provider.api/v1"
./quickstart.sh swebench --student-path ../student --model-name "model/name" --provider-url "https://provider.api/v1"
```

Runs dump, run-agent, and validate for one task in a single command, with the
right timeout and paths already wired up. Run `./quickstart.sh --help` for
all options (`--task-id`, `--seed`, `--cache-dir`). Useful to sanity-check
your agent quickly; see below for the commands it wraps.

## Core Usage

### Dump a task

```bash
# Random MBPP task
uv run agent_tester_eval dump mbpp --output task.json

# Specific MBPP task
uv run agent_tester_eval dump mbpp --task-id 128 --output task.json

# Random SWE-bench task
uv run agent_tester_eval dump swebench --output task.json

# Specific SWE-bench task
uv run agent_tester_eval dump swebench --task-id sympy__sympy-23534 --output task.json
```

### Run your agent under a timeout

```bash
uv run agent_tester_eval run-agent 120 "python -m agent_mbpp --task-file task.json --output solution.json"
```

Launches the given command in its own process group and kills it if it hasn't
returned within the given number of seconds. Useful to test your
own agent's behavior against the timeout before benchmarks.

### Validate a solution

```bash
# Correctness + metrics
uv run agent_tester_eval validate mbpp task.json solution.json
uv run agent_tester_eval validate swebench task.json solution.json

# Skip metrics check
uv run agent_tester_eval validate mbpp task.json solution.json --skip-metrics

# Metrics only
uv run agent_tester_eval validate_metrics mbpp solution.json
uv run agent_tester_eval validate_metrics swebench solution.json
```

### Display a solution

```bash
uv run agent_tester_eval display solution.json
uv run agent_tester_eval display solution.json --full
```

### All commands at a glance

`agent_tester_eval` is a Fire CLI (https://github.com/google/python-fire) --
`--help` alone only prints the module docstring, not the command list. Run it
with no arguments to see the full list: `dump`, `run-agent`, `validate`,
`validate_metrics`, `select`, `display`, `warmup`.

### Evaluation flow

```
AGENT TESTER                    AGENT
    │                              │
    │── dump task.json ───────────▶│
    │                              │── solve task
    │                              │── (pull docker for SWE-bench)
    │                              │── (cleanup container)
    │◀── solution.json ────────────│
    │── validate ──────────────────│
```

`dump`/`validate`/`validate_metrics`/`display` never execute your agent's code --
they only produce/read task and solution JSON. `run-agent` is the one command that
does launch a process (your agent, under a timeout).

---

## Metrics & Pass Criteria

### MBPP limits

| Metric | Limit |
|--------|-------|
| Max iterations | 10 |
| Max input tokens | 6,000 |
| Max output tokens | 1,500 |
| Timeout | 120 seconds |

### SWE-bench limits

| Metric | Limit |
|--------|-------|
| Max iterations | 30 |
| Max input tokens | 300,000 |
| Max output tokens | 10,000 |
| Timeout | 900 seconds |

### Pass criteria

| Benchmark | Tasks | Pass Threshold |
|-----------|-------|----------------|
| MBPP | 5 random | 4 out of 5 |
| SWE-bench | 3 random | 2 out of 3 |

---

## Troubleshooting

- A traceback mentioning `ResourceTracker`/`multiprocess` appears after a
  successful command: harmless, a known cleanup quirk in a dependency,
  unrelated to whether your command succeeded. Check the actual output/exit code.
