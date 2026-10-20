import pytest
from ismypwdsafe import patterns


@pytest.mark.parametrize("pwd, rule", [
    ("password", "top150"),
    ("P@ssw0rd", "top150"),
    ("MyPassword123", "top150"),
    ("qwertyuiop", "qwerty_walk"),
    ("1qaz2wsx", "qwerty_walk"),
    ("mnbvcxz", "qwerty_walk"),
    ("Summer1990!", "common_year"),
    ("MyPassword2024", "common_year"),
    ("password!!!", "repetition"),
    ("aaa", "repetition"),
])
def test_detect_pattern_rules(pwd, rule):
    result = patterns.detect_pattern(pwd)
    assert result.detected is True
    assert result.rule == rule
    assert result.detail is not None


@pytest.mark.parametrize("pwd", [
    "correct-horse-battery-staple",
    "vT7#pQ2!mN9x",
    "",
])
def test_detect_pattern_clean(pwd):
    result = patterns.detect_pattern(pwd)
    assert result.detected is False
    assert result.rule is None
    assert result.detail is None


def test_leet_normalization():
    assert patterns.normalize_leetspeak("P@ssw0rd") == "password"
    assert patterns.normalize_leetspeak("!c3") == "ice"


def test_year_outside_range_is_not_flagged():
    # 1234 is a 4-digit run but outside 1900-2050
    result = patterns.detect_pattern("abcd1234")
    assert result.rule != "common_year"