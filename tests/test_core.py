import pytest

from ismypwdsafe import analyze_password, core, engines
from ismypwdsafe.metrics import calc_charset, calc_combinations
from ismypwdsafe.network import BreachResult


@pytest.mark.parametrize(
    "pwd, expected_charset",
    [
        ("abc", 26),
        ("abcABC", 52),
        ("abcABC123", 62),
        ("abcABC123!", 95),
        ("", 0),
    ],
)
def test_calc_charset(pwd, expected_charset):
    charset, *_ = calc_charset(pwd)
    assert charset == expected_charset


def test_calc_combinations_small():
    combos, log10_val = calc_combinations(26, 3)
    assert combos == 26**3
    assert log10_val == pytest.approx(3 * 1.41497, rel=1e-4)


def test_calc_combinations_large_uses_log():
    combos, log10_val = calc_combinations(95, 20)
    assert combos is None
    assert log10_val > 0


def test_native_engine_offline_is_deterministic(no_network):
    result = analyze_password(
        "correct-horse-battery-staple",
        check_breach=False,
        engine_name="native",
    )
    assert result.error is None
    assert result.engine_used == "native"
    assert result.engine_requested == "native"
    assert result.engine_fallback is False
    assert result.breach is not None
    assert result.breach.checked is False
    assert result.breach.reason == "disabled"
    assert result.exit_code == core.EXIT_OK
    assert result.score is not None
    assert result.score.value == 100
    assert result.score.rating == "strong"


def test_python_engine_reports_calc_time_in_milliseconds(no_network):
    if not engines.python_available():
        pytest.skip("zxcvbn-python is not installed")

    result = analyze_password(
        "correct-horse-battery-staple",
        check_breach=False,
        engine_name="python",
    )
    assert result.error is None
    assert result.calc_time is not None
    assert result.calc_time >= 0


def test_offline_reason(no_network):
    result = analyze_password(
        "correct-horse-battery-staple",
        check_breach=False,
        breach_skip_reason="offline",
        engine_name="native",
    )
    assert result.breach is not None
    assert result.breach.checked is False
    assert result.breach.reason == "offline"


def test_empty_password_is_usage_error():
    result = analyze_password("", check_breach=False, engine_name="native")
    assert result.error is not None
    assert result.exit_code == core.EXIT_USAGE
    assert result.input is None
    assert result.score is None


def test_weak_password_exit_code():
    result = analyze_password("password", check_breach=False, engine_name="native")
    assert result.error is None
    assert result.score is not None
    assert result.score.rating == "weak"
    assert result.exit_code == core.EXIT_WEAK


def test_pwned_password_is_capped_and_exit_3(monkeypatch):
    monkeypatch.setattr(
        "ismypwdsafe.network.check_breach",
        lambda password: BreachResult(True, True, 12345, None),
    )
    result = analyze_password(
        "correct-horse-battery-staple",
        check_breach=True,
        engine_name="native",
    )
    assert result.breach is not None
    assert result.breach.pwned is True
    assert result.breach.breach_count == 12345
    assert result.score is not None
    assert result.score.value == 0
    assert result.score.rating == "weak"
    assert result.score.capped_by == "hibp"
    assert result.exit_code == core.EXIT_PWNED


def test_hibp_unknown_is_exit_5(monkeypatch):
    monkeypatch.setattr(
        "ismypwdsafe.network.check_breach",
        lambda password: BreachResult(True, None, None, "api_error"),
    )
    result = analyze_password(
        "correct-horse-battery-staple",
        check_breach=True,
        engine_name="native",
    )
    assert result.breach is not None
    assert result.breach.checked is True
    assert result.breach.pwned is None
    assert result.breach.reason == "api_error"
    assert result.exit_code == core.EXIT_HIBP_UNKNOWN


def test_clean_breach_keeps_score(monkeypatch):
    monkeypatch.setattr(
        "ismypwdsafe.network.check_breach",
        lambda password: BreachResult(True, False, 0, None),
    )
    result = analyze_password(
        "correct-horse-battery-staple",
        check_breach=True,
        engine_name="native",
    )
    assert result.breach is not None
    assert result.breach.pwned is False
    assert result.score is not None
    assert result.score.value == 100
    assert result.score.capped_by is None
    assert result.exit_code == core.EXIT_OK


def test_unknown_engine_is_engine_error():
    result = analyze_password("password", check_breach=False, engine_name="bogus")
    assert result.error is not None
    assert result.exit_code == core.EXIT_ENGINE
    assert result.engine_used is None


def test_auto_prefers_ts(monkeypatch):
    monkeypatch.setattr(engines, "ts_available", lambda: True)
    monkeypatch.setattr(engines, "python_available", lambda: True)
    assert engines.resolve_engine("auto") == "ts"


def test_auto_falls_back_to_python(monkeypatch):
    monkeypatch.setattr(engines, "ts_available", lambda: False)
    monkeypatch.setattr(engines, "python_available", lambda: True)
    assert engines.resolve_engine("auto") == "python"


def test_auto_never_falls_back_to_native(monkeypatch):
    monkeypatch.setattr(engines, "ts_available", lambda: False)
    monkeypatch.setattr(engines, "python_available", lambda: False)
    with pytest.raises(engines.EngineError):
        engines.resolve_engine("auto")


def test_native_is_available_explicitly(monkeypatch):
    monkeypatch.setattr(engines, "ts_available", lambda: False)
    monkeypatch.setattr(engines, "python_available", lambda: False)
    assert engines.resolve_engine("native") == "native"


@pytest.mark.skipif(
    not engines.python_available(),
    reason="zxcvbn-python is not installed",
)
def test_python_engine_full_result_offline():
    result = analyze_password(
        "Tr0ub4dor&3",
        check_breach=False,
        engine_name="python",
    )
    assert result.error is None
    assert result.engine_used == "python"
    assert result.score is not None
    assert result.score.raw_score_0_4 == 4
    assert result.sequence
    assert result.crack_times_display


@pytest.mark.skipif(
    not engines.python_available(),
    reason="zxcvbn-python is not installed",
)
def test_python_engine_hibp_unknown(monkeypatch):
    monkeypatch.setattr(
        "ismypwdsafe.network.check_breach",
        lambda password: BreachResult(True, None, None, "api_error"),
    )
    result = analyze_password(
        "Tr0ub4dor&3",
        check_breach=True,
        engine_name="python",
    )
    assert result.exit_code == core.EXIT_HIBP_UNKNOWN
    assert result.breach is not None
    assert result.breach.reason == "api_error"


def test_ts_hibp_error_is_mapped_to_unknown(monkeypatch):
    from ismypwdsafe.engines.base import EngineResult

    class FakeEngine:
        def score(self, password, *, check_breach=True):
            return EngineResult(
                engine_name="ts",
                engine_version="4.2.0",
                raw_score_0_4=4,
                score_100=100,
                rating="strong",
                pwned=None,
                pwned_count=None,
                hibp_status="error",
                hibp_error="network down",
            )

    monkeypatch.setattr(core, "resolve_engine", lambda name: "ts")
    monkeypatch.setattr(core, "make_engine", lambda name: FakeEngine())
    result = core.analyze_password(
        "correct-horse-battery-staple",
        check_breach=True,
        engine_name="auto",
    )
    assert result.exit_code == core.EXIT_HIBP_UNKNOWN
    assert result.engine_used == "ts"
    assert result.breach is not None
    assert result.breach.pwned is None
    assert result.breach.reason == "api_error"
