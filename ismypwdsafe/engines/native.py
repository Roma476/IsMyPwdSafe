from __future__ import annotations

from .. import network, patterns
from ..metrics import calc_charset, calc_combinations
from .base import EngineResult


class NativeEngine:
    """Legacy 1.x heuristic engine. It is intentionally not zxcvbn."""

    name = "native"

    def score(self, password: str, *, check_breach: bool = True) -> EngineResult:
        charset, _, _, _, _, _ = calc_charset(password)
        _, log10_value = calc_combinations(charset, len(password))
        value = int(min(100, max(0, log10_value * 5)))

        pattern_result = patterns.detect_pattern(password)
        if pattern_result.detected:
            value = min(value, 30)

        if pattern_result.detected or log10_value < 10:
            rating = "weak"
        elif log10_value < 14:
            rating = "medium"
        else:
            rating = "strong"

        pwned = None
        pwned_count = None
        hibp_error = None
        if not check_breach:
            hibp_status = "disabled"
        else:
            breach = network.check_breach(password)
            pwned = breach.pwned
            pwned_count = breach.breach_count
            hibp_error = breach.reason
            if breach.reason == "api_error":
                hibp_status = "error"
            elif breach.pwned:
                hibp_status = "pwned"
            else:
                hibp_status = "clean"

        return EngineResult(
            engine_name=self.name,
            engine_version=None,
            raw_score_0_4=None,
            score_100=value,
            rating=rating,
            pwned=pwned,
            pwned_count=pwned_count,
            hibp_status=hibp_status,
            hibp_error=hibp_error,
        )
