"""Parsing helpers for ``imps scan``.

The scanner deliberately uses a small, line-oriented parser instead of
``python-dotenv``.  We need line numbers for findings, and we must not
interpolate environment variables: a value such as ``${OTHER_SECRET}`` is a
reference, not a password to audit.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Key classification is intentionally conservative.  Password-like keys are
# always scored by zxcvbn.  Token-like keys are reported without a score.
_PASSWORD_KEY_RE = re.compile(
    r"(?:^|_)(PASSWORD|PASSWD|PASSPHRASE|PWD|PASS)(?:_|$)", re.IGNORECASE
)
_TOKEN_KEY_RE = re.compile(
    r"(?:^|_)(SECRET|TOKEN|API_KEY|ACCESS_KEY|PRIVATE_KEY|CLIENT_SECRET|AUTH_TOKEN)"
    r"(?:_|$)",
    re.IGNORECASE,
)
# Keys that contain "password" or "secret" but do not hold a credential value.
_SKIP_KEY_RE = re.compile(
    r"(?:^|_)(HASH|SALT|FILE|PATH|URL|URI|EMAIL|USER|USERNAME|LENGTH|MIN|MAX|RESET|"
    r"EXPIRY|EXPIRES|TTL|STRENGTH|POLICY|ENABLED|DISABLED|VERSION|ALGORITHM|ID)"
    r"(?:_|$)",
    re.IGNORECASE,
)

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")
_REFERENCE_RE = re.compile(r"^\$(?:\{[^}]+\}|[A-Za-z_][A-Za-z0-9_]*)$")

# Values that are almost always examples or deployment placeholders.  These are
# skipped rather than scored, so a stock .env.example does not produce noise.
_PLACEHOLDER_VALUES = {
    "",
    "...",
    "changeme",
    "change_me",
    "change-me",
    "example",
    "example_password",
    "replace_me",
    "replace-me",
    "todo",
    "your_password",
    "your-password",
    "yourpassword",
}

_PRIVATE_KEY_RE = re.compile(
    r"----(?:-| )BEGIN ([A-Z0-9 ]*PRIVATE KEY(?: BLOCK)?) ?(?:-----|----)"
)

# Dotenv escapes used inside double-quoted values.  Backslash-newline
# continuations are handled before this point.
_ESCAPES = {
    "n": "\n",
    "r": "\r",
    "t": "\t",
    '"': '"',
    "\\": "\\",
    "$": "$",
}


@dataclass(frozen=True)
class ParsedEntry:
    """A parsed ``KEY=VALUE`` pair.  The value is not written to output."""

    key: str
    value: str
    line: int


@dataclass(frozen=True)
class CriticalFinding:
    """A private key found in the raw text of a file."""

    key: str
    line: int
    key_format: str


@dataclass(frozen=True)
class ParseResult:
    entries: Tuple[ParsedEntry, ...]
    critical: Tuple[CriticalFinding, ...]
    warnings: Tuple[str, ...]
    unparseable_lines: int
    empty_values: int
    references: int
    placeholders: int


def _has_metadata_suffix(key: str) -> bool:
    """True when a metadata word follows a password/token word.

    This keeps ``PASSWORD_HASH`` and ``API_KEY_ID`` out of the report while
    still classifying ``USER_PASSWORD`` as a password.
    """
    credential_matches = [
        match
        for match in (_PASSWORD_KEY_RE.search(key), _TOKEN_KEY_RE.search(key))
        if match is not None
    ]
    if not credential_matches:
        return False
    first_credential = min(match.start() for match in credential_matches)
    return any(
        match.start() > first_credential for match in _SKIP_KEY_RE.finditer(key)
    )


def classify_key(key: str) -> Optional[str]:
    """Return ``"password"``, ``"token"``, or ``None`` for a key name.

    A key containing both a password word and a token word (for example
    ``PASSWORD_RESET_TOKEN``) is skipped when a metadata suffix follows the
    credential word.  The important property is that this function is
    deterministic and does not look at the value.
    """
    if not _KEY_RE.match(key):
        return None
    if _has_metadata_suffix(key):
        return None
    if _PASSWORD_KEY_RE.search(key):
        return "password"
    if _TOKEN_KEY_RE.search(key):
        return "token"
    return None


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in _PLACEHOLDER_VALUES:
        return True
    if lowered.startswith("<") and lowered.endswith(">"):
        return True
    if lowered.startswith("{{") and lowered.endswith("}}"):
        return True
    if re.fullmatch(r"x{3,}", lowered):
        return True
    return False


def _strip_unquoted_comment(value: str) -> str:
    """Remove a dotenv inline comment from an unquoted value.

    A ``#`` starts a comment only when it is at the start of the value or is
    preceded by whitespace.  ``a#b`` is therefore kept as ``a#b``.
    """
    if not value:
        return value
    for index, char in enumerate(value):
        if char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
    return value


def _parse_double_quoted(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a double-quoted value, including escapes and trailing comments."""
    out: List[str] = []
    escaped = False
    index = 1
    while index < len(raw):
        char = raw[index]
        if escaped:
            out.append(_ESCAPES.get(char, char))
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            trailing = raw[index + 1 :].strip()
            if trailing and not trailing.startswith("#"):
                return None, "trailing characters after quoted value"
            return "".join(out), None
        else:
            out.append(char)
        index += 1
    return None, "unterminated double quote"


def _parse_value(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse a dotenv value.

    Returns ``(value, warning)``.  ``value`` is ``None`` for malformed input.
    An empty string is returned as ``""`` and skipped by the caller.
    """
    raw = raw.strip()
    if not raw:
        return "", None

    if raw.startswith('"'):
        return _parse_double_quoted(raw)

    if raw.startswith("'"):
        end = raw.find("'", 1)
        if end == -1:
            return None, "unterminated single quote"
        trailing = raw[end + 1 :].strip()
        if trailing and not trailing.startswith("#"):
            return None, "trailing characters after quoted value"
        return raw[1:end], None

    value = _strip_unquoted_comment(raw)
    return value, None


def _ends_with_continuation(line: str) -> bool:
    """True when a line ends with an unescaped backslash."""
    trailing = len(line) - len(line.rstrip("\\"))
    return trailing % 2 == 1


def _logical_lines(text: str) -> List[Tuple[int, str]]:
    """Join backslash continuations, preserving the starting line number."""
    physical = text.splitlines()
    logical: List[Tuple[int, str]] = []
    index = 0
    while index < len(physical):
        start = index + 1
        line = physical[index]
        index += 1
        while _ends_with_continuation(line) and index < len(physical):
            line = line[:-1] + physical[index]
            index += 1
        logical.append((start, line))
    return logical


def _critical_key(text: str, offset: int) -> str:
    prefix = text[:offset]
    matches = list(
        re.finditer(
            r"(?m)^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_.-]*)\s*=",
            prefix,
        )
    )
    if matches:
        return matches[-1].group(1)
    return "PRIVATE_KEY"


def parse_env_text(text: str) -> ParseResult:
    """Parse dotenv text and find private-key blocks without exposing values."""
    if text.startswith("\ufeff"):
        text = text[1:]
    critical = tuple(
        CriticalFinding(
            key=_critical_key(text, match.start()),
            line=text.count("\n", 0, match.start()) + 1,
            key_format=match.group(1),
        )
        for match in _PRIVATE_KEY_RE.finditer(text)
    )

    logical = _logical_lines(text)
    entries: List[ParsedEntry] = []
    warnings: List[str] = []
    unparseable = 0
    empty_values = 0
    references = 0
    placeholders = 0

    for line_number, raw_line in logical:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            unparseable += 1
            warnings.append(f"line {line_number}: missing '='")
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _KEY_RE.match(key):
            unparseable += 1
            warnings.append(f"line {line_number}: invalid key name")
            continue

        value, warning = _parse_value(raw_value)
        if warning:
            unparseable += 1
            warnings.append(f"line {line_number}: {warning}")
            continue
        if value is None:
            continue
        if value == "":
            empty_values += 1
            continue
        if _REFERENCE_RE.match(value):
            references += 1
            continue
        if _is_placeholder(value):
            placeholders += 1
            continue

        entries.append(ParsedEntry(key=key, value=value, line=line_number))

    return ParseResult(
        entries=tuple(entries),
        critical=critical,
        warnings=tuple(warnings),
        unparseable_lines=unparseable,
        empty_values=empty_values,
        references=references,
        placeholders=placeholders,
    )


__all__ = [
    "CriticalFinding",
    "ParseResult",
    "ParsedEntry",
    "classify_key",
    "parse_env_text",
]
