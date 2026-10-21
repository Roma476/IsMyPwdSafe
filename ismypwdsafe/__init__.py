"""IsMyPwdSafe: a privacy-first password audit engine."""
from importlib.metadata import version, PackageNotFoundError
from .core import analyze_password, AuditResult, SCHEMA_VERSION  # noqa: E402,F401

try:
    __version__ = version("ismypwdsafe")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["analyze_password", "AuditResult", "SCHEMA_VERSION", "__version__"]