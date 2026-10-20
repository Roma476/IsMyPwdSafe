import pytest
from ismypwdsafe import core, analyze_password
from ismypwdsafe.patterns import PatternResult
from ismypwdsafe.network import BreachResult


@pytest.mark.parametrize("pwd, expected_charset", [
    ("abc", 26),
    ("abcABC", 52),
    ("abcABC123", 62),
    ("abcABC123!", 95),
    ("", 0),
])
def test_calc_charset(pwd, expected_charset):
    charset, *_ = core.calc_charset(pwd)
    assert charset == expected_charset


def test_calc_combinations_small():
    combos, log10_val = core.calc_combinations(26, 3)
    assert combos == 26 ** 3
    assert log10_val == pytest.approx(3 * 1.41497, rel=1e-4)


def test_calc_combinations_large_uses_log():
    combos, log10_val = core.calc_combinations(95, 20)
    assert combos is None
    assert log10_val > 0


def test_score_clean_strong(clean_breach):
    pattern = PatternResult(False, None, None)
    score = core.calculate_score(25.0, pattern, clean_breach)
    assert score.value == 100
    assert score.rating == "strong"
    assert score.capped_by is None


def test_score_pattern_capped(clean_breach):
    pattern = PatternResult(True, "top150", "x")
    score = core.calculate_score(25.0, pattern, clean_breach)
    assert score.value == 30
    assert score.capped_by == "pattern"


def test_score_pwned_capped(pattern=None):
    breach = BreachResult(checked=True, pwned=True, count=100, reason=None)
    pattern = PatternResult(False, None, None)
    score = core.calculate_score(25.0, pattern, breach)
    assert score.value == 10
    assert score.capped_by == "breach"


def test_score_pattern_and_pwned_breach_wins():
    pattern = PatternResult(True, "top150", "x")
    breach = BreachResult(checked=True, pwned=True, count=100, reason=None)
    score = core.calculate_score(25.0, pattern, breach)
    assert score.value == 10
    assert score.capped_by == "breach"


def test_analyze_password_offline_no_network(no_network):
    result = analyze_password("correct-horse-battery-staple", check_breach=False)
    assert result.error is None
    assert result.breach.checked is False
    assert result.breach.reason is None
    assert result.exit_code == core.EXIT_OK
    assert result.score.rating == "strong"


def test_analyze_password_offline_with_reason(no_network):
    result = analyze_password(
        "correct-horse-battery-staple",
        check_breach=False,
        breach_skip_reason="offline",
    )
    assert result.breach.checked is False
    assert result.breach.reason == "offline"


def test_analyze_password_empty():
    result = analyze_password("", check_breach=False)
    assert result.error is not None
    assert result.exit_code == core.EXIT_DATA
    assert result.input is None


def test_analyze_password_weak():
    result = analyze_password("password", check_breach=False)
    assert result.pattern.detected is True
    assert result.score.value <= 30
    assert result.score.rating == "weak"