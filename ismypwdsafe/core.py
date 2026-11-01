"""Core analysis: zxcvbn-first result model and orchestration."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any, Mapping, Optional, Tuple

from . import network
from .engines import EngineError, make_engine, resolve_engine
from .metrics import calc_charset

SCHEMA_VERSION = "2.0"

EXIT_OK = 0
EXIT_WEAK = 1
EXIT_USAGE = 2
EXIT_PWNED = 3
EXIT_ENGINE = 4
EXIT_HIBP_UNKNOWN = 5
EXIT_INTERRUPTED = 130

# Backwards-compatible aliases for callers that used the 1.x names.
EXIT_DATA = EXIT_USAGE
EXIT_INTERNAL = EXIT_ENGINE


@dataclass(frozen=True)
class InputInfo:
    length: int
    charset_size: int
    has_lower: bool
    has_upper: bool
    has_number: bool
    has_symbol: bool
    has_non_ascii: bool


@dataclass(frozen=True)
class ScoreResult:
    value: int
    rating: str
    raw_score_0_4: Optional[int]
    capped_by: Optional[str] = None


@dataclass(frozen=True)
class FeedbackInfo:
    warning: Optional[str] = None
    suggestions: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AuditResult:
    schema_version: str
    tool_version: str
    exit_code: int
    error: Optional[str]
    input: Optional[InputInfo]
    score: Optional[ScoreResult]
    guesses: Optional[float]
    guesses_log10: Optional[float]
    crack_times_seconds: Mapping[str, Optional[float]] = field(default_factory=dict)
    crack_times_display: Mapping[str, str] = field(default_factory=dict)
    feedback: Optional[FeedbackInfo] = None
    sequence: Tuple[Mapping[str, Any], ...] = ()
    breach: Optional[network.BreachResult] = None
    engine_requested: str = "auto"
    engine_used: Optional[str] = None
    engine_version: Optional[str] = None
    engine_fallback: bool = False
    calc_time: Optional[float] = None


def _tool_version() -> str:
    # In a source checkout version.txt is authoritative. In an installed wheel
    # it is absent and package metadata is used instead.
    version_file = Path(__file__).resolve().parent.parent / "version.txt"
    try:
        return version_file.read_text(encoding="utf-8").strip()
    except OSError:
        try:
            return metadata.version("ismypwdsafe")
        except metadata.PackageNotFoundError:
            return "0.0.0+unknown"


def _input_info(password: str) -> InputInfo:
    charset_size, lower, upper, number, symbol, non_ascii = calc_charset(password)
    return InputInfo(
        length=len(password),
        charset_size=charset_size,
        has_lower=lower,
        has_upper=upper,
        has_number=number,
        has_symbol=symbol,
        has_non_ascii=non_ascii,
    )


def _error_result(
    message: str,
    code: int,
    requested: str,
    used: Optional[str] = None,
) -> AuditResult:
    return AuditResult(
        schema_version=SCHEMA_VERSION,
        tool_version=_tool_version(),
        exit_code=code,
        error=message,
        input=None,
        score=None,
        guesses=None,
        guesses_log10=None,
        crack_times_seconds={},
        crack_times_display={},
        feedback=None,
        sequence=(),
        breach=None,
        engine_requested=requested,
        engine_used=used,
        engine_version=None,
        engine_fallback=False,
        calc_time=None,
    )


def _finite(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def analyze_password(
    password: str,
    *,
    check_breach: bool = True,
    breach_skip_reason: Optional[str] = None,
    engine_name: str = "auto",
) -> AuditResult:
    """Audit a password and return a normalized, JSON-safe result.

    ``auto`` uses zxcvbn-ts when Node.js 18+ is available, then zxcvbn-python,
    and never silently falls back to the native heuristic. The native engine is
    available only when explicitly requested.
    """
    requested = engine_name or "auto"
    if not password:
        return _error_result(
            "No password provided. Pass a password as an argument, use '-', "
            "or provide one on stdin.",
            EXIT_USAGE,
            requested,
        )

    try:
        used = resolve_engine(requested)
        engine = make_engine(used)
        engine_result = engine.score(password, check_breach=check_breach)
    except EngineError as exc:
        return _error_result(str(exc), EXIT_ENGINE, requested)
    except Exception as exc:  # noqa: BLE001 - CLI must never traceback on engine failure
        return _error_result(f"Engine failure: {exc}", EXIT_ENGINE, requested)

    if not check_breach:
        breach = network.BreachResult(
            checked=False,
            pwned=None,
            breach_count=None,
            reason=breach_skip_reason or "disabled",
        )
    elif engine_result.hibp_status == "error":
        breach = network.BreachResult(True, None, None, "api_error")
    else:
        breach = network.BreachResult(
            checked=True,
            pwned=engine_result.pwned,
            breach_count=engine_result.pwned_count,
            reason=None,
        )

    value = engine_result.score_100
    rating = engine_result.rating
    capped_by: Optional[str] = None
    if breach.checked and breach.pwned:
        value = 0
        rating = "weak"
        capped_by = "hibp"

    if breach.checked and breach.pwned is None:
        exit_code = EXIT_HIBP_UNKNOWN
    elif breach.pwned:
        exit_code = EXIT_PWNED
    elif value < 50:
        exit_code = EXIT_WEAK
    else:
        exit_code = EXIT_OK

    feedback = FeedbackInfo(
        warning=engine_result.feedback_warning,
        suggestions=tuple(engine_result.feedback_suggestions),
    )

    return AuditResult(
        schema_version=SCHEMA_VERSION,
        tool_version=_tool_version(),
        exit_code=exit_code,
        error=None,
        input=_input_info(password),
        score=ScoreResult(
            value=max(0, min(100, int(value))),
            rating=rating,
            raw_score_0_4=engine_result.raw_score_0_4,
            capped_by=capped_by,
        ),
        guesses=_finite(engine_result.guesses),
        guesses_log10=_finite(engine_result.guesses_log10),
        crack_times_seconds={
            key: _finite(value)
            for key, value in engine_result.crack_times_seconds.items()
        },
        crack_times_display=dict(engine_result.crack_times_display),
        feedback=feedback,
        sequence=tuple(engine_result.sequence),
        breach=breach,
        engine_requested=requested,
        engine_used=used,
        engine_version=engine_result.engine_version,
        engine_fallback=requested == "auto" and used != "ts",
        calc_time=_finite(engine_result.calc_time),
    )


def compute_exit_code(result: AuditResult) -> int:
    """Return the result's exit code.

    Kept as a small compatibility helper for 1.x callers; new code should read
    ``AuditResult.exit_code`` directly.
    """
    return result.exit_code


__all__ = [
    "AuditResult",
    "FeedbackInfo",
    "InputInfo",
    "SCHEMA_VERSION",
    "ScoreResult",
    "analyze_password",
    "compute_exit_code",
    "EXIT_DATA",
    "EXIT_ENGINE",
    "EXIT_HIBP_UNKNOWN",
    "EXIT_INTERNAL",
    "EXIT_INTERRUPTED",
    "EXIT_OK",
    "EXIT_PWNED",
    "EXIT_USAGE",
    "EXIT_WEAK",
]
