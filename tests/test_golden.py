import json
from pathlib import Path
from typing import Any, List

import pytest

from ismypwdsafe import analyze_password
from ismypwdsafe.render import render_json

GOLDEN_DIR = Path(__file__).parent / "golden"
CASES_PATH = GOLDEN_DIR / "cases.json"
SCORES_PATH = GOLDEN_DIR / "scores.json"


def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_golden_scores() -> None:
    if not CASES_PATH.exists() or not SCORES_PATH.exists():
        pytest.skip("Golden files not generated. Run scripts/generate_golden.py")

    golden_data: List[dict] = load_json(SCORES_PATH)
    mismatches = []

    for case in golden_data:
        pwd = case["input"]
        
        if "error" in case:
            try:
                analyze_password(pwd, check_breach=False)
                mismatches.append(f"'{pwd}': expected an error, but analysis succeeded.")
            except Exception:  # noqa: S110
                pass # The error is still happening, which is expected
            continue

        expected = case["expected"]
        result = analyze_password(pwd, check_breach=False)
        actual = json.loads(render_json(result))

        if actual != expected:
            diffs = []
            for k in expected:
                if actual.get(k) != expected[k]:
                    diffs.append(f"  {k}: expected {expected[k]}, got {actual.get(k)}")
            mismatches.append(f"'{pwd}':\n" + "\n".join(diffs))

    if mismatches:
        pytest.fail("Golden score mismatches:\n\n" + "\n\n".join(mismatches))