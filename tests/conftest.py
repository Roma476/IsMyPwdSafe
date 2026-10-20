import pytest
from ismypwdsafe import network
from ismypwdsafe.network import BreachResult


@pytest.fixture
def clean_breach():
    return BreachResult(checked=True, pwned=False, count=0, reason=None)


@pytest.fixture
def pwned_breach():
    return BreachResult(checked=True, pwned=True, count=12345, reason=None)


@pytest.fixture
def offline_breach():
    return BreachResult(checked=False, pwned=None, count=None, reason="offline")


@pytest.fixture
def no_network(monkeypatch):
    """Raise if any test accidentally performs an HTTP request."""
    def _fail(*args, **kwargs):
        raise AssertionError("Network access attempted in a test")
    monkeypatch.setattr(network.requests, "get", _fail)