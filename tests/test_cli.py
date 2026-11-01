import json

import pytest

from ismypwdsafe import cli
from ismypwdsafe.engines.availability import ts_available
from ismypwdsafe.network import BreachResult


def test_short_and_darkweb_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["-s", "-dw", "password"])
    assert exc.value.code == 2
    assert "not allowed with" in capsys.readouterr().err


def test_empty_password_returns_usage_error():
    # pytest's stdin is not a TTY, so the CLI must not hang on getpass.
    assert cli.main([]) == 2


def test_default_skips_update_check(monkeypatch, no_network):
    called = {"update": False}

    def fake_update(version):
        called["update"] = True
        return None

    monkeypatch.setattr(cli.network, "check_for_updates", fake_update)
    code = cli.main(
        ["--engine=native", "--offline", "correct-horse-battery-staple"]
    )
    assert code == 0
    assert called["update"] is False


def test_check_updates_flag(monkeypatch, no_network):
    called = {"update": False}

    def fake_update(version):
        called["update"] = True
        return None

    monkeypatch.setattr(cli.network, "check_for_updates", fake_update)
    code = cli.main(
        [
            "--engine=native",
            "--no-breach-check",
            "--check-updates",
            "correct-horse-battery-staple",
        ]
    )
    assert code == 0
    assert called["update"] is True


def test_exit_code_strong(no_network):
    assert (
        cli.main(
            ["--engine=native", "--no-breach-check", "correct-horse-battery-staple"]
        )
        == 0
    )


def test_exit_code_weak(no_network):
    assert cli.main(["--engine=native", "--no-breach-check", "password"]) == 1


def test_no_update_check_deprecation(capsys, no_network):
    code = cli.main(
        [
            "--engine=native",
            "--no-breach-check",
            "--no-update-check",
            "password",
        ]
    )
    assert code == 1
    assert "deprecated" in capsys.readouterr().err


def test_json_is_redacted_and_valid(no_network, capsys):
    code = cli.main(
        ["--engine=native", "--no-breach-check", "--json", "password"]
    )
    assert code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema_version"] == "2.0"
    assert payload["redacted"] is True
    assert payload["input"]["length"] == 8
    assert payload["score"]["rating"] == "weak"
    assert "password" not in json.dumps(payload["input"])


def test_hibp_unknown_exit_code(monkeypatch, capsys):
    monkeypatch.setattr(
        "ismypwdsafe.network.check_breach",
        lambda password: BreachResult(True, None, None, "api_error"),
    )
    code = cli.main(["--engine=native", "--json", "password"])
    assert code == 5
    payload = json.loads(capsys.readouterr().out)
    assert payload["breach"]["checked"] is True
    assert payload["breach"]["pwned"] is None
    assert payload["breach"]["reason"] == "api_error"


@pytest.mark.skipif(not ts_available(), reason="Node.js 18+ is not installed")
def test_cli_json_does_not_leak_password(capsys):
    secret = "qZ7!wX9#unique-marker-4vL"  # noqa: S105
    code = cli.main(["--engine=ts", "--offline", "--json", secret])
    assert code == 0
    output = capsys.readouterr().out
    assert secret not in output
    assert "unique-marker" not in output
    assert json.loads(output)["redacted"] is True


@pytest.mark.skipif(not ts_available(), reason="Node.js 18+ is not installed")
def test_json_full_includes_tokens(capsys):
    code = cli.main(
        ["--engine=ts", "--offline", "--json-full", "Tr0ub4dor&3"]
    )
    assert code in (0, 1)
    payload = json.loads(capsys.readouterr().out)
    assert payload["redacted"] is False
    assert payload["engine_used"] == "ts"
    assert any(match.get("token") == "Tr0ub4dor&3" for match in payload["sequence"])
