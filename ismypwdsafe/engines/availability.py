from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
from typing import Optional, Tuple


def node_version() -> Optional[Tuple[int, ...]]:
    """Return the installed Node.js version, or None when Node is absent."""
    executable = shutil.which("node")
    if executable is None:
        return None
    try:
        proc = subprocess.run(  # noqa: S603
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"v?(\d+)(?:\.(\d+))?", proc.stdout.strip())
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2) or 0))


def ts_available() -> bool:
    version = node_version()
    return version is not None and version >= (18, 0)


def python_available() -> bool:
    return importlib.util.find_spec("zxcvbn") is not None
