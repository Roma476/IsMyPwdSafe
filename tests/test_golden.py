import json
from pathlib import Path

import pytest

from ismypwdsafe import analyze_password
from ismypwdsafe.engines.availability import ts_available
from ismypwdsafe.render import render_json

GOLDEN_DIR = Path(__file__).parent / "golden"
CASES_PATH = GOLDEN_DIR / "cases.json"
SCORES_PATH = GOLDEN_DIR / "scores.json"

_IGNORED = {"tool_version", "calc_time"}


def load_json(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def test_golden_scores():
    if not CASES_PATH.exists() or not SCORES_PATH.exists():
        pytest.skip("Golden files not generated. Run scripts/generate_golden.py")

    golden_data = load_json(SCORES_PATH)
    mismatches = []

    for case in golden_data:
        expected = case["expected"].copy()
        engine = (
            expected.get("engine_used")
            or expected.get("engine_requested")
            or "native"
        )
        if engine == "ts" and not ts_available():
            pytest.skip("Golden was generated with zxcvbn-ts but Node 18+ is unavailable")
        if engine == "python":
            pytest.importorskip("zxcvbn")

        result = analyze_password(
            case["input"],
            check_breach=False,
            engine_name=engine,
        )
        actual = json.loads(render_json(result))
        for key in _IGNORED:
            expected.pop(key, None)
            actual.pop(key, None)

        if actual != expected:
            diffs = [
                f"  {key}: expected {expected.get(key)!r}, got {actual.get(key)!r}"
                for key in expected
                if actual.get(key) != expected[key]
            ]
            mismatches.append(f"{case['input']!r}:\n" + "\n".join(diffs))

    if mismatches:
        pytest.fail("Golden score mismatches:\n\n" + "\n\n".join(mismatches))
