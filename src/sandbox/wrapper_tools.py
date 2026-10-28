"""Wrappers that expose MCP tools as Python functions in the worker."""
from ..models.ToolSpec import ToolSpec
from .McpClient import McpToolError
from .protocol import (
    ToolCallMsg, ToolResultMsg,
    recv_main_message, send_message
    )

from typing import Callable, Tuple, Dict, List, Any
from multiprocessing.connection import Connection

TYPES: Dict[str, type | Tuple[type, ...]] = {
    "integer": int,
    "string": str,
    "number": (int, float),
    "boolean": bool,
    "array": (list, tuple),
    "object": dict,
    "null": type(None),
}


def signature(spec: ToolSpec) -> str:
    """Return a readable signature of the tool, e.g. "add(a: integer)"."""
    props = spec.input_schema.get("properties", {})
    params = ", ".join(f"{n}: {p.get('type', 'any')}" for n, p
                       in props.items())
    return f"{spec.name}({params})"


def check_type(arg: Any, schema: Dict) -> bool:
    """Check that an argument matches the JSON schema type of a parameter.

    Unknown or missing types are accepted, booleans are only accepted for
    "boolean", and a float with no decimal part is accepted for "integer".

    Args:
        arg: Value given by the code.
        schema: JSON schema of the parameter.

    Returns:
        True if the value has an expected type.
    """
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
    """Bind positional and keyword arguments to the tool parameters.

    Args:
        args: Positional arguments given by the code.
        kwargs: Keyword arguments given by the code.
        names: Parameter names, in schema order.
        required: Names of the required parameters.
        spec: Specification of the tool.

    Returns:
        The arguments indexed by parameter name.

    Raises:
        TypeError: If there are too many, unknown, duplicated or missing
            arguments, or if an argument has the wrong type.
    """
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
    """Build a function that calls an MCP tool from the worker.

    The function checks its arguments, sends a "tool_call" message to the
    main process and waits for the "tool_result" answer.

    Args:
        spec: Specification of the tool.
        conn: Pipe connection to the main process.

    Returns:
        A function named like the tool, returning the tool text output.
    """
    names = list(spec.input_schema.get("properties", {}))
    required = spec.input_schema.get("required", [])

    def wrapper(*args: Any, **kwargs: Any) -> str:
        """Call the MCP tool through the main process.

        Raises:
            TypeError: If the arguments do not match the tool schema.
            McpToolError: If the tool reports an error.
            RuntimeError: If the main process sends an unexpected message.
        """
        tool_args = verif_params(args, kwargs, names, required, spec)
        try:
            send_message(conn, ToolCallMsg(name=spec.name, args=tool_args))
        except (ValueError, TypeError) as e:
            raise TypeError(
                f"{spec.name}(): arguments must be JSON-serializable "
                "(str, int, float, bool, None, list, dict)"
            ) from e
        message = recv_main_message(conn)
        if not isinstance(message, ToolResultMsg):
            raise RuntimeError(
                "Unexpected message from the sandbox: "
                f"{message!r}"
            )
        if message.error:
            raise McpToolError(message.output)
        return message.output

    wrapper.__name__ = spec.name
    return wrapper
