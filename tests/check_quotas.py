"""Check remaining API quotas and key health across Groq, OpenRouter, Google.

Usage examples:
  uv run python tests/check_quotas.py
  uv run python tests/check_quotas.py --groq-model "openai/gpt-oss-120b"
  uv run python tests/check_quotas.py --google-model "gemini-3.1-pro-preview"
  uv run python tests/check_quotas.py --provider groq --model "qwen/qwen3-32b"
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
import requests

load_dotenv()

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _mask_key(key: str) -> str:
    """Return a masked version of an API key for safe display."""
    if len(key) <= 10:
        return "***"
    return f"{key[:6]}...{key[-4:]}"


def _load_keys(env_var: str) -> List[str]:
    """Load comma-separated API keys from an environment variable."""
    raw = os.environ.get(env_var, "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def _check_single_groq(idx: int, key: str, model: str) -> Dict[str, Any]:
    """Query Groq with a 1-token request to inspect ratelimit headers."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    try:
        r = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "1"}],
                "max_tokens": 1,
            },
            timeout=10,
        )
        rem_tok = int(r.headers.get("x-ratelimit-remaining-tokens", 0))
        lim_tok = int(r.headers.get("x-ratelimit-limit-tokens", 0))
        rem_req = int(r.headers.get("x-ratelimit-remaining-requests", 0))
        lim_req = int(r.headers.get("x-ratelimit-limit-requests", 0))
        rst_req = r.headers.get("x-ratelimit-reset-requests", "-")
        return {
            "idx": idx,
            "masked": _mask_key(key),
            "status": r.status_code,
            "rem_tok": rem_tok,
            "lim_tok": lim_tok,
            "rem_req": rem_req,
            "lim_req": lim_req,
            "reset": rst_req,
            "error": "" if r.status_code == 200 else r.text[:80],
        }
    except Exception as e:
        return {
            "idx": idx,
            "masked": _mask_key(key),
            "status": 0,
            "rem_tok": 0,
            "lim_tok": 0,
            "rem_req": 0,
            "lim_req": 0,
            "reset": "-",
            "error": str(e)[:80],
        }


def _check_single_openrouter(idx: int, key: str) -> Dict[str, Any]:
    """Query OpenRouter /api/v1/key endpoint (zero token cost)."""
    url = "https://openrouter.ai/api/v1/key"
    try:
        r = requests.get(
            url,
            headers={"Authorization": f"Bearer {key}"},
            timeout=10,
        )
        if r.status_code != 200:
            return {
                "idx": idx,
                "masked": _mask_key(key),
                "status": r.status_code,
                "rem_req": 0,
                "lim_req": 0,
                "used_req": 0,
                "error": r.text[:80],
            }
        data = r.json().get("data", {})
        free_info = data.get("free_model_daily_requests") or {}
        return {
            "idx": idx,
            "masked": _mask_key(key),
            "status": 200,
            "rem_req": int(free_info.get("remaining", 0)),
            "lim_req": int(free_info.get("limit", 0)),
            "used_req": int(free_info.get("used", 0)),
            "error": "",
        }
    except Exception as e:
        return {
            "idx": idx,
            "masked": _mask_key(key),
            "status": 0,
            "rem_req": 0,
            "lim_req": 0,
            "used_req": 0,
            "error": str(e)[:80],
        }


def _check_single_google(idx: int, key: str, model: str) -> Dict[str, Any]:
    """Query Google AI Studio with a 1-token test to verify key & quota."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta/openai/"
        "chat/completions"
    )
    try:
        r = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "1"}],
                "max_tokens": 1,
            },
            timeout=12,
        )
        err_msg = ""
        if r.status_code != 200:
            try:
                err_msg = r.json()[0]["error"]["message"][:70]
            except Exception:
                err_msg = r.text[:70]
        return {
            "idx": idx,
            "masked": _mask_key(key),
            "status": r.status_code,
            "error": err_msg,
        }
    except Exception as e:
        return {
            "idx": idx,
            "masked": _mask_key(key),
            "status": 0,
            "error": str(e)[:70],
        }


def print_groq_report(model: str) -> None:
    """Run parallel checks for all GROQ_API_KEYS and print a summary table."""
    keys = _load_keys("GROQ_API_KEYS")
    print(f"\n{BOLD}{CYAN}=== 1. GROQ ({len(keys)} keys) "
          f"| Model: {model} ==={RESET}")
    if not keys:
        print(f"  {RED}No keys found in GROQ_API_KEYS{RESET}")
        return

    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        results = list(
            pool.map(
                lambda p: _check_single_groq(p[0], p[1], model),
                enumerate(keys, 1),
            )
        )

    print(f"  {'Key #':<6} {'Key ID':<15} {'Status':<10} "
          f"{'Tokens/min (TPM)':<20} {'Reqs/day (RPD)':<18} {'Reset RPD'}")
    print("  " + "-" * 78)

    total_tok = 0
    total_req = 0
    active_count = 0
    for res in results:
        st = res["status"]
        color = GREEN if st == 200 else (YELLOW if st == 429 else RED)
        if st == 200:
            active_count += 1
        total_tok += res["rem_tok"]
        total_req += res["rem_req"]
        tpm_str = f"{res['rem_tok']} / {res['lim_tok']}"
        rpd_str = f"{res['rem_req']} / {res['lim_req']}"
        print(f"  #{res['idx']:<5} {res['masked']:<15} "
              f"{color}HTTP {st:<5}{RESET} "
              f"{tpm_str:<20} {rpd_str:<18} {res['reset']}")

    print("  " + "-" * 78)
    print(f"  {BOLD}TOTAL GROQ AVAILABLE:{RESET} "
          f"{GREEN}{active_count}/{len(keys)} active keys{RESET} | "
          f"Instant TPM: {BOLD}{total_tok}{RESET} tokens | "
          f"Daily Requests left: {BOLD}{total_req}{RESET}")


def print_openrouter_report() -> None:
    """Run parallel checks for all OPENROUTER_API_KEYS and print summary."""
    keys = _load_keys("OPENROUTER_API_KEYS")
    print(f"\n{BOLD}{CYAN}=== 2. OPENROUTER ({len(keys)} keys) "
          f"| Free Tier Daily Quota ==={RESET}")
    if not keys:
        print(f"  {RED}No keys found in OPENROUTER_API_KEYS{RESET}")
        return

    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        results = list(
            pool.map(
                lambda p: _check_single_openrouter(p[0], p[1]),
                enumerate(keys, 1),
            )
        )

    print(f"  {'Key #':<6} {'Key ID':<15} {'Status':<10} "
          f"{'Free Reqs Remaining (Daily)':<30} {'Used Today'}")
    print("  " + "-" * 72)

    total_rem = 0
    active_count = 0
    for res in results:
        st = res["status"]
        rem = res["rem_req"]
        color = GREEN if (st == 200 and rem > 0) else RED
        if st == 200 and rem > 0:
            active_count += 1
        total_rem += rem
        req_str = f"{rem} / {res['lim_req']}"
        print(f"  #{res['idx']:<5} {res['masked']:<15} "
              f"{color}HTTP {st:<5}{RESET} "
              f"{req_str:<30} {res['used_req']}")

    print("  " + "-" * 72)
    print(f"  {BOLD}TOTAL OPENROUTER AVAILABLE:{RESET} "
          f"{GREEN}{active_count}/{len(keys)} active keys{RESET} | "
          f"Daily Free Requests left: {BOLD}{total_rem}{RESET}")


def print_google_report(model: str) -> None:
    """Run parallel checks for all GOOGLE_API_KEYS and print summary."""
    keys = _load_keys("GOOGLE_API_KEYS")
    print(f"\n{BOLD}{CYAN}=== 3. GOOGLE AI STUDIO ({len(keys)} keys) "
          f"| Model: {model} ==={RESET}")
    print("  (Note: Google does not expose token counters in HTTP headers; "
          "testing live availability per key)")
    if not keys:
        print(f"  {RED}No keys found in GOOGLE_API_KEYS{RESET}")
        return

    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        results = list(
            pool.map(
                lambda p: _check_single_google(p[0], p[1], model),
                enumerate(keys, 1),
            )
        )

    print(f"  {'Key #':<6} {'Key ID':<15} {'Status':<12} {'Details'}")
    print("  " + "-" * 72)

    active_count = 0
    for res in results:
        st = res["status"]
        if st == 200:
            active_count += 1
            color = GREEN
            detail = "Quota OK (Ready)"
        elif st == 429:
            color = YELLOW
            detail = "Quota / Rate-limit reached (429)"
        else:
            color = RED
            detail = res["error"] or f"Failed (HTTP {st})"
        print(f"  #{res['idx']:<5} {res['masked']:<15} "
              f"{color}HTTP {st:<7}{RESET} {detail}")

    print("  " + "-" * 72)
    print(f"  {BOLD}TOTAL GOOGLE AVAILABLE:{RESET} "
          f"{GREEN}{active_count}/{len(keys)} keys ready{RESET} "
          f"(~1,500 RPD / key on Flash free tier)\n")


def main() -> None:
    """Parse CLI arguments and display quota status across providers."""
    parser = argparse.ArgumentParser(
        description="Check remaining API quotas across all configured keys."
    )
    parser.add_argument(
        "--provider",
        choices=["all", "groq", "openrouter", "google"],
        default="all",
        help="Provider to check (default: all)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override model name for the selected provider",
    )
    parser.add_argument(
        "--groq-model",
        type=str,
        default="qwen/qwen3.8-27b",
        help="Model to test on Groq (default: qwen/qwen3.8-27b)",
    )
    parser.add_argument(
        "--google-model",
        type=str,
        default="gemini-3-flash-preview",
        help="Model to test on Google (default: gemini-3-flash-preview)",
    )
    args = parser.parse_args()

    groq_model = args.model if args.provider == "groq" and args.model else (
        args.groq_model
    )
    google_model = (
        args.model if args.provider == "google" and args.model else (
            args.google_model
        )
    )

    if args.provider in ("all", "groq"):
        print_groq_report(groq_model)
    if args.provider in ("all", "openrouter"):
        print_openrouter_report()
    if args.provider in ("all", "google"):
        print_google_report(google_model)


if __name__ == "__main__":
    main()
