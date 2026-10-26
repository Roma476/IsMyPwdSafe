"""Core analysis engine: data model and orchestration."""
from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from typing import Optional, Tuple

from . import network, patterns

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
    has_non_ascii: bool


@dataclass(frozen=True)
class EntropyInfo:
    log10_value: float
    combinations: Optional[int]


@dataclass(frozen=True)
class ScoreResult:
    value: int
    rating: str
    base: int
    capped_by: Optional[str]
    capped_by_rule: Optional[str] = None


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


SCRIPT_CHARSETS = {
    "CYRILLIC": 33,
    "GREEK": 24,
    "ARABIC": 28,
    "HEBREW": 22,
    "CJK": 5000,
    "EMOJI": 1000,
    "LATIN": 200,
    "OTHER": 500,
}

def calc_charset(password: str) -> tuple[int, bool, bool, bool, bool, bool]:
    number = lower = upper = symbol = False
    has_non_ascii = False
    total = 0
    
    # Track non-ASCII script counts
    non_ascii_chars = []
    
    for char in password:
        if ord(char) > 127:
            has_non_ascii = True
            non_ascii_chars.append(char)
            continue
            
        if char.isdigit() and not number:
            number = True
            total += 10
        elif char.islower() and not lower:
            lower = True
            total += 26
        elif char.isupper() and not upper:
            upper = True
            total += 26
        elif not char.isalnum() and not symbol:
            symbol = True
            total += 33

    if has_non_ascii:
        # Identify dominant script
        scripts = set()
        for char in non_ascii_chars:
            cp = ord(char)
            # Check if it's an emoji by code point ranges
            if (
                (0x1F300 <= cp <= 0x1FAFF)
                or (0x2600 <= cp <= 0x27BF)
                or (0x1F1E6 <= cp <= 0x1F1FF)
                or (0x1F3FB <= cp <= 0x1F3FF)
            ):
                scripts.add("EMOJI")
            else:
                try:
                    name = unicodedata.name(char)
                    script = name.split()[0]
                    if script in SCRIPT_CHARSETS:
                        scripts.add(script)
                    else:
                        scripts.add("OTHER")
                except ValueError:
                    scripts.add("OTHER")
        
        # Add the charset of the largest non-ASCII script
        if scripts:
            max_script = max(scripts, key=lambda s: SCRIPT_CHARSETS.get(s, 500))
            total += SCRIPT_CHARSETS.get(max_script, 500)

    return total, lower, upper, number, symbol, has_non_ascii


def calc_combinations(charset_size: int, length: int) -> tuple[Optional[int], float]:
    log10_value = length * math.log10(charset_size) if charset_size > 0 else 0
    if must_use_log(charset_size, length):
        return None, log10_value
    return charset_size ** length, log10_value


PATTERN_PENALTIES = {
    "top150":      1.0,
    "repetition":  2.0,
    "qwerty_walk": 3.0,
    "common_year": 4.0,
}
WHOLE_INPUT_ONLY = {"common_year"}

def calculate_score(
    log10_value: float,
    pattern: patterns.PatternResult,
    breach: network.BreachResult,
    password_length: int,
    has_non_ascii: bool = False,
) -> ScoreResult:
    """
    Weighted scoring based on estimated guesses (zxcvbn-like).
    The weakest link dictates the score.
    """
    guesses_log10 = log10_value
    capped_by = None
    capped_by_rule = None

    if pattern.detected:
        penalties = []
        for rule in pattern.rules_fired:
            if rule not in PATTERN_PENALTIES:
                continue
            if rule in WHOLE_INPUT_ONLY and password_length != 4:
                continue  # not the whole input, skip the cap
            penalties.append((rule, PATTERN_PENALTIES[rule]))

        if penalties:
            worst_rule, worst_penalty = min(penalties, key=lambda x: x[1])
            if worst_penalty < guesses_log10:
                guesses_log10 = worst_penalty
                capped_by = "pattern"
                capped_by_rule = worst_rule

    elif has_non_ascii:
        # Dictionary miss: non-ASCII password with no pattern matched.
        # Cap it at 50 (guesses_log10 = 10.0) until we ship multilingual dictionaries.
        guesses_log10 = min(guesses_log10, 10.0)
        capped_by = "unicode_miss"
        capped_by_rule = None

    if breach.checked and breach.breach_count is not None and breach.breach_count > 0:
        guesses_log10 = 1.0  # 10 guesses (preserve 1.x behavior)
        capped_by = "breach"
        capped_by_rule = None

    # Use * 5 to keep the scale consistent with 1.5.x
    value = int(round(min(100.0, max(0.0, guesses_log10 * 5))))
    base  = int(round(min(100.0, max(0.0, log10_value * 5))))

    if guesses_log10 < 5:
        rating = "weak"
    elif guesses_log10 < 10:
        rating = "medium"
    else:
        rating = "strong"

    return ScoreResult(
        value=value,
        rating=rating,
        base=base,
        capped_by=capped_by,
        capped_by_rule=capped_by_rule,
    )

def compute_hardware_estimates(log10_value: float) -> Tuple[HardwareEstimate, ...]:
    out: list[HardwareEstimate] = []
    for key, label, aps in _HARDWARE_PROFILES:
        try:
            seconds = (10 ** log10_value) / aps
        except OverflowError:
            seconds = float("inf")
        out.append(HardwareEstimate(key=key, label=label, attempts_per_second=aps, seconds=seconds))
    return tuple(out)

def compute_exit_code(score: ScoreResult, breach: network.BreachResult) -> int:
    """Compute the semantic exit code for CI/CD pipelines."""
    if breach.checked and breach.pwned:
        return 3
    if score.value < 50:
        return 1
    return 0

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
        from . import __version__ as package_version
        tool_version = package_version

    if not password:
        return AuditResult(
            schema_version=SCHEMA_VERSION,
            tool_version=tool_version,
            exit_code=EXIT_DATA,
            error="No password provided",
            input=None, entropy=None, pattern=None, breach=None,
            score=None, hardware=(),
        )

    charset, has_low, has_upp, has_num, has_sym, has_unicode = calc_charset(password)
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
            checked=False, pwned=None, breach_count=None, reason=breach_skip_reason,
        )

    score = calculate_score(log10_value, pattern_result, breach_result, length, has_unicode)
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
            has_non_ascii=has_unicode,
        ),
        entropy=EntropyInfo(log10_value=log10_value, combinations=combinations),
        pattern=pattern_result,
        breach=breach_result,
        score=score,
        hardware=hardware,
    )