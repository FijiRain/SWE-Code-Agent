"""Build the manual given to the LLM and the tool_help() function."""
from ..models.SandboxConfig import SandboxConfig
from ..models.ToolSpec import ToolSpec
from .config import JSON_TO_PY, TEMPLATE_MANUAL_PATH

from string import Template
from typing import Dict, List, Callable, Any
import inspect
import textwrap


def schema_type_to_str(schema: Dict) -> str:
    """Convert the JSON schema type of a parameter to a Python type name.

    Type unions become "a | b", arrays become "list[...]" and unknown
    types become "Any".

    Args:
        schema: JSON schema of the parameter.
    """
    kind = schema.get("type")
    if isinstance(kind, list):
        return " | ".join(schema_type_to_str({**schema, "type": k})
                          for k in kind)
    if kind == "array":
        items = schema.get("items")
        return f"list[{schema_type_to_str(items)}]" if items else "list"
    return JSON_TO_PY.get(kind, "Any")


def format_prototype(spec: ToolSpec) -> str:
    """Return the Python-like prototype of a tool, e.g. "add(a: int)".

    Optional parameters get their default value, or "..." if the schema
    gives none.
    """
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
    """Describe the tools for the manual.

    The first max_full tools are shown with their description, the
    others only with their prototype.

    Args:
        tools: Tools indexed by name.
        max_full: Number of tools shown with their description.
    """
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
    """Return the authorized imports as a readable comma separated list.

    A module allowed both as "name" and "name.*" is shown once as
    "name (and its sub-modules)".
    """
    wildcards = {p[:-2] for p in patterns if p.endswith(".*")}
    names = [p for p in patterns if not p.endswith(".*")]
    parts = [f"{n} (and its sub-modules)" if n in wildcards else n
             for n in names]
    parts += [f"{w}.*" for w in sorted(wildcards - set(names))]
    return ", ".join(parts)


def format_tool_help_line(tools: Dict[str, ToolSpec]) -> str:
    """Return the manual line explaining tool_help(), empty if no tools."""
    if not tools:
        return ""
    example = ", ".join(f'"{name}"' for name in list(tools)[:2])
    return (
        "To get the full description of some tools, call tool_help with "
        "a list of tool names. Example:\n"
        f"print(tool_help([{example}]))"
    )


def all_tools_doc(tools: Dict[str, ToolSpec]) -> str:
    """Return the full documentation of every tool, separated by lines."""
    if not tools:
        return "No tools found"
    result = []
    sep = "\n\n" + ("*" * 50) + "\n\n"
    for _, spec in tools.items():
        result.append(format_tool_doc(spec))
    return sep.join(result)


def render_manual(**value: object) -> str:
    """Fill the manual template with the given values.

    Raises:
        KeyError: If a placeholder of the template has no value.
    """
    template = Template(TEMPLATE_MANUAL_PATH.read_text(encoding="utf-8"))
    return template.substitute(value).strip()


def build_manual(sand_conf: SandboxConfig, tools: Dict[str, ToolSpec]) -> str:
    """Build the sandbox manual from the configuration and the tools.

    Args:
        sand_conf: Sandbox configuration (limits, imports, directories).
        tools: MCP tools indexed by name.
    """
    return render_manual(
        time_limit=sand_conf.max_tool_time_seconds,
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
    """Build the tool_help() function exposed in the sandbox namespace.

    Args:
        tools: MCP tools indexed by name.
    """
    example = list(tools)[:2]

    def tool_help(tools_name: List[str]) -> str:
        """Return the full documentation of the given tools.

        Unknown names get a message listing the available tools.

        Raises:
            TypeError: If tools_name is not a list of strings.
        """
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
