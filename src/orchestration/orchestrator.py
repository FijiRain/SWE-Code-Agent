import os
import time
from openai import (OpenAI, APIStatusError,
                    APIConnectionError, APITimeoutError)
from openai.types.chat import ChatCompletionMessageParam
from dataclasses import dataclass
from typing import Optional

from .key_manager import KeyManager
from .exception import (KeyQuotaError, ServerError,
                        FatalError, ProviderRequestError)
from src.models.input_data_models import MBPPTaskInput, SWEBenchTaskInput
from src.models.output_data_models import SolutionOutput, StepMetrics
from .prompts import build_mbpp_sys_prompt, build_mbpp_user_prompt
from .py_extractor import extract_code
from tests.test_ExecutionResult import ExecutionResult, MockSandbox  # TEMPORAIRE POUR TEST


@dataclass
class Limits:
    max_iterations: int
    max_input_tokens: int
    max_output_tokens: int
    timeout_seconds: float


MBPP_LIMITS = Limits(10, 6000, 1500, 120.0)
SWE_LIMITS = Limits(30, 300000, 10000, 900.0)


class Orchestrator:
    """Manage LLM communication, provider resolution, and agent workflow."""

    def __init__(self, model: str, provider_url: str) -> None:
        """Initialize the orchestrator with model, provider, and state."""
        self.model = model
        self.provider_url = provider_url
        self.provider = self.load_provider(provider_url)
        self.key_manager = KeyManager(self.provider)

        self.sandbox = MockSandbox()  # Anatole ici JUSTE UN TEST
        self.sys_prompt = ""
        self.user_prompt = ""
        self.context: list[ChatCompletionMessageParam] = []

        self.step_retries = 0
        self.step_input_tokens = 0
        self.step_output_tokens = 0
        self.step_time = 0.0
        self.all_steps: list[StepMetrics] = []

    def load_provider(self, url: str) -> str:
        """Identify the matching provider environment variable from the URL."""
        format_url = url.lower()
        for key in os.environ:
            if (
                "API_KEY" in key
                and key.rsplit("_API_KEY", 1)[0].lower() in format_url
            ):
                return key
        raise ValueError("Provider not handled")

    def call_api(self) -> str:
        """Send a prompt to the LLM and map API errors to domain exceptions."""
        try:
            with OpenAI(
                base_url=self.provider_url,
                api_key=self.key_manager.get_key()
            ) as client:
                start_time = time.perf_counter()
                response = client.chat.completions.create(
                    model=self.model,
                    messages=self.context,
                    stop=["Observation:", "Observation\n"]
                )
                end_time = time.perf_counter()
                self.step_time = (end_time - start_time) * 1000
                if response.usage:
                    self.step_input_tokens = response.usage.prompt_tokens
                    self.step_output_tokens = response.usage.completion_tokens

                return response.choices[0].message.content or ""

        except APIStatusError as e:
            status = e.status_code
            if status in (401, 402, 403, 429):
                raise KeyQuotaError(
                    f"Quota or rate limit exceeded ({status}): {e}") from e
            elif 500 <= status < 600:
                raise ServerError(
                    f"Server error ({status}): {e}") from e
            else:
                raise FatalError(
                    f"Unrecoverable client error ({status}): {e}") from e

        except (APIConnectionError, APITimeoutError) as e:
            raise ServerError(f"Network/connection error: {e}") from e

        except Exception as e:
            raise FatalError(f"Unexpected error: {e}") from e

    def query_llm(self) -> str:
        """Query the LLM with retry logic, key rotation, and error handling."""
        self.step_retries = 0
        self.step_input_tokens = 0
        self.step_output_tokens = 0
        self.step_time = 0

        max_server_retries = 3
        server_retries = 0

        while True:
            try:
                content = self.call_api()
                # In case there's a minute-rate limit on key
                self.key_manager.reset_attempt()
                return content

            except KeyQuotaError:
                self.step_retries += 1
                try:
                    self.key_manager.rotate()
                except ValueError as quota_err:
                    raise KeyQuotaError(
                        "All provider API keys have "
                        "been exhausted.") from quota_err

            except ServerError:
                server_retries += 1
                self.step_retries += 1
                if server_retries > max_server_retries:
                    raise
                time.sleep(5)
                # si erreur de serveur, on peut regarder le status_code
                # renvoyé et dans la classe ServerError
                # determiner le temps auquel la requete HTTP
                # indique qu'il faut retry

            except FatalError:
                raise

    def complete_task(self,
                      task: MBPPTaskInput | SWEBenchTaskInput
                      ) -> SolutionOutput:
        """Execute the agentic loop to solve the task and return solution."""

        self.all_steps.clear()
        self.build_context(task)

        if isinstance(task, MBPPTaskInput):
            limits = MBPP_LIMITS
            benchmark_type = "mbpp"
            id_bench = str(task.task_id)
        else:
            limits = SWE_LIMITS
            benchmark_type = "swebench"
            id_bench = str(task.instance_id)

        # ouvrir la sandbox avec with ici ? + finally avec le close()
        '''#_#_#_# AGENT LOOP START #_#_#_#'''
        solved = False
        start_time = time.time()
        current_iterations = 0
        solution = ""
        error = None
        while current_iterations < limits.max_iterations and not solved:
            current_iterations += 1
            try:
                answer = self.query_llm()
            except ProviderRequestError as e:
                error = str(e)
                break
            self.context.append({"role": "assistant", "content": answer})
            sandbox_input = extract_code(answer)
            if sandbox_input is None:
                sandbox_input = ""
                sandbox_output = ("Error: No valid Python code block found. "
                                  "Wrap your code in ```python ... ```.")
            else:
                execution_res: ExecutionResult = self.sandbox.execute(sandbox_input)  # try/except pour la sandbox ??
                if execution_res.final_answer is not None:
                    solved = True
                    solution = execution_res.final_answer
                sandbox_output = self.sandbox_analysis(execution_res)

            self.context.append({"role": "user",
                                 "content": f"Observation:\n{sandbox_output}"})
            # resumer l'historique pour SWE eventuellement

            step = StepMetrics(
                step=current_iterations,
                input_tokens=self.step_input_tokens,
                output_tokens=self.step_output_tokens,
                request_time_ms=self.step_time,
                api_url=self.provider_url,
                model_name=self.model,
                llm_output=answer,
                sandbox_input=sandbox_input,
                sandbox_output=sandbox_output,
                retries=self.step_retries
            )
            self.all_steps.append(step)

            stop, error = self.stop_loop(iterations=len(self.all_steps),
                                         input_tok=sum(s.input_tokens
                                                       for s
                                                       in self.all_steps),
                                         output_tok=sum(s.output_tokens
                                                        for s
                                                        in self.all_steps),
                                         time=time.time() - start_time,
                                         limits=limits,
                                         solved=solved)
            if stop:
                break
        '''#_#_#_# AGENT LOOP END #_#_#_#'''

        total_time = time.time() - start_time
        return SolutionOutput(task_id=id_bench,
                              benchmark=benchmark_type,
                              success=solved,
                              solution=solution,
                              iterations=len(self.all_steps),
                              total_requests=len(self.all_steps)
                              + sum(s.retries for s in self.all_steps),
                              total_input_tokens=sum(s.input_tokens
                                                     for s in self.all_steps),
                              total_output_tokens=sum(s.output_tokens
                                                      for s in self.all_steps),
                              total_time_seconds=total_time,
                              steps=self.all_steps,
                              system_prompt=self.sys_prompt,
                              error=error if not solved else None,
                              )

    def build_context(self, task: MBPPTaskInput | SWEBenchTaskInput) -> None:
        if isinstance(task, MBPPTaskInput):
            # Attention il faudra mettre le manual en arg du sys prompt, la c par defaut
            self.sys_prompt = build_mbpp_sys_prompt()
            self.user_prompt = build_mbpp_user_prompt(task)
        else:
            # A implémenter pour SWE, str vide pour Pylance
            self.sys_prompt = ""
            self.user_prompt = ""

        self.context = [{"role": "system", "content": self.sys_prompt},
                        {"role": "user", "content": self.user_prompt}]

    def stop_loop(self, iterations: int,
                  input_tok: int,
                  output_tok: int,
                  time: float,
                  limits: Limits,
                  solved: bool) -> tuple[bool, Optional[str]]:
        if solved:
            return True, None
        if iterations >= limits.max_iterations:
            return True, "Max iterations limit reached"
        if input_tok >= limits.max_input_tokens:
            return True, "Max input tokens exceeded"
        if output_tok >= limits.max_output_tokens:
            return True, "Max output tokens exceeded"
        if time >= limits.timeout_seconds:
            return True, "Execution timeout exceeded"

        return False, None

    def sandbox_analysis(self, sandbox_output: ExecutionResult) -> str:
        if sandbox_output.timed_out:
            if sandbox_output.stdout:
                return (f"Execution timed out (infinite loop/slow algorithm). "
                        f"Current output:\n{sandbox_output.stdout}")
            # if the execution timeout without stdout
            return "Execution timed out (infinite loop/slow algorithm)."
        if sandbox_output.error:
            if sandbox_output.stdout:
                return (f"Error:\n{sandbox_output.error}\n"
                        f"Current output:\n{sandbox_output.stdout}")
            # if the execution fails immediately without stdout
            return f"Error:\n{sandbox_output.error}"
        if sandbox_output.final_answer is not None:
            return f"Final answer submitted:\n{sandbox_output.final_answer}"
        if sandbox_output.truncated:
            return (f"The output was truncated.\n"
                    f"Current output:\n{sandbox_output.stdout}")
        if sandbox_output.stdout:
            return sandbox_output.stdout

        # Cover the case when the LLM forget to write "print(result)"
        return ("Code executed successfully with no output return. "
                "Remember to use print() to see results.")
