"""Command-line entry point to run the agent on an MBPP task."""
import sys
from fire import Fire
from src.launcher import run_MBPP


def main() -> None:
    """Run the MBPP launcher from the command line and report errors."""
    try:
        Fire(run_MBPP)
    except Exception as e:
        print(f"ERROR - {e.__class__.__name__} :\n"
              f"{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
