import pytest
from ismypwdsafe import cli


def test_short_and_darkweb_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["-s", "-dw", "password"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "not allowed with" in err


def test_empty_password_returns_data_error(monkeypatch):
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt="": "")
    # password arg omitted
    assert cli.main([]) == 65


def test_offline_skips_both_requests(monkeypatch, no_network):
    called = {"update": False}
    def fake_update(v):
        called["update"] = True
        return None
    monkeypatch.setattr(cli.network, "check_for_updates", fake_update)

    code = cli.main(["-o", "correct-horse-battery-staple"])
    assert code == 0
    assert called["update"] is False


def test_exit_code_reflects_result(monkeypatch):
    # Only 0 is possible until 1.5 adds semantic exit codes
    monkeypatch.setattr(
        cli.network, "check_for_updates", lambda v: None,
    )
    assert cli.main(["--no-breach-check", "password"]) == 0