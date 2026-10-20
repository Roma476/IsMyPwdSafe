"""IsMyPwdSafe: a privacy-first password audit engine."""
__version__ = "1.4.1"

from .core import analyze_password, AuditResult, SCHEMA_VERSION  # noqa: E402,F401

__all__ = ["analyze_password", "AuditResult", "SCHEMA_VERSION", "__version__"]