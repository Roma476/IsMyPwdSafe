"""Outbound HTTP: HaveIBeenPwned range API and GitHub version check."""
import hashlib
from typing import Optional, Union

import requests


def _hash_password(password: str) -> str:
    """SHA-1 hex digest. Computed once by callers; never transmitted in full."""
    return hashlib.sha1(password.encode('utf-8')).hexdigest()


def check_pwned(password: str) -> Union[int, str]:
    """
    k-anonymity breach check. Returns the breach count (int, 0 if clean)
    or a human-readable error string on network/API failure.
    """
    sha1 = _hash_password(password)
    prefix = sha1[:5].upper()
    suffix = sha1[5:].upper()

    url = "https://api.pwnedpasswords.com/range/{}".format(prefix)
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return "API request failed with status code: {}".format(response.status_code)
        for line in response.text.splitlines():
            server_suffix, count = line.split(':')
            if server_suffix == suffix:
                return int(count)
        return 0
    except Exception:
        return "You are offline or the API is unreachable. Cannot check if the password has been pwned."


def _version_tuple(v: str):
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
                return latest
    except Exception:
        pass
    return None