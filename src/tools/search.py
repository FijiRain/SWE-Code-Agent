from src.tools.path_utils import get_testbed_root
from pathlib import Path
import re
import ast


def get_clean_files(root: Path, pattern: str = "*.py") -> list[Path]:
    """Finds all non-noise files matching pattern, sorted."""
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
                    result.append(f"{file.resolve()}:{line_num} {line}")
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
                result.append(f"{file.resolve()}:{line_num} {line_content}")
    if not result:
        return f"No definition found for '{name}'."

    return ("\n".join(r for r in result))
