import json
from pathlib import Path

import pytest

from ismypwdsafe import analyze_password
from ismypwdsafe.engines.availability import ts_available
from ismypwdsafe.render import render_json

GOLDEN_DIR = Path(__file__).parent / "golden"
SCORES_PATH = GOLDEN_DIR / "scores.json"
SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "result.schema.json"


def load_json(path: Path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def test_json_schema_against_golden() -> None:
    if not SCORES_PATH.exists():
        pytest.skip("Golden scores not generated. Run scripts/generate_golden.py")
    jsonschema = pytest.importorskip("jsonschema")

    schema = load_json(SCHEMA_PATH)
    for case in load_json(SCORES_PATH):
        jsonschema.validate(instance=case["expected"], schema=schema)


def test_live_output_validates_and_is_strict_json() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(SCHEMA_PATH)
    result = analyze_password("password", check_breach=False, engine_name="native")
    rendered = render_json(result)
    assert "Infinity" not in rendered
    assert "NaN" not in rendered
    jsonschema.validate(instance=json.loads(rendered), schema=schema)


def test_error_output_validates() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = load_json(SCHEMA_PATH)
    result = analyze_password("", check_breach=False, engine_name="native")
    jsonschema.validate(instance=json.loads(render_json(result)), schema=schema)


@pytest.mark.skipif(not ts_available(), reason="Node.js 18+ is not installed")
def test_tokens_are_redacted_by_default() -> None:
    result = analyze_password("password", check_breach=False, engine_name="ts")
    payload = json.loads(render_json(result))
    assert payload["redacted"] is True
    assert any(match.get("pattern") == "dictionary" for match in payload["sequence"])
    for match in payload["sequence"]:
        assert match.get("token") == "<redacted>"

    full = json.loads(render_json(result, include_tokens=True))
    assert full["redacted"] is False
    assert any(match.get("token") == "password" for match in full["sequence"])
    assert "password" not in json.dumps(full["input"])
