import pytest

from ismypwdsafe import analyze_password


@pytest.mark.parametrize("pwd", [
    "",
    " ",
    "a",
    "\x00",
    "a\nb",
    "\x1b[31mred\x1b[0m",
    "a" * 10000,
    "🔒🔑",
    "P@ssw0rd\x00",
])
def test_edge_cases_do_not_crash(pwd):
    result = analyze_password(pwd, check_breach=False)
    
    assert result is not None
    
    # Empty string should return an error
    if not pwd:
        assert result.error is not None
        assert result.exit_code != 0
    else:
        assert result.error is None
        assert 0 <= result.score.value <= 100