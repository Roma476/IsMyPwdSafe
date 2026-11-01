import re
from typing import Any

from ismypwdsafe import ui
from ismypwdsafe.core import AuditResult, FeedbackInfo, InputInfo, ScoreResult
from ismypwdsafe.network import BreachResult

ANSI_RE = re.compile(r"\033\[[0-9;]*m")

CRACK_TIMES = {
    "online_throttling_100_per_hour": "1 minute",
    "online_no_throttling_10_per_second": "less than a second",
    "offline_slow_hashing_1e4_per_second": "less than a second",
    "offline_fast_hashing_1e10_per_second": "less than a second",
}


def _plain(text: str) -> str:
    return ANSI_RE.sub("", text)


def _result(
    *,
    engine_used: str = "ts",
    score_value: int = 0,
    rating: str = "weak",
    raw_score: Any = 0,
    capped_by: Any = "hibp",
    sequence: Any = (),
    feedback: Any = None,
    breach: Any = None,
    crack_times: Any = None,
) -> AuditResult:
    crack = CRACK_TIMES if crack_times is None else crack_times
    return AuditResult(
        schema_version="2.0",
        tool_version="2.0.1",
        exit_code=3,
        error=None,
        input=InputInfo(
            length=11,
            charset_size=36,
            has_lower=True,
            has_upper=False,
            has_number=True,
            has_symbol=False,
            has_non_ascii=False,
        ),
        score=ScoreResult(
            value=score_value,
            rating=rating,
            raw_score_0_4=raw_score,
            capped_by=capped_by,
        ),
        guesses=1.0,
        guesses_log10=0.0,
        crack_times_seconds={},
        crack_times_display=crack,
        feedback=feedback,
        sequence=sequence,
        breach=breach or BreachResult(True, True, 2266543, None),
        engine_requested=engine_used,
        engine_used=engine_used,
        engine_version="4.2.0" if engine_used == "ts" else None,
        engine_fallback=False,
        calc_time=12.0 if engine_used == "ts" else None,
    )


def _pwned_result() -> AuditResult:
    return _result(
        sequence=({"pattern": "pwned", "token": "password123"},),
        feedback=FeedbackInfo(
            warning="Your password was exposed by a data breach on the Internet.",
            suggestions=(
                "Add more words that are less common.",
                "If you use this password elsewhere, you should change it.",
            ),
        ),
    )


def _pwned_pattern_result() -> AuditResult:
    return _result(
        sequence=(
            {
                "pattern": "dictionary",
                "token": "password",
                "dictionary_name": "passwords-common",
                "rank": 2,
            },
            {"pattern": "bruteforce", "token": ".123"},
        ),
        feedback=FeedbackInfo(
            warning="This is similar to a commonly used password.",
            suggestions=("Add more words that are less common.",),
        ),
    )


def _weak_result() -> AuditResult:
    return _result(
        breach=BreachResult(True, False, 0, None),
        sequence=(
            {
                "pattern": "dictionary",
                "token": "password",
                "dictionary_name": "passwords-common",
                "rank": 2,
            },
        ),
        feedback=FeedbackInfo(
            warning="This is a heavily used password.",
            suggestions=("Add more words that are less common.",),
        ),
    )


def test_full_report_uses_terminal_width(monkeypatch, capsys):
    monkeypatch.setattr(ui, "ANIMATE", False)
    monkeypatch.setattr(ui, "get_width", lambda: 120)

    ui.print_output(_pwned_result(), "password123")
    lines = _plain(capsys.readouterr().out).splitlines()
    tops = [line for line in lines if line.startswith("┌")]

    assert tops
    assert {len(line) for line in tops} == {118}


def test_full_report_uses_columns_when_wide(monkeypatch, capsys):
    monkeypatch.setattr(ui, "ANIMATE", False)
    monkeypatch.setattr(ui, "get_width", lambda: 120)

    ui.print_output(_weak_result(), "password")
    lines = _plain(capsys.readouterr().out).splitlines()

    assert any(
        "TIME TO CRACK" in line and "PATTERN MATCHES" in line for line in lines
    )
    assert "zxcvbn 0/4" not in "\n".join(lines)


def test_pwned_details_are_not_repeated(monkeypatch, capsys):
    monkeypatch.setattr(ui, "ANIMATE", False)
    monkeypatch.setattr(ui, "get_width", lambda: 80)

    ui.print_output(_pwned_result(), "password123")
    output = _plain(capsys.readouterr().out)

    assert output.count("2,266,543") == 1
    assert "found in HaveIBeenPwned" not in output
    assert "Score forced" not in output
    assert "Your password was exposed" not in output
    assert "If you use this password elsewhere" not in output
    assert "• Add more words that are less common." in output


def test_pwned_password_keeps_pattern_matches(monkeypatch, capsys):
    monkeypatch.setattr(ui, "ANIMATE", False)
    monkeypatch.setattr(ui, "get_width", lambda: 120)

    ui.print_output(_pwned_pattern_result(), "password.123")
    output = _plain(capsys.readouterr().out)

    assert "PATTERN MATCHES" in output
    assert "password  passwords-common #2" in output
    assert ".123  brute-force" in output
    assert output.count("2,266,543") == 1


def test_native_report_omits_empty_zxcvbn_sections(monkeypatch, capsys):
    monkeypatch.setattr(ui, "ANIMATE", False)
    monkeypatch.setattr(ui, "get_width", lambda: 80)

    result = _result(
        engine_used="native",
        score_value=100,
        rating="strong",
        raw_score=None,
        capped_by=None,
        sequence=(),
        feedback=None,
        breach=BreachResult(False, None, None, "offline"),
        crack_times={},
    )
    ui.print_output(result, "correct-horse-battery-staple")
    output = _plain(capsys.readouterr().out)

    assert "TIME TO CRACK" not in output
    assert "PATTERN MATCHES" not in output
    assert "WHAT TO DO" not in output
    assert "No zxcvbn" not in output
    assert "STRONG  100/100" in output
    assert "native heuristic" in output
