from fire import Fire
from src.launcher import run_MBPP


def main() -> None:
    try:
        Fire(run_MBPP)
    except Exception as e:
        print(f"ERROR - {e.__class__.__name__} :\n"
              f"{e}")


if __name__ == "__main__":
    main()
