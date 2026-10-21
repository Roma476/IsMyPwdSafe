"""Outbound HTTP: HaveIBeenPwned range API and GitHub version check."""
from dataclasses import dataclass
from typing import NamedTuple, Optional, Union

import hashlib
import requests
import warnings


def _hash_password(password: str) -> str:
    """SHA-1 hex digest. Computed once by callers; never transmitted in full."""
    return hashlib.sha1(password.encode('utf-8')).hexdigest()  # noqa: S324


def check_pwned(password: str) -> Union[int, str]:
    """
    k-anonymity breach check. Returns the breach count (int, 0 if clean)
    or a human-readable error string on network/API failure.
    """
    sha1 = _hash_password(password)
    prefix = sha1[:5].upper()
    suffix = sha1[5:].upper()

    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return f"API request failed with status code: {response.status_code}"
        for line in response.text.splitlines():
            server_suffix, count = line.split(':')
            if server_suffix == suffix:
                return int(count)
        return 0
    except Exception:
        return (
            "You are offline or the API is unreachable. "
            "Cannot check if the password has been pwned."
        )


def _version_tuple(v: str) -> tuple[int, ...]:
    """Converts '1.2.3' to (1, 2, 3) for comparison. Falls back to (0,) on garbage."""
    try:
        return tuple(map(int, v.strip().split(".")))
    except ValueError:
        return (0,)


def check_for_updates(current_version: str) -> Optional[str]:
    """Returns a newer version string if available, else None. Silent on any error."""
    url = "https://raw.githubusercontent.com/Roma476/IsMyPwdSafe/main/version.txt"
    try:
        response = requests.get(url, timeout=1.5)
        if response.status_code == 200:
            latest = response.text.strip()
            if _version_tuple(latest) > _version_tuple(current_version):
                return str(latest)
    except Exception:  # noqa: S110
        pass
    return None


@dataclass(frozen=True)
class BreachResult:
    checked: bool
    pwned: Optional[bool]
    breach_count: Optional[int]
    reason: Optional[str]

    @property
    def count(self) -> Optional[int]:
        warnings.warn(
            "BreachResult.count is deprecated, use breach_count instead.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.breach_count


def check_breach(password: str) -> BreachResult:
    """Structured version of check_pwned. Never raises."""
    sha1 = _hash_password(password)
    prefix = sha1[:5].upper()
    suffix = sha1[5:].upper()

    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return BreachResult(checked=True, pwned=None, breach_count=None, reason="api_error")
        for line in response.text.splitlines():
            server_suffix, count_str = line.split(':')
            if server_suffix == suffix:
                return BreachResult(
                    checked=True, 
                    pwned=True, 
                    breach_count=int(count_str), 
                    reason=None
                )
        return BreachResult(checked=True, pwned=False, breach_count=0, reason=None)
    except Exception:  # noqa: S110
        return BreachResult(checked=True, pwned=None, breach_count=None, reason="api_error")