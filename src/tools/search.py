from src.tools.path_utils import get_testbed_root
import re


def search_code(pattern: str, file_pattern: str = "*") -> str:
    max_match = 100

    testbed_root = get_testbed_root()
    try:
        regex = re.compile(pattern)
    except re.error:
        return f"Error: Invalid regular expression '{pattern}'."

    files = []
    for p in testbed_root.rglob(file_pattern):
        if not p.is_file():
            continue
        if any(part.startswith(".") or part == "__pycache__" for
                part in p.parts):
            continue
        files.append(p)
    files = sorted(files)
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
