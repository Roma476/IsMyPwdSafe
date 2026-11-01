import pytest

hypothesis = pytest.importorskip("hypothesis")
from hypothesis import given  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from ismypwdsafe import analyze_password  # noqa: E402


@given(st.text())
def test_score_bounds(password):
    result = analyze_password(password, check_breach=False, engine_name="native")
    if result.error is None:
        assert result.score is not None
        assert 0 <= result.score.value <= 100


@given(st.text())
def test_determinism(password):
    first = analyze_password(password, check_breach=False, engine_name="native")
    second = analyze_password(password, check_breach=False, engine_name="native")
    if first.error is None:
        assert first.score is not None
        assert second.score is not None
        assert first.score.value == second.score.value
        assert first.score.rating == second.score.rating
    else:
        assert first.error == second.error


@given(st.text(min_size=1))
def test_no_crash(password):
    try:
        analyze_password(password, check_breach=False, engine_name="native")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"analyze_password raised on {password!r}: {exc}")
