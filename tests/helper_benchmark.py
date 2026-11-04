"""Helper to compute provider reliability and metrics from solution JSON."""
import json
import sys
from pathlib import Path


def analyze_file(filepath: Path) -> None:
    """Read a solution JSON file and print benchmark and reliability stats."""
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    task_id = data.get("task_id", "Unknown")
    benchmark = data.get("benchmark", "swebench")
    success = data.get("success", False)
    total_time = data.get("total_time_seconds", 0.0)
    in_tok = data.get("total_input_tokens", 0)
    out_tok = data.get("total_output_tokens", 0)
    steps = data.get("steps", [])

    model_name = (
        steps[0].get("model_name", "Unknown") if steps else "Unknown"
    )
    api_url = (
        steps[0].get("api_url", "Unknown") if steps else "Unknown"
    )

    # Provider reliability calculations
    total_retries = sum(s.get("retries", 0) for s in steps)
    total_requests = len(steps) + total_retries
    response_times = [s.get("request_time_ms", 0.0) for s in steps]
    avg_resp_ms = (
        sum(response_times) / len(response_times) if response_times else 0.0
    )
    avg_resp_s = avg_resp_ms / 1000.0

    # Availability: ratio of successful calls without retry over total attempts
    avail_pct = (
        (len(steps) / total_requests * 100.0) if total_requests > 0 else 100.0
    )

    print("=" * 60)
    print(f"BENCHMARK SUMMARY: {filepath.name}")
    print("=" * 60)
    print(f"Task ID:          {task_id} ({benchmark})")
    print(f"Model:            {model_name}")
    print(f"Provider URL:     {api_url}")
    print(f"Status:           {'PASSED' if success else 'FAILED'}")
    print(f"Iterations:       {len(steps)}")
    print(
        f"Tokens:           {in_tok:,} in / {out_tok:,} out "
        f"({in_tok + out_tok:,} total)"
    )
    print(f"Wall-Clock Time:  {total_time:.2f}s")
    print("-" * 60)
    print("PROVIDER RELIABILITY:")
    print(f"  Avg Response Time:    {avg_resp_ms:.1f} ms ({avg_resp_s:.2f}s)")
    print(f"  Total Retries:        {total_retries}")
    print(
        f"  Total API Requests:   {total_requests} "
        f"({len(steps)} steps + {total_retries} retries)"
    )
    print(f"  Provider Availability:{avail_pct:.1f}%")
    print("=" * 60)


def main() -> None:
    """Entrypoint: analyze default cache or path passed as CLI argument."""
    target = (
        sys.argv[1] if len(sys.argv) > 1 else "cache/swebench_solution.json"
    )
    p = Path(target)
    if p.is_dir():
        for json_file in sorted(p.glob("*.json")):
            analyze_file(json_file)
            print()
    else:
        analyze_file(p)


if __name__ == "__main__":
    main()
