import pytest
from hypothesis import given
from hypothesis import strategies as st

from ismypwdsafe import analyze_password


@given(st.text())
def test_score_bounds(password):
    """Lo score deve sempre essere compreso tra 0 e 100."""
    result = analyze_password(password, check_breach=False)
    if result.error is None:
        assert 0 <= result.score.value <= 100

@given(st.text())
def test_determinism(password):
    """Lo stesso input deve sempre produrre lo stesso output."""
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
    """Nessuna stringa generata casualmente deve causare eccezioni."""
    try:
        analyze_password(password, check_breach=False)
    except Exception as e:
        pytest.fail(f"analyze_password ha lanciato un'eccezione su '{password}': {e}")