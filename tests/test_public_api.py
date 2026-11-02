import json
import pkgutil

from ismypwdsafe import (
    SCHEMA_VERSION,
    AuditResult,
    analyze_password,
    render_json,
    result_to_dict,
)


def test_public_api_exports_json_helpers() -> None:
    result = analyze_password(
        "password",
        check_breach=False,
        engine_name="native",
    )
    assert isinstance(result, AuditResult)

    payload = result_to_dict(result)
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["redacted"] is True
    assert json.loads(render_json(result)) == payload


def test_package_data_contains_py_typed() -> None:
    assert pkgutil.get_data("ismypwdsafe", "py.typed") is not None
