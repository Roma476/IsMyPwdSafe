import pytest
from ismypwdsafe import patterns


def test_top150_match():
    result = patterns.detect_pattern("password")
    assert result.detected is True
    assert result.rule == "top150"


def test_top150_leet():
    result = patterns.detect_pattern("P@ssw0rd")
    assert result.rule == "top150"


def test_top150_substring():
    result = patterns.detect_pattern("MyPassword123")
    assert result.rule == "top150"


def test_qwerty_walk_helper():
    assert patterns.check_keyboard_spatial("qwertyuiop") is True
    assert patterns.check_keyboard_spatial("1qaz2wsx") is True
    assert patterns.check_keyboard_spatial("mnbvcxz") is True
    assert patterns.check_keyboard_spatial("1qaz") is True
    assert patterns.check_keyboard_spatial("hello") is False


def test_qwerty_walk_via_detect_pattern():
    # "zxcvbnm" non è nella top-150, quindi la regola walk scatta
    result = patterns.detect_pattern("mnbvcxz")
    assert result.detected is True
    assert result.rule == "qwerty_walk"


def test_common_year():
    result = patterns.detect_pattern("1990zz")
    assert result.detected is True
    assert result.rule == "common_year"


def test_common_year_outside_range():
    result = patterns.detect_pattern("1800zz")
    assert result.rule != "common_year"


def test_repetition():
    result = patterns.detect_pattern("xyz!!!abc")
    assert result.detected is True
    assert result.rule == "repetition"


def test_clean_password():
    result = patterns.detect_pattern("correct-horse-battery-staple")
    assert result.detected is False
    assert result.rule is None


def test_empty_password():
    result = patterns.detect_pattern("")
    assert result.detected is False


def test_normalize_leetspeak():
    assert patterns.normalize_leetspeak("P@ssw0rd") == "password"
    assert patterns.normalize_leetspeak("!c3") == "ice"