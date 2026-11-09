*This project has been created as part of the 42 curriculum by alsimoni, anfarenc, tmoga.*

> « Never send a human to do a machine's job. » — Agent Smith, *The Matrix* (1999)

# Agent Smith — Autonomous Code Generation & Execution Framework

## Description

**Agent Smith** is an autonomous Software Engineering Code Agent framework built from scratch in Python 3.10 without any third-party agent orchestration libraries. Rather than relying on static prompts or rigid JSON tool-calling schemas, the agent reasons about programming tasks, writes executable Python code, invokes external tools via the **Model Context Protocol (MCP)**, observes execution results inside a restricted multi-process **Sandbox**, and iterates until all tests pass.

The framework is designed to solve two distinct software engineering benchmarks under strict iteration, token, and wall-clock limits:
- **MBPP (Mostly Basic Python Problems)**: Algorithmic Python challenges solved within `10` iterations, `6,000` input tokens, `1,500` output tokens, and `120s`.
- **SWE-bench Verified**: Real-world GitHub bug reports in large production repositories (`sympy`, `xarray`, `django`, etc.) solved inside isolated Docker environments within `30` iterations, `300,000` input tokens, `10,000` output tokens, and `900s`.

---

## System Architecture

The framework is divided into four decoupled security and execution domains:

```
+-------------------+       Prompt / Context        +------------------------+
|     LLM APIs      | <---------------------------> |      Orchestrator      |
| (Groq, OpenRouter,|    Stop-Bounded Generation    |  (KeyManager, Limits,  |
| Google AI Studio) |                               |  Context Compression)  |
+-------------------+                               +-----------+------------+
                                                                |
                                                         Raw LLM Response
                                                                v
                                                    +------------------------+
                                                    |     Code Extractor     |
                                                    |   (py_extractor.py)    |
                                                    | Python / XML / ReAct   |
                                                    +-----------+------------+
                                                                |
                                                      Executable Python Code
                                                                v
+---------------------------------------------------------------+---------------------------------------------------------------+
| SANDBOX (Host Process + Isolated Spawn Worker)                                                                                |
|                                                                                                                               |
|  +----------------------------------------+       Multiprocessing Pipe        +--------------------------------------------+  |
|  |         Worker Process (spawn)         | <-------------------------------> |           Main Sandbox Process             |  |
|  | - Restricted __builtins__ & __import__ |   CodeMsg / StdoutMsg / ResultMsg | - Enforces wall-clock execution timeout    |  |
|  | - Restricted open() (realpath check)   |   ToolCallMsg / ToolResultMsg     | - Restarts worker on timeout or crash      |  |
|  | - RLIMIT_AS memory cap                 |                                   | - Forwards ToolCallMsg to McpBridge        |  |
|  | - BlockedSocket (no network access)    |                                   | - Truncates oversized stdout & tool output |  |
|  | - Built-in final_answer() signal       |                                   +---------------------+----------------------+  |
|  +----------------------------------------+                                                         |                         |
+-----------------------------------------------------------------------------------------------------+-------------------------+
                                                                                                      |
                                                                                           STDIO / Streamable HTTP
                                                                                                      v
                                                                                +--------------------------------------------+
                                                                                |                MCP Servers                 |
                                                                                | - mcp_tools_mbpp.py (run_tests)            |
                                                                                | - mcp_tools_swebench.py (9 SWE tools)      |
                                                                                +---------------------+----------------------+
                                                                                                      |
                                                                                 Bind-Mounted TESTBED_PATH & docker exec
                                                                                                      v
                                                                                +--------------------------------------------+
                                                                                |        SWE-bench Docker Container          |
                                                                                |           (/testbed repository)            |
                                                                                +--------------------------------------------+
```

### Repository Structure

```text
.
├── agent_mbpp.py                 # CLI entry point for the MBPP agent
├── agent_swebench.py             # CLI entry point for the SWE-bench agent
├── mcp_tools_mbpp.py             # FastMCP server exposing MBPP tools (stdio & HTTP)
├── mcp_tools_swebench.py         # FastMCP server exposing the 9 SWE-bench tools (stdio & HTTP)
├── sandbox_template.json         # Example JSON configuration for the Sandbox CLI
├── sandbox_swebench.json         # Sandbox configuration used during SWE-bench runs
├── BENCHMARK_REPORT.md           # Full 5-model x 3-task SWE-bench benchmark study
├── benchmark_datas/              # Backing SolutionOutput JSON traces for all benchmark runs
└── src/
    ├── launcher.py               # Task validation, Docker lifecycle setup, and output serialization
    ├── models/                   # Pydantic schemas (SandboxConfig, StepMetrics, SolutionOutput, etc.)
    ├── orchestration/            # Agent loop, LLM API client, KeyManager, prompts, code extractor, Docker env
    ├── sandbox/                  # Multi-process sandbox, security restrictions, MCP client/bridge, REPL, manual
    └── tools/                    # Standalone tool implementations (path_utils, filesystem, search, execution)
```

---

## Agent Loop Explanation

The agentic loop is implemented in [`src/orchestration/orchestrator.py`](src/orchestration/orchestrator.py) and follows a strict **`Thought -> Code -> Observation`** cycle:

1. **Dynamic Manual Injection & Context Initialization (`build_context`)**:
   At the start of a task, the `Orchestrator` opens a `Sandbox` connected to the target MCP server (`mcp_tools_mbpp.py` or `mcp_tools_swebench.py`), dynamically generates the tool and environment documentation via `sandbox.get_manual()`, and injects it into the system prompt (`PROMPT_MBPP` or `PROMPT_SWE` in [`src/orchestration/prompts.py`](src/orchestration/prompts.py)).

2. **Stop-Bounded LLM Generation (`call_api` & `query_llm`)**:
   - The `Orchestrator` queries the OpenAI-compatible chat completion endpoint with `stop=["Observation:", "Observation\n", "```Thought", "```\nThought"]`. This prevents models from hallucinating fictional observations or chaining multiple unexecuted turns in a single response.
   - If a stop sequence cuts off the closing fence of a Markdown block (leaving an odd number of ` ``` ` delimiters), `call_api()` automatically restores the closing ` ``` ` fence so extraction remains clean.

3. **Multi-Format Code Extraction (`py_extractor.py`)**:
   To remain model-agnostic across diverse LLM families, [`src/orchestration/py_extractor.py`](src/orchestration/py_extractor.py) normalizes multiple output styles into executable Python before passing code to the sandbox:
   - **Primary Python blocks**: ```` ```python ... ``` ```` or ```` ```py ... ``` ```` (only the first block is kept via `keep_first_block()` so hallucinated follow-up steps are discarded).
   - **XML / Qwen / Hermes tool calls**: `<tool_call>{"name": "...", "arguments": {...}}</tool_call>`, `<code>...</code>`, or `<python>...</python>`.
   - **ReAct format**: `Action: tool_name` / `Action Input: {...}` converted into `print(tool_name(...))`.
   - **Unfenced `final_answer(...)` fallback**: Tokenizes text outside code fences using Python's `tokenize` module to rescue standalone `final_answer(...)` calls with balanced parentheses.
   - If no valid code block is found, the loop returns explicit feedback: `"Error: No valid Python code block found. You must wrap your code in ```python ... ```."`

4. **Multi-Key Rotation & Fault Tolerance (`KeyManager`)**:
   - [`src/orchestration/key_manager.py`](src/orchestration/key_manager.py) loads comma-separated API keys from environment variables (e.g. `GROQ_API_KEY="key1,key2,key3"`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`) matched dynamically from `--provider-url`.
   - On `HTTP 401`, `402`, `403`, or `429` rate-limit errors, the orchestrator parses `retry-after` / `x-ratelimit-reset-tokens` headers (`parse_header.py`), rotates to the next API key via `key_manager.rotate()`, and increments `StepMetrics.retries`.
   - On `HTTP 413` (`RequestTooLargeError`, common on Groq's strict tokens-per-minute cap), `trim_context()` progressively truncates the oldest oversized user observations in the conversation history and retries seamlessly.

5. **Execution, Observation Formatting & Patch Recovery (`sandbox_analysis` & `force_swe_patch`)**:
   - The extracted code is executed in the `Sandbox`. `sandbox_analysis()` formats `ExecutionResult` into an explicit `Observation:` message covering stdout, runtime errors, timeouts (preserving partial stdout), output truncation notices, or a reminder to use `print()` if no output was produced.
   - **Empty-Patch Guard & Automatic Patch Recovery**: In SWE-bench, if the model calls `final_answer(...)` with prose instead of a diff, or if the loop hits an iteration/token/quota limit after the model has already edited `/testbed`, `force_swe_patch()` executes `final_answer(get_patch())` inside the sandbox to harvest any valid uncommitted `git diff`. If no files were modified yet, `final_answer` is rejected with an error instructing the model to use `edit_file()` and `run_tests()` first.

6. **Metrics & Hard Limit Enforcement (`stop_loop`)**:
   Every iteration records a `StepMetrics` entry (`step`, `input_tokens`, `output_tokens`, `request_time_ms`, `timestamp`, `api_url`, `model_name`, `llm_output`, `sandbox_input`, `sandbox_output`, `retries`). The loop halts immediately if cumulative input tokens, output tokens, iterations, or wall-clock time reach the benchmark's hard limits, serializing a complete `SolutionOutput` JSON file.

---

## Sandbox Design

The sandbox ([`src/sandbox/`](src/sandbox/)) is a security boundary implemented strictly with the Python 3.10 standard library (`multiprocessing`, `ast`, `builtins`, `resource`, `socket`, `os`).

### 1. Process Isolation & Stateful Execution (`api.py` & `worker.py`)
- The `Sandbox` spawns a dedicated child process using `multiprocessing.get_context("spawn")` (`code_worker_loop` in [`src/sandbox/worker.py`](src/sandbox/worker.py)).
- The parent and worker communicate over a bidirectional `Pipe` using typed protocol messages ([`src/sandbox/protocol.py`](src/sandbox/protocol.py)): `ReadyMsg`, `CodeMsg`, `StdoutMsg`, `ToolCallMsg`, `ToolResultMsg`, `ResultMsg`, and `StopMsg`.
- Variables and imports persist inside the worker's `namespace` dictionary across consecutive `execute()` calls. If user code triggers a timeout, memory exhaustion, or process crash (e.g. `os._exit`), the parent kills the worker and spawns a fresh one automatically, notifying the LLM that state was reset.
- Wall-clock execution timeouts (`max_execution_time_seconds`) are enforced by the parent process polling the pipe. Time spent waiting on external MCP tool calls (`ToolCallMsg`) is excluded from the Python execution timer (`deadline += time.monotonic() - start_time`).

### 2. Standard-Library Security Restrictions (`restricted_sandbox.py`)
Before executing any code, the worker process locks down its environment:
- **Environment & Signal Scrubbing**: `os.environ.clear()` wipes all host environment variables (including API keys) inside the worker process before user code runs.
- **Allowlist Import Hook (`make_import` & `valid_module`)**: Replaces `__builtins__["__import__"]` with a custom import hook that only permits modules matching `SandboxConfig.authorized_imports` (supporting exact names and `package.*` wildcards) and blocks relative imports (`level != 0`). Imported modules are shallow-copied via `valid_module()`, stripping private `_` attributes and unauthorized submodules so sandboxed code cannot traverse module references (e.g. reaching `os` or `sys` through an allowed module).
- **Filesystem Access Restriction (`make_open` & `check_path_allowed`)**: Replaces `open()` with `restricted_open()`, which resolves symlinks and `..` segments via `os.path.realpath()` and verifies `os.path.commonpath()` against `SandboxConfig.allowed_directories`. Any access outside allowed directories (such as `/etc/passwd`, `/home`, or `../../../`) raises `PermissionError`.
- **Restricted Builtins (`build_builtins`)**: Builds `__builtins__` strictly from `SandboxConfig.authorized_builtins`, removing dangerous builtins (`eval`, `exec`, `compile`, `getattr`, `setattr`, `globals`, `input`, `exit`).
- **Network Isolation (`restricted_conn`)**: Monkey-patches `socket.socket` and `socket.SocketType` with `BlockedSocket` and overrides `create_connection`, `create_server`, `fromfd`, `getaddrinfo`, and `gethostbyname*` to raise `PermissionError("Network access is disabled in the sandbox")`.
- **Memory Limit (`apply_memory_restricted`)**: Applies `resource.setrlimit(resource.RLIMIT_AS, ...)` to cap the worker's virtual address space to `max_memory_mb`.
- **Exception Propagation**: `SystemExit` and `KeyboardInterrupt` inside sandboxed code are caught and reported as sandbox errors without killing the orchestrator, while `KeyboardInterrupt` on the host cleanly shuts down the worker and MCP bridge.

### 3. Built-in `final_answer` & Dynamic Manual Generation (`manual_manager.py`)
- **`final_answer` Construct**: Injected directly by the worker into `namespace["final_answer"]` (never exposed as an MCP tool). Calling `final_answer(val)` records `str(val)` and raises `FinalAnswerSignal` to immediately halt the current snippet and return the solution.
- **Dynamic MCP Discovery (`McpBridge` & `McpClient`)**: [`src/sandbox/McpClient.py`](src/sandbox/McpClient.py) supports both **stdio** subprocesses and **Streamable HTTP** (`streamable_http_client`) servers. [`src/sandbox/McpBrige.py`](src/sandbox/McpBrige.py) runs the async MCP client on a background event-loop thread so synchronous tool wrappers inside the worker can invoke tools seamlessly.
- **Dynamic Sandbox Manual (`build_manual` & `tool_help`)**: [`src/sandbox/manual_manager.py`](src/sandbox/manual_manager.py) introspects the connected MCP server's JSON schemas at runtime to generate function prototypes, descriptions, parameter types, and an in-sandbox `tool_help([...])` helper. Connecting a different MCP server (such as `simple_mcp_server.py`) automatically updates both the exposed callables and the generated manual.

---

## Tool Implementation Details

All MCP tools live in [`src/tools/`](src/tools/) and are exposed by [`mcp_tools_mbpp.py`](mcp_tools_mbpp.py) and [`mcp_tools_swebench.py`](mcp_tools_swebench.py) at the repository root. Both servers support `--transport stdio` / `stdio` and `--transport http` / `http` (using FastMCP's `streamable-http` transport).

### Hybrid Host–Docker Architecture for SWE-bench (Option b)
For SWE-bench, we implemented **Option (b)**: running the Sandbox and MCP server on the host while bridging into the SWE-bench Docker container ([`src/orchestration/docker_env.py`](src/orchestration/docker_env.py)):
1. `swe_docker_env()` extracts `/testbed` (including `.git`) from the task's image into a temporary host directory (`host_dir = /tmp/smith_testbed_*`), writes `task.eval_script` to `host_dir / "eval.sh"`, and starts the container in the background with `-v {host_dir}:/testbed`.
2. A `SIGTERM` signal handler and `try...finally` block guarantee `docker rm -f` and `shutil.rmtree(host_dir)` even if the agent process is force-killed by a timeout.
3. The MCP server receives `TESTBED_PATH` (pointing to `host_dir`) and `SWE_CONTAINER_ID`. When the 42 Moulinette tests `mcp_tools_swebench.py` standalone without Docker, only `TESTBED_PATH` is set, and the tools transparently operate in local mode on `TESTBED_PATH`.

### Path Translation & Traversal Protection (`src/tools/path_utils.py`)
- **`get_testbed_root()`**: Reads `TESTBED_PATH` from the environment (or `/testbed` if inside a container) and raises a `ValueError` if unset—never falling back to `Path.cwd()` so tools can never accidentally modify the host project directory.
- **`resolve_testbed_path(user_path)`**: Maps `/testbed/...` or relative paths to the resolved `TESTBED_PATH` root and verifies `resolved.is_relative_to(testbed_root)` to block path traversal (`../`).
- **`to_display_path(file)`**: Formats host temporary paths back into canonical `/testbed/<relative_path>` strings so the LLM and Docker commands always see consistent container paths.

### Mandatory Tools Overview
- **File System Tools ([`src/tools/filesystem.py`](src/tools/filesystem.py))**:
  - `read_file(filepath, start_line=1, end_line=-1)`: Returns 1-indexed lines formatted as `<line_num>: <line>`. Validates line bounds and caps output at `500` lines per call with a truncation notice to protect the LLM's context window.
  - `edit_file(filepath, old_str, new_str)`: Enforces exact uniqueness (`count == 1`), returning clear errors if `old_str` is missing or ambiguous (`count > 1`). After updating a `.py` file, it parses the updated content with `ast.parse()` and appends an explicit `SyntaxError` warning with line number if the edit broke syntax.
  - `list_files(directory=".", pattern="*")`: Recursively lists non-hidden, non-`__pycache__` files matching `pattern` (capped at `100` entries with a truncation notice).
- **Code Search Tools ([`src/tools/search.py`](src/tools/search.py))**:
  - `search_code(pattern, file_pattern="*")`: Recursive regex search across clean files, returning `/testbed/<path>:<line_num> <line>` (capped at `100` matches).
  - `search_function_or_class_definition_in_code(name)`: Uses Python's `ast.walk()` to locate exact `FunctionDef`, `AsyncFunctionDef`, and `ClassDef` nodes by name, avoiding false positives in comments or strings.
  - `find_references(name, filepath="", line=-1)`: Word-boundary regex search (`\b<name>\b`) across Python files (or a single file), optionally excluding the definition line.
- **Execution Tools ([`src/tools/execution.py`](src/tools/execution.py))**:
  - `run_command(command, workdir=".")`: Executes `["docker", "exec", "-w", container_workdir, container_id, "/bin/bash", "-c", command]` when `SWE_CONTAINER_ID` is set, or `["/bin/bash", "-c", command]` in `TESTBED_PATH` during standalone Moulinette tests (with `shell=False` on the host and a 60s timeout).
  - `get_patch()`: Runs `git -c core.fileMode=false diff` inside `TESTBED_PATH` to return the exact unified diff.
  - `run_tests()` (`run_swebench_tests`): Executes `/testbed/eval.sh` inside the container (or locally if no container is active) with a 300s timeout. Implements **tail truncation** (`result[-15000:]`), preserving the exit code and the end of the log where pytest failure tracebacks and summary lines appear.
  - `run_tests(code, test_list)` (`run_mbpp_tests`): Executes candidate MBPP code and assertions in an isolated subprocess with a 30s timeout, returning `{"success": bool, "output": str}`.

---

## Benchmark Results and Analysis

The full benchmark study comparing **9 screened models** and a final cohort of **5 models across 3 free-tier providers** (**Groq**, **Google AI Studio**, and **OpenRouter**) on **3 SWE-bench Verified tasks** (`sympy__sympy-14711`, `pydata__xarray-4629`, and `django__django-11066`) is available in **[`BENCHMARK_REPORT.md`](BENCHMARK_REPORT.md)**, with all backing `SolutionOutput` JSON files stored in **[`benchmark_datas/`](benchmark_datas/)**.

### Summary of 5-Model Cohort Across All 3 SWE-bench Tasks

| Model | Provider | Tasks Solved | Avg Iterations (`/ 30`) | Total Input Tokens (3 Tasks) | Total Output Tokens (3 Tasks) | Total Wall-Clock Time | Avg Exploration Step | Avg Submission Discipline |
| :--- | :--- | :-: | :-: | --: | --: | --: | :-: | :-: |
| **`openai/gpt-oss-120b`** | Groq | **3 / 3 (100%)** | **6.0** | 94,332 | 3,864 | 403.3s | Step 2.0 | **0.0** |
| **`qwen/qwen3.8-27b`** | Groq | **3 / 3 (100%)** | **6.7** | 104,532 | **1,314** | 1,100.4s | Step 1.3 | **0.0** |
| **`gemini-3.1-flash-lite-preview`** | Google AI Studio | **3 / 3 (100%)** | 11.3 | 225,872 | 3,661 | 121.4s | **Step 1.0** | **0.0** |
| **`nvidia/nemotron-3.5-super-vl:free`** | OpenRouter | **3 / 3 (100%)** | 11.0 | 211,461 | 7,649 | 277.6s | **Step 1.0** | **0.0** |
| **`gemini-3.5-flash-lite`** | Google AI Studio | **2 / 3 (66.7%)** | 15.0 | 380,442 | 5,612 | **85.3s** | Step 2.0 | 0.5 |

### Key Findings & Ablation Highlights
1. **Primary Pipeline Choice (`openai/gpt-oss-120b` on Groq)**: Solved `3/3` tasks with the lowest average step count (`6.0` iterations: `4`, `8`, and `6`), `100%` API availability (`0` retries), and `0` wasted turns after tests passed.
2. **Stop-Sequence Ablation**: Adding `"```Thought"` and `"```\nThought"` to the API `stop` sequences prevented `openai/gpt-oss-120b` from hallucinating multi-turn monologues (`~3,000+` output tokens in a single turn), turning a Task 1 failure into a clean **4-step pass**.
3. **Resilience Under Free-Tier Quotas (`HTTP 413` Trimming & `force_swe_patch()`)**: Adding `HTTP 413` context trimming reduced `qwen/qwen3.8-27b`'s Task 1 run from `10` steps (`46,075` input tokens, `342.7s`) down to **4 steps (`15,645` input tokens, `77.4s`)**, while `force_swe_patch()` rescued valid patches whenever upstream rate limits interrupted a run mid-flight.
4. **High-Speed Fallback (`gemini-3.1-flash-lite-preview` & `gemini-3.5-flash-lite` on Google AI Studio)**: Delivered `1.20s–2.61s` average response latency, solving `django__django-11066` in `14.5s–49.0s` end-to-end.

See **[`BENCHMARK_REPORT.md`](BENCHMARK_REPORT.md)** for per-task tables, provider reliability metrics, and the list of disregarded models.

---

## Instructions

### 1. Prerequisites & Installation
- **Python 3.10** and **[`uv`](https://docs.astral.sh/uv/)** package manager.
- **Docker** (required for SWE-bench tasks).

Install all dependencies inside the project virtual environment:
```bash
uv sync
```

### 2. Environment Configuration (`.env`)
Create a `.env` file at the root of the repository with your free-tier API keys (comma-separated for multi-key rotation):
```env
GROQ_API_KEY="gsk_key1,gsk_key2,gsk_key3"
OPENROUTER_API_KEY="sk-or-v1-key1,sk-or-v1-key2"
GEMINI_API_KEY="AIzaSyKey1,AIzaSyKey2"
```

### 3. Running the Interactive Sandbox CLI
```bash
# Launch interactive sandbox REPL with default restrictions
uv run sandbox

# Launch with a custom JSON configuration
uv run sandbox sandbox_template.json

# Launch connected to the MBPP MCP server over stdio
uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py" sandbox_template.json

# Launch connected to theMBPP MCP server over Streamable HTTP
uv run python mcp_tools_mbpp.py --transport http --port 8000
uv run sandbox --mcp-server "http://127.0.0.1:8000/mcp"

# Launch connected to the SWE-bench MCP server over stdio
TESTBED_PATH=/path/to/repo uv run sandbox --mcp-stdio "python mcp_tools_swebench.py" sandbox_template.json
```

### 4. Running the MBPP Agent
```bash
# 1. Dump an MBPP task using the moulinette
cd moulinette
uv run moulinette_eval dump mbpp --output ../cache/mbpp_task.json

# 2. Run the MBPP agent
cd ../student
uv run python -m agent_mbpp \
  --task-file ../cache/mbpp_task.json \
  --output ../cache/mbpp_solution.json \
  --model-name "openai/gpt-oss-120b" \
  --provider-url "https://api.groq.com/openai/v1/"

# 3. Validate the solution
cd ../moulinette
uv run moulinette_eval validate mbpp ../cache/mbpp_task.json ../cache/mbpp_solution.json
```

### 5. Running the SWE-bench Agent
```bash
# 1. Dump a SWE-bench task
cd moulinette
uv run moulinette_eval dump swebench --output ../cache/swebench_task.json

# 2. Run the SWE-bench agent
cd ../student
uv run python -m agent_swebench \
  --task-file ../cache/swebench_task.json \
  --output ../cache/swebench_solution.json \
  --model-name "openai/gpt-oss-120b" \
  --provider-url "https://api.groq.com/openai/v1/"

# 3. Validate the generated patch
cd ../moulinette
uv run moulinette_eval validate swebench ../cache/swebench_task.json ../cache/swebench_solution.json
```

---

## Resources

### Technical References & Papers

#### AI Agents & LLM:

- [Building Effective AI Agents \ Anthropic](https://www.youtube.com/watch?v=v2FigSIz_pI&list=WL&index=91&t=2s)
- [A survey on large language model based autonomous agents | Frontiers of Computer Science | Springer Nature Link](https://link.springer.com/article/10.1007/s11704-024-40231-1)
- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/pdf/2210.03629)
- [Python: Create a ReAct Agent from Scratch](https://www.youtube.com/watch?v=hKVhRA9kfeM)
- [A practical guide to building agents | OpenAI](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- [Agent Harness explained in 8min..](https://www.youtube.com/watch?v=1a1VXDdIyrk)
- [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/pdf/2304.03442)

#### MCP:

- [MCP expliqué à fond : le "port USB-C" qui branche l'IA sur le monde réel](https://www.youtube.com/watch?v=v2FigSIz_pI&list=WL&index=91&t=2s)
- [What is the Model Context Protocol (MCP)?](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro)
- [How Model Context Protocol (MCP) actually works](https://www.youtube.com/watch?v=cGuyrANVi4A)
- [Build an MCP server - Model Context Protocol](https://modelcontextprotocol.io/docs/2026-07-28/develop/build-server)
- [FastMCP](https://gofastmcp.com/getting-started/welcome)

#### Tool use:

- [Writing effective tools for AI agents—using AI agents \ Anthropic](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [JSON-RPC Client](https://www.youtube.com/watch?v=FmeyLUKHI4Q&t=22s)
- [Toolformer: Language Models Can Teach Themselves to Use Tools](https://arxiv.org/pdf/2302.04761)

#### Benchmarks: 

- [SWE-bench: Can Language Models Resolve Real-World GitHub Issues?](https://arxiv.org/abs/2310.06770)
- [Raising the bar on SWE-bench Verified with Claude 3.5 Sonnet](https://www.anthropic.com/news/swe-bench-sonnet)
- [SWE-bench Leaderboards](https://www.swebench.com/)

#### Sandbox:

- [Secure code execution · Hugging Face ](https://huggingface.co/docs/smolagents/tutorials/secure_code_execution)
- [Secure code execution · GitHub (sandbox open source pour exemple)](https://github.com/openedx/codejail)
- [Sandboxing Untrusted Python Code: Secure Execution Strategies and UBOS Solutions](https://ubos.tech/news/sandboxing-untrusted-python-code-secure-execution-strategies-and-ubos-solutions/)
- [Introducing LangSmith Sandboxes: Secure Code Execution for Agents](https://www.langchain.com/blog/introducing-langsmith-sandboxes-secure-code-execution-for-agents#why-sandboxes)
- [Notes on sandboxing untrusted code - why Python can't be sandboxed, comparing Firecracker/gVisor/WASM approaches · GitHub (résume la sandbox et montre ses limites)s](https://gist.github.com/mavdol/2c68acb408686f1e038bf89e5705b28c)

#### Divers:

- [Introducing smolagents: simple agents that write actions in code. (alternative pour tool call en code plutôt qu’en JSON)](https://huggingface.co/blog/smolagents)
- [agents.py - huggingface/smolagents · GitHub (un exemple d’agent, full codé avec sandbox pour avoir la vision globale)](https://github.com/huggingface/smolagents/blob/main/src/smolagents/agents.py)

### AI Usage Disclosure
In accordance with the 42 AI policy, AI tools were used as a pair-programming and review assistant across the following areas:
- Finding some resources.
- Drafting this README.
- Helping with the architecture of some parts of the code and files.
- Some utils functions and manual as well as the agent prompt were also made by AI
