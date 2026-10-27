import json
import re
from typing import Any, Optional


def format_tool_call(tool_name: str, raw_args: Any) -> str:
    """Convert a tool name and arguments into executable Python code."""
    name = tool_name.strip()
    if name.lower() in ("python", "python_interpreter", "code", "execute"):
        if isinstance(raw_args, dict) and "code" in raw_args:
            return str(raw_args["code"]).strip()
        return str(raw_args).strip()

    if isinstance(raw_args, dict):
        kwargs_str = ", ".join(f"{k}={repr(v)}" for k, v in raw_args.items())
        call_str = f"{name}({kwargs_str})"
    elif raw_args is None or raw_args == "":
        call_str = f"{name}()"
    else:
        call_str = f"{name}({repr(raw_args)})"

    if name == "final_answer":
        return call_str
    return f"print({call_str})"


def extract_react_action(answer: str) -> Optional[str]:
    """Extract and convert ReAct 'Action / Action Input' into Python code."""
    pattern = (
        r"Action\s*:\s*([^\n]+)\s*\n"
        r"Action\s+Input\s*:\s*(.+)"
    )
    match = re.search(pattern, answer, re.DOTALL | re.IGNORECASE)
    if not match:
        return None

    tool_name = match.group(1).strip()
    raw_input = match.group(2).strip()

    try:
        parsed_input = json.loads(raw_input)
    except json.JSONDecodeError:
        parsed_input = raw_input.strip("'\"")

    return format_tool_call(tool_name, parsed_input)


def extract_xml_tool_call(content: str) -> Optional[str]:
    """Parse XML <tool_call> JSON payload (Hermes/Qwen format) into Python."""
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "name" in data:
            args = data.get("arguments", data.get("parameters", {}))
            if isinstance(args, str):
                args = json.loads(args)
            return format_tool_call(data["name"], args)
    except json.JSONDecodeError:
        pass
    return content if content else None


def extract_code(answer: str) -> Optional[str]:
    """Extract executable Python code from various LLM output formats."""
    if not answer or not answer.strip():
        return None

    # Explicit Python Markdown block: ```python ... ``` or ```py ... ```
    py_md = re.search(
        r"```(?:python|py)\s*\n(.*?)```",
        answer,
        re.DOTALL | re.IGNORECASE
    )
    if py_md and py_md.group(1).strip():
        return py_md.group(1).strip()

    # XML tags: <code>...</code>, <python>...</python>, <tool_call>...
    xml_match = re.search(
        r"<(code|python|tool_call)>\s*(.*?)\s*</\1>",
        answer,
        re.DOTALL | re.IGNORECASE
    )
    if xml_match and xml_match.group(2).strip():
        tag = xml_match.group(1).lower()
        inner = xml_match.group(2).strip()
        if tag == "tool_call":
            return extract_xml_tool_call(inner)
        return inner

    # Generic Markdown block without language specifier: ``` ... ```
    gen_md = re.search(r"```\s*\n(.*?)```", answer, re.DOTALL)
    if gen_md and gen_md.group(1).strip():
        return gen_md.group(1).strip()

    # Classic ReAct format: Action: tool_name / Action Input: {...}
    react_code = extract_react_action(answer)
    if react_code:
        return react_code

    return None
