"""IsMyPwdSafe: a privacy-first password audit engine."""
__version__ = "1.5.0r"

from .core import SCHEMA_VERSION, AuditResult, analyze_password  # noqa: E402,F401

__all__ = ["analyze_password", "AuditResult", "SCHEMA_VERSION", "__version__"]