"""IsMyPwdSafe: a privacy-first password audit engine."""
from importlib.metadata import PackageNotFoundError, version

from .core import SCHEMA_VERSION, AuditResult, analyze_password  # noqa: E402,F401

try:
    __version__ = version("ismypwdsafe")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["analyze_password", "AuditResult", "SCHEMA_VERSION", "__version__"]