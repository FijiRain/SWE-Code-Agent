from src.tools.path_utils import (get_testbed_root, resolve_testbed_path,
                                  to_display_path)
from pathlib import Path
import re
import ast


def get_clean_files(root: Path, pattern: str = "*.py") -> list[Path]:
    """Find all non-hidden, non-cache files matching pattern under root.

    Args:
        root: Base directory Path to search recursively.
        pattern: Glob pattern to match filenames against.

    Returns:
        A sorted list of matching file Paths.
    """
    files = []
    for p in root.rglob(pattern):
        if not p.is_file():
            continue
        if any(part.startswith(".") or part == "__pycache__"
               for part in p.parts):
            continue
        files.append(p)
    return sorted(files)


def search_code(pattern: str, file_pattern: str = "*") -> str:
    """Search files in the testbed for lines matching a regular expression.

    Args:
        pattern: Regular expression pattern to search for.
        file_pattern: Glob pattern to filter which files are searched.

    Returns:
        Matching lines formatted as '<filepath>:<line_num> <line>', or a
        message if no matches are found or the regex is invalid.
    """
    max_match = 100

    testbed_root = get_testbed_root()
    try:
        regex = re.compile(pattern)
    except re.error:
        return f"Error: Invalid regular expression '{pattern}'."

    files = get_clean_files(testbed_root, file_pattern)
    result = []
    for file in files:
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            for line_num, line in enumerate(lines, start=1):
                if regex.search(line):
                    result.append(f"{to_display_path(file)}:{line_num} {line}")
        except PermissionError:
            continue
    if not result:
        return f"No matches found for pattern '{pattern}'."
    warn_msg = ""
    if len(result) > max_match:
        result = result[:max_match]
        warn_msg = (f"\n... [Truncated: showing first {max_match} matches. "
                    "Please refine your search pattern.]")

    return ("\n".join(r for r in result) + warn_msg)


def search_function_or_class_definition_in_code(name: str) -> str:
    """Find function, async function, or class definitions by name using AST.

    Args:
        name: Exact identifier of the function or class to locate.

    Returns:
        Definition locations formatted as '<filepath>:<line_num> <line>',
        or a message if no definition is found.
    """
    testbed_root = get_testbed_root()
    files = get_clean_files(testbed_root, "*.py")
    result = []
    for file in files:
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
            if name not in content:
                continue  # Skip the files if the word isn't in the file
            lines = content.splitlines()
        except PermissionError:
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue  # Skip files with syntax errors
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)) and node.name == name:
                line_num = node.lineno
                line_content = lines[line_num - 1]
                result.append(f"{to_display_path(file)}:{line_num} "
                              f"{line_content}")
    if not result:
        return f"No definition found for '{name}'."

    return ("\n".join(r for r in result))


def find_references(name: str, filepath: str = "", line: int = -1) -> str:
    """Find word-boundary references to a symbol across Python files.

    Args:
        name: Symbol name to search for.
        filepath: Optional specific file path to restrict the search to.
        line: Optional line number in filepath to exclude from results.

    Returns:
        Reference locations formatted as '<filepath>:<line_num> <line>',
        or an error/status message string.
    """
    max_match = 100

    if not name or not name.strip():
        return "Error: name cannot be empty."

    if filepath:
        path = resolve_testbed_path(filepath)
        if not path or not path.is_file():
            return f"Error: {path} is not a file or do not exist"
        files = [path]
    else:
        files = get_clean_files(get_testbed_root(), "*.py")

    pattern = r"\b" + re.escape(name) + r"\b"
    regex = re.compile(pattern)
    result = []
    for file in files:
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
            if name not in content:
                continue
        except PermissionError:
            continue

        lines = content.splitlines()
        for line_num, line_content in enumerate(lines, start=1):
            if filepath and line_num == line:
                continue
            if regex.search(line_content):
                result.append(f"{to_display_path(file)}:{line_num} "
                              f"{line_content}")

    if not result:
        return f"No references found for '{name}'."
    warn_msg = ""
    if len(result) > max_match:
        result = result[:max_match]
        warn_msg = (f"\n... [Truncated: showing first {max_match} matches. "
                    "Please refine your search pattern.]")

    return ("\n".join(r for r in result) + warn_msg)
