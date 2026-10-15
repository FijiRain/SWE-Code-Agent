import io
from contextlib import redirect_stdout


def run(code: str, namespace: dict) -> str:
    buffer = io.StringIO()
    try:
        with redirect_stdout(buffer):
            exec(code, namespace)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"
    return buffer.getvalue()
