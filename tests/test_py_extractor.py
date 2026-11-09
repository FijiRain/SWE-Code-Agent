"""Unit tests for Python code extraction from LLM responses."""
from src.orchestration.py_extractor import (
    extract_code,
    extract_final_answer_call,
)


def test_standard_markdown_block() -> None:
    s = "Thought: testing\nCode:\n```python\nprint(1 + 1)\n```"
    assert extract_code(s) == "print(1 + 1)"


def test_final_answer_inside_block() -> None:
    s = "Thought: done\nCode:\n```python\nfinal_answer('hello')\n```"
    assert extract_code(s) == "final_answer('hello')"


def test_final_answer_outside_block() -> None:
    s = (
        "Thought: done\n"
        "Code:\n"
        "```python\n"
        "def foo():\n"
        "    return 42\n"
        "```\n"
        "</think>\n\n"
        "final_answer('''def foo():\n    return 42''')"
    )
    extracted = extract_code(s)
    assert extracted is not None
    assert "def foo():" in extracted
    assert "final_answer('''def foo():" in extracted


def test_only_final_answer() -> None:
    s = "Thought: done.\nfinal_answer('solution')"
    assert extract_code(s) == "final_answer('solution')"


def test_no_false_positive_in_thought() -> None:
    s = (
        "Thought: I will call final_answer(code) later.\n"
        "Code:\n"
        "```python\n"
        "print('step 1')\n"
        "```"
    )
    assert extract_code(s) == "print('step 1')"


def test_extract_final_answer_call_direct() -> None:
    call = extract_final_answer_call("final_answer('abc')")
    assert call == "final_answer('abc')"


def test_no_teleport_from_later_code_block() -> None:
    s = (
        "Thought: Read file.\n"
        "Code:\n"
        "```python\n"
        "print('reading')\n"
        "```Thought: Submit.\n"
        "Code:\n"
        "```python\n"
        "final_answer(' premature ')\n"
        "```"
    )
    assert extract_code(s) == "print('reading')"


if __name__ == "__main__":
    test_extract_final_answer_call_direct()
    test_standard_markdown_block()
    test_final_answer_inside_block()
    test_final_answer_outside_block()
    test_only_final_answer()
    test_no_false_positive_in_thought()
    test_no_teleport_from_later_code_block()
    print("All py_extractor tests passed!")
