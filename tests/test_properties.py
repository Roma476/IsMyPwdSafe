import pytest
from hypothesis import given
from hypothesis import strategies as st

from ismypwdsafe import analyze_password


@given(st.text())
def test_score_bounds(password):
    """The score must always be between 0 and 100, inclusive."""
    result = analyze_password(password, check_breach=False)
    if result.error is None:
        assert 0 <= result.score.value <= 100

@given(st.text())
def test_determinism(password):
    """The same password should always yield the same score and pattern detection."""
    res1 = analyze_password(password, check_breach=False)
    res2 = analyze_password(password, check_breach=False)
    
    if res1.error is None:
        assert res1.score.value == res2.score.value
        assert res1.score.rating == res2.score.rating
        if res1.pattern and res2.pattern:
            assert res1.pattern.detected == res2.pattern.detected
            assert res1.pattern.rules_fired == res2.pattern.rules_fired
    else:
        assert res1.error == res2.error

@given(st.text(min_size=1))
def test_no_crash(password):
    """No matter the input, analyze_password should not raise an exception."""
    try:
        analyze_password(password, check_breach=False)
    except Exception as e:
        pytest.fail(f"analyze_password ha lanciato un'eccezione su '{password}': {e}")