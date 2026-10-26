import pytest

from ismypwdsafe import analyze_password, core
from ismypwdsafe.network import BreachResult
from ismypwdsafe.patterns import PatternResult


@pytest.mark.parametrize("pwd, expected_charset, expected_unicode", [
    ("abc", 26, False),
    ("abcABC", 52, False),
    ("abcABC123", 62, False),
    ("abcABC123!", 95, False),
    ("", 0, False),
    ("пароль", 33, True),
    ("🔒🔑", 1000, True),
    ("abc🔒", 1026, True), # 26 (lower) + 1000 (emoji)
])
def test_calc_charset(pwd, expected_charset, expected_unicode):
    charset, _, _, _, _, has_non_ascii = core.calc_charset(pwd)
    assert charset == expected_charset
    assert has_non_ascii == expected_unicode


def test_calc_combinations_small():
    combos, log10_val = core.calc_combinations(26, 3)
    assert combos == 26 ** 3
    assert log10_val == pytest.approx(3 * 1.41497, rel=1e-4)


def test_calc_combinations_large_uses_log():
    combos, log10_val = core.calc_combinations(95, 20)
    assert combos is None
    assert log10_val > 0


def test_score_clean_strong(clean_breach):
    pattern = PatternResult(False, None, None, [])
    score = core.calculate_score(25.0, pattern, clean_breach, 20, False)
    assert score.value == 100
    assert score.rating == "strong"
    assert score.capped_by is None


def test_score_pattern_capped(clean_breach):
    pattern = PatternResult(True, "top150", "x", ["top150"])
    score = core.calculate_score(25.0, pattern, clean_breach, 20, False)
    assert score.value == 5
    assert score.capped_by == "pattern"
    assert score.capped_by_rule == "top150"


def test_score_pwned_capped():
    breach = BreachResult(checked=True, pwned=True, breach_count=100, reason=None)
    pattern = PatternResult(False, None, None, [])
    score = core.calculate_score(25.0, pattern, breach, 20, False)
    assert score.value == 5
    assert score.capped_by == "breach"


def test_score_pattern_and_pwned_breach_wins():
    pattern = PatternResult(True, "top150", "x", ["top150"])
    breach = BreachResult(checked=True, pwned=True, breach_count=100, reason=None)
    score = core.calculate_score(25.0, pattern, breach, 20, False)
    assert score.value == 5
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

def test_score_unicode_miss():
    pattern = PatternResult(False, None, None, [])
    breach = BreachResult(checked=True, pwned=False, breach_count=0, reason=None)
    # High entropy (log10=15) but unicode_miss caps at 10.0 (score 50)
    score = core.calculate_score(15.0, pattern, breach, 6, True)
    assert score.value == 50
    assert score.capped_by == "unicode_miss"