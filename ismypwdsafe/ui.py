# ruff: noqa: E501
"""Terminal rendering for the zxcvbn-first result model."""
from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
import time
from typing import Any, Iterable, Mapping, Sequence

from .core import AuditResult

# Enable ANSI escape processing on Windows consoles.
os.system("")  # noqa: S605, S607


def _supports_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        return True
    term = os.environ.get("TERM", "")
    return term not in ("", "dumb")


USE_COLOR = _supports_color()
ANIMATE = sys.stdout.isatty() and USE_COLOR


class C:
    RESET = "\033[0m" if USE_COLOR else ""
    BOLD = "\033[1m" if USE_COLOR else ""
    DIM = "\033[2m" if USE_COLOR else ""
    ITALIC = "\033[3m" if USE_COLOR else ""
    UNDER = "\033[4m" if USE_COLOR else ""
    RED = "\033[31m" if USE_COLOR else ""
    GREEN = "\033[32m" if USE_COLOR else ""
    YELLOW = "\033[33m" if USE_COLOR else ""
    BLUE = "\033[34m" if USE_COLOR else ""
    MAGENTA = "\033[35m" if USE_COLOR else ""
    CYAN = "\033[36m" if USE_COLOR else ""
    WHITE = "\033[37m" if USE_COLOR else ""


_ANSI = re.compile(r"\033\[[0-9;]*m")


def get_width() -> int:
    return max(40, shutil.get_terminal_size((80, 20)).columns)


def dim(text: str) -> str:
    return f"{C.DIM}{text}{C.RESET}"


def bold(text: str) -> str:
    return f"{C.BOLD}{text}{C.RESET}"


def err(text: str) -> str:
    return f"{C.RED}{text}{C.RESET}"


def warn(text: str) -> str:
    return f"{C.YELLOW}{text}{C.RESET}"


def ok(text: str) -> str:
    return f"{C.GREEN}{text}{C.RESET}"


def _visible_len(text: str) -> int:
    return len(_ANSI.sub("", text))


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _visible_len(text))


def _color_for_rating(rating: str) -> str:
    if rating == "weak":
        return C.RED
    if rating == "medium":
        return C.YELLOW
    return C.GREEN


def _bar(percent: int, width: int = 30) -> str:
    percent = max(0, min(100, percent))
    filled = round(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def _box(title: str, lines: Sequence[str], *, color: str = "") -> list[str]:
    width = min(get_width() - 2, 76)
    inner = max(20, width - 4)
    rendered: list[str] = []
    title_text = f" {title} "
    top_left = "┌" + title_text
    top = top_left + "─" * max(0, width - _visible_len(top_left) - 1) + "┐"
    rendered.append((color or "") + top + C.RESET)
    for line in lines:
        if not line:
            rendered.append((color or "") + "│" + C.RESET + " " * (width - 2) + (color or "") + "│" + C.RESET)
            continue
        wrapped = textwrap.wrap(
            str(line),
            width=inner,
            break_long_words=True,
            break_on_hyphens=False,
            replace_whitespace=False,
        ) or [""]
        for part in wrapped:
            rendered.append(
                (color or "")
                + "│"
                + C.RESET
                + " "
                + _pad(part, inner)
                + " "
                + (color or "")
                + "│"
                + C.RESET
            )
    rendered.append((color or "") + "└" + "─" * (width - 2) + "┘" + C.RESET)
    return rendered


def _print_lines(lines: Iterable[str], *, animate: bool = False) -> None:
    for line in lines:
        print(line)
        if animate:
            time.sleep(0.012)


def _banner() -> None:
    if ANIMATE:
        print("\033[2J\033[H", end="")
    title = "IsMyPwdSafe"
    tagline = "zxcvbn, but readable"
    line = f"{bold(C.CYAN + title)} {dim('·')} {dim(tagline)}"
    print()
    print("  " + line)
    print()


def _input_lines(result: AuditResult, password: str, mask_mode: bool) -> list[str]:
    info = result.input
    if info is None:
        return []
    shown = "*" * len(password) if mask_mode else password
    flags = []
    if info.has_lower:
        flags.append("lower")
    if info.has_upper:
        flags.append("upper")
    if info.has_number:
        flags.append("numbers")
    if info.has_symbol:
        flags.append("symbols")
    if info.has_non_ascii:
        flags.append("non-ASCII")
    return [
        f"Password:  {shown or '(empty)'}",
        f"Length:    {info.length}",
        f"Charset:   {info.charset_size} [{', '.join(flags) or 'none'}]",
    ]


def _score_lines(result: AuditResult) -> list[str]:
    score = result.score
    if score is None:
        return ["No score available."]
    color = _color_for_rating(score.rating)
    label = score.rating.upper()
    raw = (
        f"zxcvbn {score.raw_score_0_4}/4"
        if score.raw_score_0_4 is not None
        else "native heuristic (no zxcvbn score)"
    )
    lines = [
        f"{color}{C.BOLD}{label}{C.RESET}  {color}{score.value}/100{C.RESET}   {dim(raw)}",
        f"{color}{_bar(score.value)}{C.RESET}",
    ]
    if score.capped_by == "hibp":
        lines.append(err("Score forced to 0 because the password appears in a breach."))
    if result.engine_used == "native":
        lines.append(warn("Legacy native engine: no sequence, feedback, or crack-time detail."))
    return lines


_CRACK_LABELS = {
    "online_throttling_100_per_hour": "Online, throttled (100/hour)",
    "online_no_throttling_10_per_second": "Online, unthrottled (10/sec)",
    "offline_slow_hashing_1e4_per_second": "Offline, slow hash (10k/sec)",
    "offline_fast_hashing_1e10_per_second": "Offline, fast hash (10B/sec)",
}


def _crack_lines(result: AuditResult) -> list[str]:
    if not result.crack_times_display:
        return ["No zxcvbn crack-time estimate available."]
    lines = []
    for key, label in _CRACK_LABELS.items():
        value = result.crack_times_display.get(key)
        if value:
            lines.append(f"{label:<34} {bold(value)}")
    return lines


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "?"
    if number >= 1e15:
        return f"{number:.2e}"
    if number >= 1000:
        return f"{number:,.0f}"
    if number >= 1:
        return f"{number:.2f}".rstrip("0").rstrip(".")
    return f"{number:.3g}"


def _match_detail(match: Mapping[str, Any]) -> str:
    pattern = str(match.get("pattern") or "unknown")
    if pattern == "dictionary":
        detail = f"dictionary: {match.get('dictionary_name') or '?'}"
        if match.get("rank") is not None:
            detail += f", rank {match.get('rank')}"
        if match.get("reversed"):
            detail += ", reversed"
        if match.get("l33t"):
            detail += ", l33t"
        return detail
    if pattern == "spatial":
        return f"keyboard: {match.get('graph') or '?'}, {match.get('turns') or '?'} turns"
    if pattern == "repeat":
        return f"repeated {match.get('repeat_count') or '?'} times"
    if pattern == "sequence":
        return f"sequence: {match.get('sequence_name') or '?'}"
    if pattern == "regex":
        return f"regex: {match.get('regex_name') or '?'}"
    if pattern == "date":
        parts = [match.get("year"), match.get("month"), match.get("day")]
        if any(part is not None for part in parts):
            return "date: " + "-".join(str(part or "?") for part in parts)
        return "date pattern"
    if pattern == "bruteforce":
        return "brute-force"
    if pattern == "pwned":
        return "found in HaveIBeenPwned"
    return pattern


def _sequence_lines(result: AuditResult, mask_mode: bool) -> list[str]:
    if not result.sequence:
        if result.engine_used == "native":
            return ["Native engine does not expose sequence matches."]
        return ["No matches: zxcvbn did not find a recognisable pattern."]
    lines = []
    for index, match in enumerate(result.sequence, start=1):
        token = str(match.get("token") or "")
        shown = "*" * len(token) if mask_mode else token
        shown = shown if shown else "(empty)"
        detail = _match_detail(match)
        guesses = _format_number(match.get("guesses"))
        lines.append(
            f"{index:>2}. {bold(shown)}  {detail}  {dim('guesses: ' + guesses)}"
        )
    return lines


def _feedback_lines(result: AuditResult) -> list[str]:
    feedback = result.feedback
    if feedback is None:
        return ["No feedback available."]
    lines: list[str] = []
    if feedback.warning:
        lines.append(err(f"Warning: {feedback.warning}"))
    if feedback.suggestions:
        lines.append("Suggestions:")
        lines.extend(f"  • {item}" for item in feedback.suggestions)
    if not lines:
        lines.append("No specific zxcvbn feedback.")
    return lines


def _breach_lines(result: AuditResult) -> tuple[list[str], str]:
    breach = result.breach
    if breach is None:
        return ["No breach information available."], C.DIM
    if not breach.checked:
        if breach.reason == "offline":
            return [
                warn("OFFLINE: breach check skipped because --offline was used."),
                dim("No network request was made."),
            ], C.YELLOW
        return [
            warn("Breach check disabled."),
            dim("Use the default mode (without --no-breach-check) to enable HIBP."),
        ], C.YELLOW
    if breach.pwned is None or breach.reason == "api_error":
        return [
            err("UNKNOWN: HaveIBeenPwned could not be reached."),
            "This password must not be treated as safe.",
            dim("Exit code 5 indicates an unknown breach status."),
        ], C.RED
    if breach.pwned:
        count = _format_number(breach.breach_count) if breach.breach_count else "many"
        return [
            err("FOUND IN DATA BREACHES"),
            f"Seen {bold(count)} times in the HaveIBeenPwned corpus.",
            "Change this password everywhere it is used.",
        ], C.RED
    return [
        ok("Not found in HaveIBeenPwned."),
        dim("Checked with k-anonymity: only a 5-character SHA-1 prefix was sent."),
    ], C.GREEN


def _engine_line(result: AuditResult) -> str:
    if result.engine_used is None:
        requested = result.engine_requested
        return dim(f"Engine: unavailable (requested: {requested})")
    version = f" {result.engine_version}" if result.engine_version else ""
    line = f"Engine: {result.engine_used}{version}"
    if result.engine_fallback:
        line += " (auto fallback: Node/zxcvbn-ts unavailable)"
    if result.calc_time is not None:
        line += f"  ·  {result.calc_time:.0f} ms"
    return dim(line)


def print_output(
    result: AuditResult,
    password: str,
    mask_mode: bool = False,
    view: str = "full",
) -> None:
    """Print a result in full, short, or dark-web-only mode."""
    _banner()

    if result.error:
        _print_lines(_box("ERROR", [err(result.error)], color=C.RED))
        if result.engine_used is None and result.engine_requested:
            print(dim(f"Requested engine: {result.engine_requested}"))
        return

    if view == "darkweb":
        breach, color = _breach_lines(result)
        _print_lines(_box("BREACH CHECK", breach, color=color))
        print(_engine_line(result))
        return

    if view == "short":
        _print_lines(_box("SCORE", _score_lines(result), color=_color_for_rating(result.score.rating if result.score else "weak")))
        breach, color = _breach_lines(result)
        _print_lines(_box("BREACH CHECK", breach, color=color))
        print(_engine_line(result))
        return

    _print_lines(_box("INPUT", _input_lines(result, password, mask_mode), color=C.CYAN))
    score_color = _color_for_rating(result.score.rating if result.score else "weak")
    _print_lines(_box("SCORE", _score_lines(result), color=score_color))
    _print_lines(_box("TIME TO CRACK", _crack_lines(result), color=C.BLUE))
    _print_lines(_box("WHY", _sequence_lines(result, mask_mode), color=C.MAGENTA))
    _print_lines(_box("FEEDBACK", _feedback_lines(result), color=C.YELLOW))
    breach, breach_color = _breach_lines(result)
    _print_lines(_box("BREACH CHECK", breach, color=breach_color))
    print(_engine_line(result))


__all__ = [
    "ANIMATE",
    "C",
    "USE_COLOR",
    "bold",
    "dim",
    "err",
    "get_width",
    "ok",
    "print_output",
    "warn",
]
