"""IsMyPwdSafe: a privacy-first, zxcvbn-first password audit."""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .core import SCHEMA_VERSION, AuditResult, analyze_password  # noqa: E402,F401

try:
    __version__ = version("ismypwdsafe")
except PackageNotFoundError:
    try:
        __version__ = (Path(__file__).resolve().parent.parent / "version.txt").read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        __version__ = "0.0.0+unknown"

__all__ = ["analyze_password", "AuditResult", "SCHEMA_VERSION", "__version__"]
