"""Outbound HTTP: HaveIBeenPwned range API and GitHub version check."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import requests

_HIBP_URL = "https://api.pwnedpasswords.com/range/{prefix}"


def _hash_password(password: str) -> str:
    """SHA-1 hex digest. Computed locally; only a 5-character prefix is sent."""
    return hashlib.sha1(password.encode("utf-8")).hexdigest()  # noqa: S324


def _version_tuple(value: str) -> tuple[int, ...]:
    """Convert '1.2.3' to (1, 2, 3), ignoring pre-release suffixes."""
    core = value.strip().split("-", 1)[0].split("+", 1)[0]
    try:
        return tuple(int(part) for part in core.split("."))
    except ValueError:
        return (0,)


@dataclass(frozen=True)
class BreachResult:
    checked: bool
    pwned: Optional[bool]
    breach_count: Optional[int]
    reason: Optional[str]

    @property
    def unknown(self) -> bool:
        return self.checked and self.pwned is None


def check_breach(password: str) -> BreachResult:
    """Check a password against HIBP with k-anonymity. Never raises.

    The response uses padding, so a clean password is not distinguishable from
    a padded response by its length or status code.
    """
    sha1 = _hash_password(password)
    prefix = sha1[:5].upper()
    suffix = sha1[5:].upper()

    try:
        response = requests.get(
            _HIBP_URL.format(prefix=prefix),
            headers={"Add-Padding": "true", "User-Agent": "IsMyPwdSafe"},
            timeout=5,
        )
        if response.status_code != 200:
            return BreachResult(True, None, None, "api_error")
        for line in response.text.splitlines():
            if ":" not in line:
                continue
            server_suffix, count_str = line.split(":", 1)
            if server_suffix.strip().upper() == suffix:
                try:
                    count = int(count_str.strip())
                except ValueError:
                    return BreachResult(True, None, None, "api_error")
                if count <= 0:
                    return BreachResult(True, False, 0, None)
                return BreachResult(True, True, count, None)
        return BreachResult(True, False, 0, None)
    except Exception:  # noqa: BLE001 - network failures are expected and non-fatal
        return BreachResult(True, None, None, "api_error")


def check_for_updates(current_version: str) -> Optional[str]:
    """Return a newer version string if available, else None. Silent on error."""
    url = "https://raw.githubusercontent.com/Roma476/IsMyPwdSafe/main/version.txt"
    try:
        response = requests.get(url, timeout=1.5)
        if response.status_code == 200:
            latest = response.text.strip()
            if _version_tuple(latest) > _version_tuple(current_version):
                return str(latest)
    except Exception:  # noqa: BLE001, S110
        pass
    return None
