from src.tools.path_utils import resolve_testbed_path, get_testbed_root


def read_file(filepath: str, start_line: int = 1, end_line: int = -1) -> str:
    """Read lines from a file within the testbed with 1-indexed line numbers.

    Args:
        filepath: Path to the file relative to the testbed root.
        start_line: First line number to read (1-indexed, inclusive).
        end_line: Last line number to read (inclusive), or -1 for end of file.

    Returns:
        Numbered file lines formatted as '<line_num>: <line>', or an error
        message string.
    """
    try:
        path = resolve_testbed_path(filepath)
    except ValueError as e:
        return f"Error: {e}"

    if not path.exists():
        return f"Error: File not found at '{filepath}'"

    if not path.is_file():
        return f"Error: '{filepath}' is not a file"

    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()

    if not lines:
        return f"{filepath} is empty"

    total_lines = len(lines)
    start_line = max(1, start_line)  # in case the user give me a start line<1
    if start_line > total_lines:
        return (f"Error: start_line ({start_line}) is greater than total lines"
                f" ({total_lines}).")
    if end_line == -1 or end_line > total_lines:
        end_line = total_lines

    if start_line > end_line:
        return (f"Error: start_line ({start_line}) is greater than end_line "
                f"({end_line}).")

    selected_lines = lines[start_line - 1:end_line]
    result = ("\n".join(f"{line_num}: {line}"
              for line_num, line in enumerate(selected_lines,
                                              start=start_line)))

    return result


def edit_file(filepath: str, old_str: str, new_str: str) -> str:
    """Replace a unique occurrence of old_str with new_str in a file.

    Args:
        filepath: Path to the file relative to the testbed root.
        old_str: Exact target substring to replace (must occur once).
        new_str: Replacement substring.

    Returns:
        A confirmation message upon success, or an error message string.
    """
    try:
        path = resolve_testbed_path(filepath)
    except ValueError as e:
        return f"Error: {e}"

    if not path.exists():
        return f"Error: File not found at '{filepath}'"

    if not path.is_file():
        return f"Error: '{filepath}' is not a file"

    if not old_str:
        return "Error: old_str is empty"

    content = path.read_text(encoding="utf-8", errors="replace")
    count = content.count(old_str)
    if count == 0:
        return (f"Error: Target string not found in '{filepath}'. "
                "Make sure whitespace and indentation match exactly.")
    if count > 1:
        return (f"Error: Target string appears {count} times in '{filepath}'. "
                "Please provide more surrounding context lines to make the "
                "replacement unique.")
    new_content = content.replace(old_str, new_str, 1)
    path.write_text(new_content, encoding="utf-8")
    return (f"Successfully updated '{filepath}'.")


def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List non-hidden files in a directory matching a glob pattern.

    Args:
        directory: Directory path relative to the testbed root.
        pattern: Glob pattern to filter file names.

    Returns:
        Newline-separated relative file paths (up to 100 entries), or an
        error/status message string.
    """
    try:
        path = resolve_testbed_path(directory)
    except ValueError as e:
        return f"Error: {e}"

    if not path.exists():
        return f"Error: Directory not found at '{directory}'"

    if not path.is_dir():
        return f"Error: '{directory}' is not a directory"

    files = []
    for p in path.rglob(pattern):
        if not p.is_file():
            continue
        if any(part.startswith(".") or part == "__pycache__" for
               part in p.parts):
            continue
        files.append(p)
    if not files:
        return (f"No files matching '{pattern}' found in '{directory}'.")
    files = sorted(files)

    total_count = len(files)
    max_results = 100
    warn_msg = ""
    if total_count > max_results:
        files = files[:max_results]
        warn_msg = (f"\n... [Showing first {max_results} of {total_count} "
                    "files. Use a more specific subfolder or pattern.]")

    result = "\n".join(str(p.relative_to(get_testbed_root())) for p in files)
    return result + warn_msg
