from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from ismypwdsafe import cli
from ismypwdsafe.network import BreachResult
from ismypwdsafe.scan import (
    ScanOptions,
    ScanUsageError,
    discover_files,
    render_scan_json,
    render_scan_text,
    scan_files,
    scan_main,
)


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _native(**overrides) -> ScanOptions:
    values = {
        "engine": "native",
        "check_breach": False,
        "include_patterns": (".env", ".env.*", "*.env", "*.env.*"),
    }
    values.update(overrides)
    return ScanOptions(**values)


def test_scan_offline_scores_password_and_never_prints_value(tmp_path: Path) -> None:
    secret = "unique-password-marker-7xQ"  # noqa: S105
    _write(tmp_path / ".env", f"DB_PASSWORD={secret}\nAPI_KEY=ghp_abcdefghijklmnopqrstuvwxyz\n")

    result = scan_files(_native(paths=(".env",)), cwd=tmp_path)

    assert [item.kind for item in result.findings] == ["password", "token"]
    assert result.findings[0].score is not None
    assert result.findings[1].score is None
    assert result.findings[1].breach is None
    assert result.exit_code == 1
    text = render_scan_text(result)
    payload = render_scan_json(result)
    assert secret not in text
    assert secret not in payload
    assert "HIBP: not applicable" in text
    assert json.loads(payload)["kind"] == "scan"


def test_scan_pwned_password_forces_score_zero_and_exit_three(
    tmp_path: Path, monkeypatch
) -> None:
    _write(tmp_path / ".env", "DB_PASSWORD=password\n")
    monkeypatch.setattr(
        "ismypwdsafe.scan.network.check_breach",
        lambda value: BreachResult(True, True, 12345, None),
    )

    result = scan_files(
        _native(paths=(".env",), check_breach=True), cwd=tmp_path
    )

    assert result.exit_code == 3
    assert result.findings[0].score == 0
    assert result.findings[0].rating == "weak"
    assert result.findings[0].breach is not None
    assert result.findings[0].breach.breach_count == 12345


def test_scan_hibp_disabled_and_offline_do_not_exit_five(
    tmp_path: Path, monkeypatch
) -> None:
    _write(tmp_path / ".env", "DB_PASSWORD=correct-horse-battery-staple\n")

    def fail(*args, **kwargs):
        raise AssertionError("network should not be used")

    monkeypatch.setattr("ismypwdsafe.scan.network.check_breach", fail)

    disabled = scan_files(
        _native(paths=(".env",), check_breach=False), cwd=tmp_path
    )
    offline = scan_files(
        _native(paths=(".env",), check_breach=True, offline=True), cwd=tmp_path
    )

    assert disabled.exit_code == 0
    assert disabled.findings[0].breach is not None
    assert disabled.findings[0].breach.reason == "disabled"
    assert offline.exit_code == 0
    assert offline.findings[0].breach is not None
    assert offline.findings[0].breach.reason == "offline"


def test_scan_hibp_api_error_exits_five(tmp_path: Path, monkeypatch) -> None:
    _write(tmp_path / ".env", "DB_PASSWORD=correct-horse-battery-staple\n")
    monkeypatch.setattr(
        "ismypwdsafe.scan.network.check_breach",
        lambda value: BreachResult(True, None, None, "api_error"),
    )

    result = scan_files(_native(paths=(".env",), check_breach=True), cwd=tmp_path)

    assert result.exit_code == 5
    assert result.findings[0].breach is not None
    assert result.findings[0].breach.reason == "api_error"


def test_scan_hibp_timeout_retains_partial_results(tmp_path: Path, monkeypatch) -> None:
    _write(tmp_path / ".env", "DB_PASSWORD=password\n")

    def slow(value):
        time.sleep(0.2)
        return BreachResult(True, False, 0, None)

    monkeypatch.setattr("ismypwdsafe.scan.network.check_breach", slow)

    result = scan_files(
        _native(paths=(".env",), check_breach=True, timeout=0.001), cwd=tmp_path
    )

    assert result.incomplete is True
    assert result.unchecked_values == 1
    assert result.exit_code == 5
    assert result.findings[0].breach is not None
    assert result.findings[0].breach.reason == "scan_timeout"


def test_scan_deduplicates_hibp_requests(tmp_path: Path, monkeypatch) -> None:
    _write(
        tmp_path / ".env",
        "DB_PASSWORD=password\nOTHER_PASSWORD=password\n",
    )
    calls = []

    def fake(value):
        calls.append(value)
        return BreachResult(True, False, 0, None)

    monkeypatch.setattr("ismypwdsafe.scan.network.check_breach", fake)

    result = scan_files(_native(paths=(".env",), check_breach=True), cwd=tmp_path)

    assert calls == ["password"]
    assert len(result.findings) == 2
    assert all(item.breach is not None for item in result.findings)
    assert result.findings[0].breach == result.findings[1].breach


def test_scan_token_is_not_scored_or_sent_to_hibp(tmp_path: Path, monkeypatch) -> None:
    _write(tmp_path / ".env", "API_KEY=ghp_abcdefghijklmnopqrstuvwxyz\n")

    def fail(*args, **kwargs):
        raise AssertionError("tokens must not be sent to HIBP")

    monkeypatch.setattr("ismypwdsafe.scan.network.check_breach", fail)

    result = scan_files(
        _native(paths=(".env",), check_breach=True), cwd=tmp_path
    )

    assert result.exit_code == 0
    assert result.findings[0].kind == "token"
    assert result.findings[0].score is None
    assert result.findings[0].breach is None
    assert result.findings[0].token_format == "GitHub personal access token"  # noqa: S105


def test_scan_private_key_is_critical_and_not_rendered(tmp_path: Path) -> None:
    marker = "MIIEuniquePrivateKeyMarker"
    _write(
        tmp_path / ".env",
        "PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n"
        f"{marker}\n"
        "-----END RSA PRIVATE KEY-----\n",
    )

    result = scan_files(_native(paths=(".env",)), cwd=tmp_path)

    assert result.exit_code == 6
    assert len(result.findings) == 1
    assert result.findings[0].kind == "critical"
    assert result.findings[0].score is None
    assert marker not in render_scan_text(result)
    assert marker not in render_scan_json(result)


def test_scan_engine_error_exits_four(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "DB_PASSWORD=correct-horse-battery-staple\n")

    result = scan_files(
        _native(paths=(".env",), engine="does-not-exist"), cwd=tmp_path
    )

    assert result.exit_code == 4
    assert result.engine_error
    assert result.findings[0].score is None


def test_scan_engine_error_does_not_echo_value(tmp_path: Path, monkeypatch) -> None:
    secret = "engine-error-unique-marker"  # noqa: S105
    _write(tmp_path / ".env", f"DB_PASSWORD={secret}\n")

    def failing(value, **kwargs):
        return SimpleNamespace(score=None, error=f"engine failed for {value}")

    monkeypatch.setattr("ismypwdsafe.scan.analyze_password", failing)

    result = scan_files(_native(paths=(".env",)), cwd=tmp_path)

    assert result.exit_code == 4
    assert result.engine_error == "scoring engine failed; no score was produced"
    assert secret not in render_scan_text(result)
    assert secret not in render_scan_json(result)


def test_scan_usage_error_for_missing_path(tmp_path: Path) -> None:
    with pytest.raises(ScanUsageError) as exc:
        scan_files(_native(paths=("missing.env",)), cwd=tmp_path)
    assert "path not found" in str(exc.value)


def test_discovery_uses_tracked_files_only_by_default(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "DB_PASSWORD=secret\n")
    _write(tmp_path / ".env.local", "DB_PASSWORD=secret\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
    subprocess.run(["git", "add", ".env"], cwd=tmp_path, check=True)  # noqa: S607

    tracked = discover_files(ScanOptions(), cwd=tmp_path)
    with_untracked = discover_files(
        ScanOptions(include_untracked=True), cwd=tmp_path
    )

    assert [path.name for path in tracked] == [".env"]
    assert {path.name for path in with_untracked} == {".env", ".env.local"}


def test_discovery_include_untracked_includes_ignored_env(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", ".env.local\n")
    _write(tmp_path / ".env.local", "DB_PASSWORD=secret\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607

    default = discover_files(ScanOptions(), cwd=tmp_path)
    untracked = discover_files(ScanOptions(include_untracked=True), cwd=tmp_path)

    assert default == []
    assert [path.name for path in untracked] == [".env.local"]


def test_discovery_explicit_ignored_file_works(tmp_path: Path) -> None:
    _write(tmp_path / ".gitignore", ".env\n")
    _write(tmp_path / ".env", "DB_PASSWORD=secret\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607

    found = discover_files(ScanOptions(paths=(".env",)), cwd=tmp_path)

    assert [path.name for path in found] == [".env"]


def test_discovery_without_git_requires_opt_in(tmp_path: Path) -> None:
    _write(tmp_path / ".env", "DB_PASSWORD=secret\n")

    with pytest.raises(Exception) as exc:
        discover_files(ScanOptions(), cwd=tmp_path)
    assert "not a git repository" in str(exc.value)

    found = discover_files(ScanOptions(no_git=True), cwd=tmp_path)
    assert [path.name for path in found] == [".env"]


def test_scan_json_contract_validates(tmp_path: Path) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    _write(tmp_path / ".env", "DB_PASSWORD=password\n")
    result = scan_files(_native(paths=(".env",)), cwd=tmp_path)
    schema_path = Path(__file__).parent.parent / "schema" / "scan.schema.json"
    if not schema_path.exists():
        pytest.skip("scan schema not present")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(json.loads(render_scan_json(result)), schema)


def test_cli_routes_scan_and_json_full_is_usage_error(tmp_path: Path, capsys) -> None:
    _write(tmp_path / ".env", "DB_PASSWORD=password\n")
    code = cli.main(
        [
            "scan",
            "--no-git",
            "--offline",
            "--engine=native",
            "--quiet",
            str(tmp_path / ".env"),
        ]
    )
    assert code == 1
    assert capsys.readouterr().out == ""

    with pytest.raises(SystemExit) as exc:
        cli.main(["scan", "--json-full"])
    assert exc.value.code == 2


def test_scan_main_json_output_is_strict(tmp_path: Path, capsys) -> None:
    marker = "unique-secret-marker-4vL"
    _write(tmp_path / ".env", f"DB_PASSWORD={marker}\n")
    code = scan_main(
        [
            "--no-git",
            "--offline",
            "--engine=native",
            "--json",
            str(tmp_path / ".env"),
        ]
    )
    assert code == 1
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["kind"] == "scan"
    assert payload["schema_version"] == "1.0"
    assert marker not in captured.out
