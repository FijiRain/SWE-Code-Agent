from .models.input_data_models import MBPPTaskInput, SWEBenchTaskInput
from .prompts import PROMPT_MBPP, PROMPT_SWE


class ReactLoop():
    def __init__(self, task: MBPPTaskInput | SWEBenchTaskInput) -> None:
        self.task_type = task
        self.sys_prompt = self.base_prompt()

    def base_prompt(self) -> str:
        if self.task_type == MBPPTaskInput:
            return PROMPT_MBPP
        else:
            return PROMPT_SWE


    
