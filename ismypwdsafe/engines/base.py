from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, Tuple


class EngineError(RuntimeError):
    """Raised when a scoring engine cannot be used or fails while scoring."""


_SCORE_PERCENT = {0: 0, 1: 25, 2: 50, 3: 75, 4: 100}
_SCORE_RATING = {0: "weak", 1: "weak", 2: "medium", 3: "strong", 4: "strong"}


def score_percent(raw_score: int) -> int:
    return _SCORE_PERCENT.get(raw_score, 0)


def score_rating(raw_score: int) -> str:
    return _SCORE_RATING.get(raw_score, "weak")


@dataclass(frozen=True)
class EngineResult:
    """Normalized result from a scoring engine.

    The shape is a deliberately small common denominator. zxcvbn engines fill
    in the explanation fields; the native fallback only fills score/breach.
    """

    engine_name: str
    engine_version: Optional[str]
    raw_score_0_4: Optional[int]
    score_100: int
    rating: str
    guesses: Optional[float] = None
    guesses_log10: Optional[float] = None
    crack_times_seconds: Dict[str, Optional[float]] = field(default_factory=dict)
    crack_times_display: Dict[str, str] = field(default_factory=dict)
    feedback_warning: Optional[str] = None
    feedback_suggestions: Tuple[str, ...] = ()
    sequence: Tuple[Dict[str, Any], ...] = ()
    calc_time: Optional[float] = None
    pwned: Optional[bool] = None
    pwned_count: Optional[int] = None
    hibp_status: str = "disabled"
    hibp_error: Optional[str] = None


class EngineBackend(Protocol):
    name: str

    def score(self, password: str, *, check_breach: bool = True) -> EngineResult:
        ...
