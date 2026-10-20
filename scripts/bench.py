import json
import time
from pathlib import Path

from ismypwdsafe import analyze_password

# Load cases from the golden file to ensure we benchmark realistic inputs
GOLDEN_DIR = Path(__file__).parent.parent / "tests" / "golden"
CASES_PATH = GOLDEN_DIR / "cases.json"

def main():
    if not CASES_PATH.exists():
        print("Run scripts/generate_golden.py first.")
        return

    with open(CASES_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    # Run once to warm up
    for pwd in cases:
        analyze_password(pwd, check_breach=False)

    start = time.perf_counter()
    for _ in range(10):  # 10 iterations over all cases
        for pwd in cases:
            analyze_password(pwd, check_breach=False)
    end = time.perf_counter()

    total_runs = len(cases) * 10
    avg_time = (end - start) / total_runs

    out_dir = Path(__file__).parent.parent / "bench"
    out_dir.mkdir(exist_ok=True)
    
    result = {
        "cases": len(cases),
        "iterations": 10,
        "total_runs": total_runs,
        "total_time_seconds": end - start,
        "avg_time_per_run_ms": avg_time * 1000
    }

    with open(out_dir / "baseline.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Benchmark complete. Average time per run: {avg_time * 1000:.3f} ms")
    print("Saved to bench/baseline.json")

if __name__ == "__main__":
    main()