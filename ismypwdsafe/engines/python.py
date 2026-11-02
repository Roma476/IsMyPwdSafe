from __future__ import annotations

from datetime import timedelta
from importlib import metadata
from typing import Any, Dict, Optional

from .. import network
from .base import EngineError, EngineResult, score_percent, score_rating

_SEQUENCE_KEYS = {
    "matchedWord": "matched_word",
    "dictionaryName": "dictionary_name",
    "baseToken": "base_token",
    "baseGuesses": "base_guesses",
    "repeatCount": "repeat_count",
    "sequenceName": "sequence_name",
    "sequenceSpace": "sequence_space",
    "regexName": "regex_name",
    "regexMatch": "regex_match",
    "shiftedCount": "shifted_count",
    "pwnedAmount": "pwned_amount",
    "subDisplay": "sub_display",
    "guessesLog10": "guesses_log10",
    "uppercaseVariations": "uppercase_variations",
    "l33tVariations": "l33t_variations",
}


def _normalize_match(match: Dict[str, Any]) -> Dict[str, Any]:
    return {_SEQUENCE_KEYS.get(key, key): value for key, value in match.items()}


def _version() -> Optional[str]:
    try:
        return metadata.version("zxcvbn")
    except metadata.PackageNotFoundError:
        return None


def _calc_time_ms(value: Any) -> Optional[float]:
    """Convert zxcvbn-python's timedelta to the contract's milliseconds."""
    if isinstance(value, timedelta):
        return value.total_seconds() * 1000.0
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class PythonZxcvbnEngine:
    name = "python"

    def __init__(self) -> None:
        try:
            import zxcvbn
        except ImportError as exc:
            raise EngineError(
                "--engine=python requires the 'zxcvbn' package. Install it with: "
                "pip install ismypwdsafe[python]"
            ) from exc
        self._zxcvbn = zxcvbn.zxcvbn

    def score(self, password: str, *, check_breach: bool = True) -> EngineResult:
        try:
            raw = self._zxcvbn(password)
        except Exception as exc:  # pragma: no cover - defensive
            raise EngineError(f"zxcvbn-python failed: {exc}") from exc

        raw_score = int(raw.get("score", 0))
        feedback = raw.get("feedback") or {}
        sequence = tuple(
            _normalize_match(dict(item)) for item in raw.get("sequence", [])
            if isinstance(item, dict)
        )
        crack_seconds: Dict[str, Optional[float]] = {
            str(key): value for key, value in (raw.get("crack_times_seconds") or {}).items()
        }
        crack_display: Dict[str, str] = {
            str(key): str(value) for key, value in (raw.get("crack_times_display") or {}).items()
        }

        pwned: Optional[bool] = None
        pwned_count: Optional[int] = None
        hibp_error: Optional[str] = None
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
            engine_version=_version(),
            raw_score_0_4=raw_score,
            score_100=score_percent(raw_score),
            rating=score_rating(raw_score),
            guesses=raw.get("guesses"),
            guesses_log10=raw.get("guesses_log10"),
            crack_times_seconds=crack_seconds,
            crack_times_display=crack_display,
            feedback_warning=feedback.get("warning"),
            feedback_suggestions=tuple(feedback.get("suggestions") or ()),
            sequence=sequence,
            calc_time=_calc_time_ms(raw.get("calc_time")),
            pwned=pwned,
            pwned_count=pwned_count,
            hibp_status=hibp_status,
            hibp_error=hibp_error,
        )
