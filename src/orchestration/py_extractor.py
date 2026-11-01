import io
import json
import re
import tokenize
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


def extract_final_answer_call(text: str) -> Optional[str]:
    """Extract a standalone final_answer(...) call from text."""
    match = re.search(r"(?:^|[\n>`])\s*(final_answer\s*\()", text)
    if not match:
        return None
    start = match.start(1)
    sub_text = text[start:]
    try:
        tokens = tokenize.generate_tokens(io.StringIO(sub_text).readline)
        paren_depth = 0
        end_row, end_col = None, None
        for tok in tokens:
            if tok.string == "(":
                paren_depth += 1
            elif tok.string == ")":
                paren_depth -= 1
                if paren_depth == 0:
                    end_row, end_col = tok.end
                    break
        if end_row is not None:
            lines = sub_text.splitlines(keepends=True)
            matched = (
                "".join(lines[:end_row - 1])
                + lines[end_row - 1][:end_col]
            )
            return matched.strip()
    except Exception:
        pass
    return None


def extract_code(answer: str) -> Optional[str]:
    """Extract executable Python code from various LLM output formats."""
    if not answer or not answer.strip():
        return None

    extracted: Optional[str] = None

    # Explicit Python Markdown block: ```python ... ``` or ```py ... ```
    py_md = re.search(
        r"```(?:python|py)\s*\n(.*?)```",
        answer,
        re.DOTALL | re.IGNORECASE
    )
    if py_md and py_md.group(1).strip():
        extracted = py_md.group(1).strip()
    else:
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
                extracted = extract_xml_tool_call(inner)
            else:
                extracted = inner
        else:
            # Generic Markdown block without language specifier: ``` ... ```
            gen_md = re.search(r"```\s*\n(.*?)```", answer, re.DOTALL)
            if gen_md and gen_md.group(1).strip():
                extracted = gen_md.group(1).strip()
            else:
                # Classic ReAct format: Action: tool_name / Action Input: {...}
                react_code = extract_react_action(answer)
                if react_code:
                    extracted = react_code

    # Fallback/safeguard: check for final_answer(...) call outside fences
    outside_fences = re.sub(r"```.*?```", "\n", answer, flags=re.DOTALL)
    final_call = extract_final_answer_call(outside_fences)
    if final_call:
        if extracted is None:
            return final_call
        if "final_answer" not in extracted:
            return f"{extracted}\n{final_call}"

    return extracted
