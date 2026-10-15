from .sandbox.api import Sandbox
from .sandbox.SandboxConfig import load_config

sand = Sandbox(load_config("sandbox_template.json"))

result = sand.execute("print('a')")
print(result.stdout, end="")
# result = sand.execute("print(1/ 0)")
# print(result.error)
# result = sand.execute("final_answer('b')")
# print(result.final_answer)
