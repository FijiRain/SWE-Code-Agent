from fire import Fire
from src.launcher import run_SWE


def main() -> None:
    try:
        Fire(run_SWE)
    except Exception as e:
        print(f"ERROR - {e.__class__.__name__} :\n"
              f"{e}")


if __name__ == "__main__":
    main()
