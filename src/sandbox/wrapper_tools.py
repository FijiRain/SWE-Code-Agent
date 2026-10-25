from .McpClient import ToolSpec
from .McpClient import McpToolError

from typing import Callable, Tuple, Dict, List, Any
from multiprocessing.connection import Connection
from pydantic import BaseModel, Field

TYPES = {
    "integer": int,
    "string": str,
    "number": (int, float),
    "boolean": bool,
    "array": (list, tuple),
    "object": dict,
    "null": type(None),
}


class WorkerToolMessageOutput(BaseModel):
    name: str = Field(default="", description="name of tool")
    args: Dict[str, Any] = Field(
        default_factory=dict,
        description="argument for tool"
    )


class WorkerToolMessageIntput(BaseModel):
    error: bool = Field(default=False, description="If error ar occured")
    output: str = Field(default="", description="output of calling tool")


def signature(spec: ToolSpec) -> str:
    props = spec.input_schema.get("properties", {})
    params = ", ".join(f"{n}: {p.get('type', 'any')}" for n, p
                       in props.items())
    return f"{spec.name}({params})"


def check_type(arg: Any, schema: Dict) -> bool:
    expected = schema.get("type")
    if isinstance(expected, str):
        expected = [expected]
    if not expected or any(t not in TYPES for t in expected):
        return True
    if isinstance(arg, bool) and "boolean" not in expected:
        return False
    if "integer" in expected and isinstance(arg, float) and arg.is_integer():
        return True
    return any(isinstance(arg, TYPES[t]) for t in expected)


def verif_params(
        args: Tuple,
        kwargs: Dict,
        names: List,
        required: List,
        spec: ToolSpec
        ) -> Dict:
    if (len(kwargs) + len(args) > len(names)):
        raise TypeError(
            "Too many arguments: "
            f"{signature(spec)}"
        )
    result = {}
    for idx, arg in enumerate(args):
        if check_type(arg, spec.input_schema["properties"][names[idx]]):
            result[names[idx]] = arg
        else:
            raise TypeError(
                f"{names[idx]} must be "
                f"{spec.input_schema['properties'][names[idx]]['type']}"
            )

    for name, arg in kwargs.items():
        if name in result:
            raise TypeError(f"{signature(spec)} "
                            f"got multiple values for '{name}'")
        if name not in names:
            raise TypeError(
                f"Invalid argument: {name}"
            )
        if check_type(arg, spec.input_schema["properties"][name]):
            result[name] = arg
        else:
            raise TypeError(
                f"{name} must be "
                f"{spec.input_schema['properties'][name]['type']}"
            )
    missing_arg = []
    for name in required:
        if name not in result.keys():
            missing_arg.append(name)
    if missing_arg:
        quoted_args = [f"'{arg}'" for arg in missing_arg]
        string_error = (
            f"missing {len(missing_arg)} required positional "
            f"argument: {', '.join(quoted_args[:-1])} and "
            f"{quoted_args[-1]}"
        )
        if len(missing_arg) <= 1:
            string_error = (
                f"missing {len(missing_arg)} required positional "
                f"argument: '{''.join(missing_arg)}'"
            )
        raise TypeError(string_error)

    return result


def make_tools_wrapper(spec: ToolSpec, conn: Connection) -> Callable[..., Any]:
    names = list(spec.input_schema.get("properties", {}))
    required = spec.input_schema.get("required", [])

    def wrapper(*args, **kwargs):
        tool_args = verif_params(args, kwargs, names, required, spec)
        ouptut = WorkerToolMessageOutput(
            name=spec.name,
            args=tool_args
        )
        conn.send(("tool_call", ouptut))
        kind, response = conn.recv()
        if kind != "tool_result" or not isinstance(
                                        response, WorkerToolMessageIntput):
            raise RuntimeError("Unexpected message from the sandbox: "
                               f"{kind!r}")
        if response.error:
            raise McpToolError(response.output)
        return response.output

    wrapper.__name__ = spec.name
    return wrapper