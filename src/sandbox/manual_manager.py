from .SandboxConfig import SandboxConfig
from .McpClient import ToolSpec

from pathlib import Path
from string import Template
from typing import Dict, List, Callable, Any
import inspect
import textwrap

TEMPLATE_PATH = Path(__file__).parent / "templates" / "manual_all_tool.txt"


JSON_TO_PY = {"string": "str", "integer": "int", "number": "float",
              "boolean": "bool", "object": "dict", "null": "None"}


def schema_type_to_str(schema: Dict) -> str:
    kind = schema.get("type")
    if isinstance(kind, list):
        return " | ".join(schema_type_to_str({**schema, "type": k})
                          for k in kind)
    if kind == "array":
        items = schema.get("items")
        return f"list[{schema_type_to_str(items)}]" if items else "list"
    return JSON_TO_PY.get(kind, "Any")


def format_prototype(spec: ToolSpec) -> str:
    props = spec.input_schema.get("properties", {})
    required = spec.input_schema.get("required", [])
    params = []
    for name, schema in props.items():
        text = f"{name}: {schema_type_to_str(schema)}"
        if name not in required:
            text += (
                f" = {schema['default']!r}"
                if "default" in schema else " = ..."
                )
        params.append(text)
    return f"{spec.name}({', '.join(params)})"


def format_tools(tools: Dict[str, ToolSpec], max_full: int = 3) -> str:
    specs = list(tools.values())
    blocks = []
    for spec in specs[:max_full]:
        doc = textwrap.indent(inspect.cleandoc(spec.description), "    ")
        blocks.append(format_prototype(spec) + (f"\n{doc}" if doc else ""))
    text = "\n\n".join(blocks)
    others = [format_prototype(s) for s in specs[max_full:]]
    if others:
        text += "\n\nOther tools:\n" + "\n".join(f"- {line}"
                                                 for line in others)
    return text


def format_imports(patterns: List[str]) -> str:
    wildcards = {p[:-2] for p in patterns if p.endswith(".*")}
    names = [p for p in patterns if not p.endswith(".*")]
    parts = [f"{n} (and its sub-modules)" if n in wildcards else n
             for n in names]
    parts += [f"{w}.*" for w in sorted(wildcards - set(names))]
    return ", ".join(parts)


def format_tool_help_line(tools: Dict[str, ToolSpec]) -> str:
    if not tools:
        return ""
    example = ", ".join(f'"{name}"' for name in list(tools)[:2])
    return (
        "To get the full description of some tools, call tool_help with "
        "a list of tool names. Example:\n"
        f"print(tool_help([{example}]))"
    )


def all_tools_doc(tools: Dict[str, ToolSpec]) -> str:
    result = []
    sep = "\n\n" + ("*" * 50) + "\n\n"
    for _, spec in tools.items():
        result.append(format_tool_doc(spec))
    return sep.join(result)


def render_manual(**value: str) -> str:
    template = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    return template.substitute(value).strip()


def build_manual(sand_conf: SandboxConfig, tools: Dict[str, ToolSpec]) -> str:
    return render_manual(
        time_limit=sand_conf.max_execution_time_seconds,
        memory_limit=sand_conf.max_memory_mb,
        charcter_limit_output=sand_conf.max_len_output,
        charcater_limit_tool=sand_conf.max_len_tool_output,
        imports=format_imports(sand_conf.authorized_imports),
        directories=", ".join(sand_conf.allowed_directories),
        restricted_builtin=", ".join(sand_conf.not_authorized_builtins),
        tools=format_tools(tools),
        tool_help_line=format_tool_help_line(tools),
        tools_lists=all_tools_doc(tools)
    )


def format_tool_doc(spec: ToolSpec) -> str:
    """Full documentation of one tool: prototype, description, parameters."""
    lines = [format_prototype(spec)]

    description = (inspect.cleandoc(spec.description)
                   if spec.description else "")
    if description:
        lines += ["", description]

    props = spec.input_schema.get("properties", {})
    required = spec.input_schema.get("required", [])
    if props:
        lines += ["", "Parameters:"]
        for name, schema in props.items():
            details = [schema_type_to_str(schema),
                       "required" if name in required else "optional"]
            if "default" in schema:
                details.append(f"default {schema['default']!r}")
            if "enum" in schema:
                values = ", ".join(repr(v) for v in schema["enum"])
                details.append(f"one of {values}")
            line = f"- {name} ({', '.join(details)})"
            if schema.get("description"):
                line += f": {schema['description']}"
            lines.append(line)

    return "\n".join(lines)


def make_tool_help(tools: Dict[str, ToolSpec]) -> Callable[..., Any]:
    example = list(tools)[:2]

    def tool_help(tools_name: List[str]) -> str:
        if not isinstance(tools_name, (list, tuple)):
            raise TypeError(
                "tool_help() takes a list of tool names, for example "
                f"tool_help({example!r}). "
                f"Got {type(tools_name).__name__}: {tools_name!r:.80}"
            )
        bad_type = [name for name in tools_name if not isinstance(name, str)]
        if bad_type:
            raise TypeError(
                "tool_help() takes a list of strings (tool names). "
                f"Found {type(bad_type[0]).__name__}: {bad_type[0]!r:.80}"
            )
        result = []
        for name in tools_name:
            spec = tools.get(name)
            if not spec:
                result.append(f"Unknown tool '{name}'. "
                              f"\n\nAvailable: {', '.join(tools)}")
                continue
            result.append(format_tool_doc(spec))
        return "\n\n**************\n\n".join(result)
    return tool_help
