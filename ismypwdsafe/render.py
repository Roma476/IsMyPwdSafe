"""Stable JSON output and privacy redaction."""
from __future__ import annotations

import json
import math
from dataclasses import asdict
from typing import Any, Dict, Iterable, Mapping, cast

from .core import AuditResult

# Values that can contain the password, a dictionary word, or a fragment of it.
_SENSITIVE_MATCH_KEYS = {
    "token",
    "matched_word",
    "base_token",
    "sub_display",
    "regex_match",
    "subs",
}


def _sanitize(value: Any) -> Any:
    """Convert dataclass output to strict JSON values (no NaN/Infinity)."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(item) for item in value]
    return str(value)


def _redact_match(match: Mapping[str, Any]) -> Dict[str, Any]:
    redacted: Dict[str, Any] = {}
    for key, value in match.items():
        if key in _SENSITIVE_MATCH_KEYS:
            redacted[str(key)] = "<redacted>"
        else:
            redacted[str(key)] = _sanitize(value)
    return redacted


def _redact_sequence(
    sequence: Iterable[Mapping[str, Any]],
) -> list[Dict[str, Any]]:
    return [_redact_match(match) for match in sequence]


def result_to_dict(result: AuditResult, *, include_tokens: bool = False) -> Dict[str, Any]:
    data = asdict(result)
    data["redacted"] = not include_tokens
    if not include_tokens:
        data["sequence"] = _redact_sequence(result.sequence)
    return cast(Dict[str, Any], _sanitize(data))


def render_json(result: AuditResult, *, include_tokens: bool = False) -> str:
    """Render the v2 JSON contract. Tokens are redacted unless requested."""
    payload = result_to_dict(result, include_tokens=include_tokens)
    return json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
    )


__all__ = ["render_json", "result_to_dict"]
