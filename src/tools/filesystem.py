from src.tools.path_utils import resolve_testbed_path


def read_file(filepath: str, start_line: int = 1, end_line: int = -1) -> str:
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


def list_files(directory, pattern) -> None:
    pass
