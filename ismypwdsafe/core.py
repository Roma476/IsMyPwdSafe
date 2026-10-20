"""Core analysis engine: data model and orchestration.

Pure logic, no I/O except what network.py does. Importable as a library:

    from ismypwdsafe import analyze_password
    result = analyze_password("hunter2", check_breach=False)
    print(result.score.value, result.score.rating)
"""
from dataclasses import dataclass
from typing import Optional, Tuple
import math

from . import patterns
from . import network


SCHEMA_VERSION = 1

# Exit codes. In 1.3.0 only 0 and 64/65/70 are returned; 1 and 3 are
# reserved for 1.5.0 when the semantic exit code contract lands.
EXIT_OK = 0
EXIT_USAGE = 64
EXIT_DATA = 65
EXIT_INTERNAL = 70


@dataclass(frozen=True)
class InputInfo:
    length: int
    charset_size: int
    has_lowercase: bool
    has_uppercase: bool
    has_digits: bool
    has_symbols: bool


@dataclass(frozen=True)
class EntropyInfo:
    log10_value: float
    combinations: Optional[int]


@dataclass(frozen=True)
class ScoreResult:
    value: int
    rating: str                 # "weak" | "medium" | "strong"
    base: int                   # entropy-only score before caps
    capped_by: Optional[str]    # None | "pattern" | "breach"


@dataclass(frozen=True)
class HardwareEstimate:
    key: str
    label: str
    attempts_per_second: float
    seconds: float


@dataclass(frozen=True)
class AuditResult:
    schema_version: int
    tool_version: str
    exit_code: int
    error: Optional[str]
    input: Optional[InputInfo]
    entropy: Optional[EntropyInfo]
    pattern: Optional[patterns.PatternResult]
    breach: Optional[network.BreachResult]
    score: Optional[ScoreResult]
    hardware: Tuple[HardwareEstimate, ...]


_HARDWARE_PROFILES = (
    ("pc_1k", "PC (1K/s)", 1e3),
    ("server_1m", "Server (1M/s)", 1e6),
    ("gpu_1b", "GPU Rig (1B/s)", 1e9),
    ("cluster_1t", "Cluster (1T/s)", 1e12),
)


def must_use_log(charset_size: int, length: int) -> bool:
    if charset_size > 95:
        return length >= 3
    if charset_size in (62, 63):
        return length >= 5
    return length >= 4


def calc_charset(password: str):
    number = lower = upper = symbol = False
    total = 0
    for char in password:
        if char.isdigit() and not number:
            number = True
            total += 10
        elif char.islower() and not lower:
            lower = True
            total += 26
        elif char.isupper() and not upper:
            upper = True
            total += 26
        elif not char.isalnum() and ord(char) < 128 and not symbol:
            symbol = True
            total += 33
    return total, lower, upper, number, symbol


def calc_combinations(charset_size: int, length: int):
    log10_value = length * math.log10(charset_size) if charset_size > 0 else 0
    if must_use_log(charset_size, length):
        return None, log10_value
    return charset_size ** length, log10_value


def calculate_score(
    log10_value: float,
    pattern: patterns.PatternResult,
    breach: network.BreachResult,
) -> ScoreResult:
    raw_base = int(min(100, max(0, log10_value * 5)))
    value = raw_base
    capped_by = None

    if pattern.detected:
        value = min(value, 30)
        capped_by = "pattern"
    if breach.checked and breach.pwned:
        value = min(value, 10)
        capped_by = "breach"

    if pattern.detected or log10_value < 10:
        rating = "weak"
    elif log10_value < 14:
        rating = "medium"
    else:
        rating = "strong"

    return ScoreResult(value=value, rating=rating, base=raw_base, capped_by=capped_by)


def compute_hardware_estimates(log10_value: float) -> Tuple[HardwareEstimate, ...]:
    out = []
    for key, label, aps in _HARDWARE_PROFILES:
        seconds = (10 ** log10_value) / aps
        out.append(HardwareEstimate(key=key, label=label, attempts_per_second=aps, seconds=seconds))
    return tuple(out)


def analyze_password(
    password: str,
    *,
    check_breach: bool = True,
    breach_skip_reason: Optional[str] = None,
    tool_version: Optional[str] = None,
) -> AuditResult:
    """
    Run the full audit on a password and return a structured result.

    check_breach=False skips the HIBP request. breach_skip_reason is stored
    verbatim in result.breach.reason ("offline", "disabled", or None).
    tool_version defaults to the package __version__ when not provided.
    """
    if tool_version is None:
        from . import __version__ as tool_version

    if not password:
        return AuditResult(
            schema_version=SCHEMA_VERSION,
            tool_version=tool_version,
            exit_code=EXIT_DATA,
            error="No password provided",
            input=None, entropy=None, pattern=None, breach=None,
            score=None, hardware=(),
        )

    charset, has_low, has_upp, has_num, has_sym = calc_charset(password)
    if charset == 0:
        return AuditResult(
            schema_version=SCHEMA_VERSION,
            tool_version=tool_version,
            exit_code=EXIT_DATA,
            error="Could not determine charset",
            input=None, entropy=None, pattern=None, breach=None,
            score=None, hardware=(),
        )

    length = len(password)
    combinations, log10_value = calc_combinations(charset, length)

    pattern_result = patterns.detect_pattern(password)

    if check_breach:
        breach_result = network.check_breach(password)
    else:
        breach_result = network.BreachResult(
            checked=False, pwned=None, count=None, reason=breach_skip_reason,
        )

    score = calculate_score(log10_value, pattern_result, breach_result)
    hardware = compute_hardware_estimates(log10_value)

    return AuditResult(
        schema_version=SCHEMA_VERSION,
        tool_version=tool_version,
        exit_code=EXIT_OK,
        error=None,
        input=InputInfo(
            length=length,
            charset_size=charset,
            has_lowercase=has_low,
            has_uppercase=has_upp,
            has_digits=has_num,
            has_symbols=has_sym,
        ),
        entropy=EntropyInfo(log10_value=log10_value, combinations=combinations),
        pattern=pattern_result,
        breach=breach_result,
        score=score,
        hardware=hardware,
    )