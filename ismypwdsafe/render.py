"""JSON rendering for the machine contract."""
import json
from dataclasses import asdict
from typing import Any

from .core import AuditResult


def _to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_dict(v) for k, v in asdict(obj).items()}
    if hasattr(obj, "_asdict"):  # NamedTuple
        return {k: _to_dict(v) for k, v in obj._asdict().items()}
    if isinstance(obj, list):
        return [_to_dict(v) for v in obj]
    return obj


def render_json(result: AuditResult) -> str:
    """Serialize an AuditResult to a JSON string with schema versioning."""
    data = _to_dict(result)
    data["schema_version"] = "1.0"
    return json.dumps(data, indent=2)