import json

import pytest

from ismypwdsafe import analyze_password
from ismypwdsafe.engines.availability import python_available, ts_available
from ismypwdsafe.render import render_json

SECRET = "qZ7!wX9#unique-marker-4vL"  # noqa: S105


def _engine_available(engine: str) -> bool:
    if engine == "ts":
        return ts_available()
    if engine == "python":
        return python_available()
    return True


@pytest.mark.parametrize("engine", ["native", "python", "ts"])
def test_default_json_does_not_contain_the_password(engine):
    if not _engine_available(engine):
        pytest.skip(f"{engine} engine is not installed")

    result = analyze_password(SECRET, check_breach=False, engine_name=engine)
    assert result.error is None
    rendered = render_json(result)
    payload = json.loads(rendered)

    assert SECRET not in rendered
    assert "unique-marker" not in rendered
    assert "password" not in payload
    assert payload["redacted"] is True

    for match in payload["sequence"]:
        assert match.get("token") in (None, "<redacted>")
        for key in (
            "matched_word",
            "base_token",
            "sub_display",
            "regex_match",
            "subs",
        ):
            if key in match:
                assert match[key] == "<redacted>"


@pytest.mark.skipif(not ts_available(), reason="Node.js 18+ is not installed")
def test_json_full_exposes_tokens_but_not_a_top_level_password():
    result = analyze_password(SECRET, check_breach=False, engine_name="ts")
    payload = json.loads(render_json(result, include_tokens=True))

    assert payload["redacted"] is False
    assert "password" not in payload
    assert "password" not in payload["input"]
    tokens = {match.get("token") for match in payload["sequence"]}
    assert {"unique", "marker"} <= tokens
    assert SECRET not in json.dumps(payload["input"])


@pytest.mark.parametrize("engine", ["native", "python", "ts"])
def test_engine_used_is_the_engine_that_actually_scored(engine):
    if not _engine_available(engine):
        pytest.skip(f"{engine} engine is not installed")

    result = analyze_password(SECRET, check_breach=False, engine_name=engine)
    payload = json.loads(render_json(result))

    assert result.engine_requested == engine
    assert result.engine_used == engine
    assert payload["engine_requested"] == engine
    assert payload["engine_used"] == engine
    assert payload["engine_fallback"] is False
    assert payload["engine_version"] == result.engine_version


def test_auto_reports_the_actual_engine():
    if ts_available():
        expected = "ts"
        fallback = False
    elif python_available():
        expected = "python"
        fallback = True
    else:
        expected = None
        fallback = False

    result = analyze_password(SECRET, check_breach=False, engine_name="auto")
    assert result.engine_used == expected
    assert result.engine_fallback is fallback
    if expected is None:
        assert result.exit_code == 4
    else:
        assert result.error is None


def test_auto_never_silently_uses_native(monkeypatch):
    import ismypwdsafe.engines as engines

    monkeypatch.setattr(engines, "ts_available", lambda: False)
    monkeypatch.setattr(engines, "python_available", lambda: False)

    result = analyze_password(SECRET, check_breach=False, engine_name="auto")
    assert result.exit_code == 4
    assert result.engine_used is None
    assert result.engine_requested == "auto"
    assert result.error is not None
    assert "native" in result.error
