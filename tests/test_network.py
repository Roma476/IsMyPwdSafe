from ismypwdsafe import network


class _FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


def test_check_breach_pwned(monkeypatch):
    # sha1("password") = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
    # prefix = 5BAA6, suffix = 1E4C9B93F3F0682250B6CF8331B7EE68FD8
    def fake_get(url, **kwargs):
        assert "5BAA6" in url
        assert kwargs["headers"]["Add-Padding"] == "true"
        return _FakeResponse(200, "1E4C9B93F3F0682250B6CF8331B7EE68FD8:9545824\n")

    monkeypatch.setattr(network.requests, "get", fake_get)
    result = network.check_breach("password")
    assert result.checked is True
    assert result.pwned is True
    assert result.breach_count == 9545824
    assert result.reason is None
    assert result.unknown is False


def test_check_breach_clean(monkeypatch):
    monkeypatch.setattr(
        network.requests,
        "get",
        lambda url, **kwargs: _FakeResponse(200, "DEADBEEF:1\n"),
    )
    result = network.check_breach("password")
    assert result.checked is True
    assert result.pwned is False
    assert result.breach_count == 0
    assert result.unknown is False


def test_check_breach_api_error(monkeypatch):
    monkeypatch.setattr(
        network.requests,
        "get",
        lambda url, **kwargs: _FakeResponse(500),
    )
    result = network.check_breach("password")
    assert result.checked is True
    assert result.pwned is None
    assert result.reason == "api_error"
    assert result.unknown is True


def test_check_breach_network_exception(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("no route")

    monkeypatch.setattr(network.requests, "get", boom)
    result = network.check_breach("password")
    assert result.checked is True
    assert result.pwned is None
    assert result.reason == "api_error"


def test_k_anonymity_only_prefix_sent(monkeypatch):
    seen_urls = []

    def fake_get(url, **kwargs):
        seen_urls.append(url)
        return _FakeResponse(200, "")

    monkeypatch.setattr(network.requests, "get", fake_get)
    network.check_breach("correct-horse-battery-staple")
    assert len(seen_urls) == 1
    prefix = seen_urls[0].rsplit("/", 1)[-1]
    assert len(prefix) == 5
    assert prefix.isupper()


def test_malformed_padding_line_is_ignored(monkeypatch):
    monkeypatch.setattr(
        network.requests,
        "get",
        lambda url, **kwargs: _FakeResponse(200, "garbage\nDEAD:01\n"),
    )
    result = network.check_breach("password")
    assert result.pwned is False


def test_zero_count_padding_is_clean(monkeypatch):
    # HIBP padding entries use count 0 and must not be reported as pwned.
    monkeypatch.setattr(
        network.requests,
        "get",
        lambda url, **kwargs: _FakeResponse(
            200, "1E4C9B93F3F0682250B6CF8331B7EE68FD8:0\n"
        ),
    )
    result = network.check_breach("password")
    assert result.pwned is False
    assert result.breach_count == 0
