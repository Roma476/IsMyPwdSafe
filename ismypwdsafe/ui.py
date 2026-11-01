# ruff: noqa: E501
"""Terminal rendering for the zxcvbn-first result model."""
from __future__ import annotations

import os
import re
import shutil
import sys
import textwrap
import time
from typing import Any, Iterable, Mapping, Optional, Sequence

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
    width = max(1, width)
    filled = round(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def _layout_width() -> int:
    """Use the terminal width, leaving one column of breathing room."""
    return max(40, get_width() - 2)


def _wrap_line(text: str, width: int) -> list[str]:
    """Wrap visible characters without counting ANSI escape sequences."""
    plain = _ANSI.sub("", str(text))
    leading = ""
    position = 0
    while True:
        match = _ANSI.match(str(text), position)
        if match is None:
            break
        leading += match.group(0)
        position = match.end()
    parts = textwrap.wrap(
        plain,
        width=width,
        break_long_words=True,
        break_on_hyphens=False,
        replace_whitespace=False,
    ) or [""]
    if leading:
        return [leading + part + C.RESET for part in parts]
    return parts


def _box(
    title: str,
    lines: Sequence[str],
    *,
    color: str = "",
    width: Optional[int] = None,
) -> list[str]:
    width = max(40, width if width is not None else _layout_width())
    inner = max(20, width - 4)
    rendered: list[str] = []
    title_text = f" {title} "
    if _visible_len(title_text) > width - 2:
        title_text = f" {title[: max(0, width - 4)]} "
    available = max(0, width - 2 - _visible_len(title_text))
    left = available // 2
    right = available - left
    top = "┌" + "─" * left + title_text + "─" * right + "┐"
    rendered.append((color or "") + top + C.RESET)
    for line in lines:
        if not line:
            rendered.append(
                (color or "")
                + "│"
                + C.RESET
                + " " * (width - 2)
                + (color or "")
                + "│"
                + C.RESET
            )
            continue
        wrapped = _wrap_line(str(line), inner)
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


def _columns(
    left_title: str,
    left_lines: Sequence[str],
    left_color: str,
    right_title: str,
    right_lines: Sequence[str],
    right_color: str,
    *,
    width: Optional[int] = None,
) -> list[str]:
    """Render two boxes side by side without losing box borders."""
    total = max(40, width if width is not None else _layout_width())
    gap = 2
    left_width = (total - gap) // 2
    right_width = total - gap - left_width
    left = _box(left_title, left_lines, color=left_color, width=left_width)
    right = _box(right_title, right_lines, color=right_color, width=right_width)

    def _pad_rows(box: list[str], color: str, width: int, rows: int) -> list[str]:
        if rows <= 0:
            return box
        bottom = box.pop()
        interior = (color or "") + "│" + C.RESET + " " * (width - 2) + (color or "") + "│" + C.RESET
        box.extend([interior] * rows)
        box.append(bottom)
        return box

    rows = max(len(left), len(right)) - 2
    _pad_rows(left, left_color, left_width, rows - (len(left) - 2))
    _pad_rows(right, right_color, right_width, rows - (len(right) - 2))
    return [
        _pad(left_line, left_width) + " " * gap + _pad(right_line, right_width)
        for left_line, right_line in zip(left, right)
    ]


def _print_lines(lines: Iterable[str], *, animate: bool = False) -> None:
    for line in lines:
        print(line)
        if animate:
            time.sleep(0.012)


_BANNER_ART = (
    r"                                                                                                        ",
    r"$$$$$$\           $$\      $$\           $$$$$$$\                      $$\  $$$$$$\             $$$$$$\ ",
    r"\_$$  _|          $$$\    $$$ |          $$  __$$\                     $$ |$$  __$$\           $$  __$$\ ",
    r"  $$ |   $$$$$$$\ $$$$\  $$$$ |$$\   $$\ $$ |  $$ |$$\  $$\  $$\  $$$$$$$ |$$ /  \__| $$$$$$\  $$ /  \__|$$$$$$\ ",
    r"  $$ |  $$  _____|$$\$$\$$ $$ |$$ |  $$ |$$$$$$$  |$$ | $$ | $$ |$$  __$$ |\$$$$$$\   \____$$\ $$$$\    $$  __$$\ ",
    r"  $$ |  \$$$$$$\  $$ \$$$  $$ |$$ |  $$ |$$  ____/ $$ | $$ | $$ |$$ /  $$ | \____$$\  $$$$$$$ |$$  _|   $$$$$$$$ |",
    r"  $$ |   \____$$\ $$ |\$  /$$ |$$ |  $$ |$$ |      $$ | $$ | $$ |$$ |  $$ |$$\   $$ |$$  __$$ |$$ |     $$   ____|",
    r"$$$$$$\ $$$$$$$  |$$ | \_/ $$ |\$$$$$$$ |$$ |      \$$$$$\$$$$  |\$$$$$$$ |\$$$$$$  |\$$$$$$$ |$$ |     \$$$$$$$\ ",
    r"\______|\_______/ \__|     \__| \____$$ |\__|       \_____\____/  \_______| \______/  \_______|\__|      \_______|",
    r"                               $$\   $$ |",
    r"                               \$$$$$$  |",
    r"                                \______/",
)


def _banner() -> None:
    if ANIMATE:
        print("\033[2J\033[H", end="")
    width = get_width()
    art_width = max(len(line) for line in _BANNER_ART)
    if width >= art_width:
        block_pad = max((width - art_width) // 2, 0)
        print()
        for line in _BANNER_ART:
            print(" " * block_pad + C.CYAN + C.BOLD + line + C.RESET)
        line = f"{dim('zxcvbn, but readable')}"
    else:
        line = f"{bold(C.CYAN + 'IsMyPwdSafe')} {dim('·')} {dim('zxcvbn, but readable')}"
    padding = max(0, (width - _visible_len(line)) // 2)
    print()
    print(" " * padding + line)
    print()


def _input_summary_line(result: AuditResult, password: str, mask_mode: bool) -> str:
    info = result.input
    if info is None:
        return ""
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
    return (
        f"Password: {shown or '(empty)'}  ·  Length: {info.length}  ·  "
        f"Charset: {info.charset_size} [{', '.join(flags) or 'none'}]"
    )


def _score_lines(result: AuditResult, width: int = 30) -> list[str]:
    score = result.score
    if score is None:
        return ["No score available."]
    color = _color_for_rating(score.rating)
    label = score.rating.upper()
    line = f"{color}{C.BOLD}{label}{C.RESET}  {color}{score.value}/100{C.RESET}"
    if score.raw_score_0_4 is None:
        line += f"   {dim('native heuristic')}"
    bar_width = max(20, width - 4)
    return [
        line,
        f"{color}{_bar(score.value, bar_width)}{C.RESET}",
    ]


_CRACK_LABELS = {
    "online_throttling_100_per_hour": "Online, 100/hour",
    "online_no_throttling_10_per_second": "Online, 10/sec",
    "offline_slow_hashing_1e4_per_second": "Offline, 10k/sec",
    "offline_fast_hashing_1e10_per_second": "Offline, 10B/sec",
}


def _crack_lines(result: AuditResult) -> list[str]:
    if not result.crack_times_display:
        return []
    lines = []
    for key, label in _CRACK_LABELS.items():
        value = result.crack_times_display.get(key)
        if value:
            lines.append(f"{label:<18} {bold(value)}")
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
        detail = str(match.get("dictionary_name") or "dictionary")
        if match.get("rank") is not None:
            detail += f" #{match.get('rank')}"
        if match.get("reversed"):
            detail += " rev"
        if match.get("l33t"):
            detail += " l33t"
        return detail
    if pattern == "spatial":
        return f"keyboard {match.get('graph') or '?'}, {match.get('turns') or '?'} turns"
    if pattern == "repeat":
        return f"repeat x{match.get('repeat_count') or '?'}"
    if pattern == "sequence":
        return f"sequence {match.get('sequence_name') or '?'}"
    if pattern == "regex":
        return f"regex {match.get('regex_name') or '?'}"
    if pattern == "date":
        parts = [match.get("year"), match.get("month"), match.get("day")]
        if any(part is not None for part in parts):
            return "date " + "-".join(str(part or "?") for part in parts)
        return "date pattern"
    if pattern == "bruteforce":
        return "brute-force"
    if pattern == "pwned":
        return "breach match"
    return pattern


def _sequence_lines(result: AuditResult, mask_mode: bool) -> list[str]:
    # The HIBP matcher adds a synthetic "pwned" match. The breach section
    # already reports it, so showing it again here would be repetitive.
    matches = [
        match
        for match in result.sequence
        if str(match.get("pattern") or "") != "pwned"
    ]
    if not matches:
        if result.engine_used == "native":
            return []
        if result.breach is not None and result.breach.pwned:
            return []
        return ["No zxcvbn pattern matched."]
    lines = []
    for index, match in enumerate(matches, start=1):
        token = str(match.get("token") or "")
        shown = "*" * len(token) if mask_mode else token
        shown = shown if shown else "(empty)"
        detail = _match_detail(match)
        lines.append(f"{index:>2}. {bold(shown)}  {detail}")
    return lines


def _is_breach_advice(text: str) -> bool:
    lower = text.lower()
    return "breach" in lower or "elsewhere" in lower or "pwned" in lower


def _feedback_lines(result: AuditResult) -> list[str]:
    feedback = result.feedback
    if feedback is None:
        return []

    pwned = result.breach is not None and bool(result.breach.pwned)
    lines: list[str] = []
    if feedback.warning and not (pwned and _is_breach_advice(feedback.warning)):
        lines.append(err(f"Warning: {feedback.warning}"))

    suggestions = [
        item
        for item in feedback.suggestions
        if not (pwned and _is_breach_advice(item))
    ]
    if suggestions:
        if lines:
            lines.append("")
        lines.extend(f"• {item}" for item in suggestions)
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
            err(f"FOUND IN HIBP  ·  seen {bold(count)} times"),
            "Change this password everywhere it is used.",
            dim("Final score capped at 0."),
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
    width = _layout_width()
    rating = result.score.rating if result.score else "weak"
    score_color = _color_for_rating(rating)

    if result.error:
        _print_lines(_box("ERROR", [err(result.error)], color=C.RED, width=width))
        if result.engine_used is None and result.engine_requested:
            print(dim(f"Requested engine: {result.engine_requested}"))
        return

    if view == "darkweb":
        breach, color = _breach_lines(result)
        _print_lines(_box("BREACH CHECK", breach, color=color, width=width))
        print()
        print(_engine_line(result))
        return

    if view == "short":
        _print_lines(
            _box(
                "SCORE",
                _score_lines(result, width),
                color=score_color,
                width=width,
            )
        )
        print()
        breach, color = _breach_lines(result)
        _print_lines(_box("BREACH CHECK", breach, color=color, width=width))
        print()
        print(_engine_line(result))
        return

    summary = _score_lines(result, width)
    input_line = _input_summary_line(result, password, mask_mode)
    if input_line:
        summary.extend(["", input_line])
    _print_lines(_box("SUMMARY", summary, color=score_color, width=width))
    print()

    crack_lines = _crack_lines(result)
    why_lines = _sequence_lines(result, mask_mode)
    if crack_lines and why_lines and width >= 88:
        _print_lines(
            _columns(
                "TIME TO CRACK",
                crack_lines,
                C.BLUE,
                "PATTERN MATCHES",
                why_lines,
                C.MAGENTA,
                width=width,
            )
        )
        print()
    else:
        if crack_lines:
            _print_lines(
                _box("TIME TO CRACK", crack_lines, color=C.BLUE, width=width)
            )
            print()
        if why_lines:
            _print_lines(
                _box("PATTERN MATCHES", why_lines, color=C.MAGENTA, width=width)
            )
            print()

    breach, breach_color = _breach_lines(result)
    _print_lines(_box("BREACH CHECK", breach, color=breach_color, width=width))
    print()

    feedback = _feedback_lines(result)
    if feedback:
        _print_lines(_box("WHAT TO DO", feedback, color=C.YELLOW, width=width))
        print()

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
