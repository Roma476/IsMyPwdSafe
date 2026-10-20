import json
from pathlib import Path

import jsonschema
import pytest

from ismypwdsafe import analyze_password
from ismypwdsafe.render import render_json


@pytest.mark.parametrize("pwd", ["password", "correct-horse-battery-staple", ""])
def test_json_schema(pwd):
    schema_path = Path(__file__).parent.parent / "schema" / "result.schema.json"
    with open(schema_path) as f:
        schema = json.load(f)

    result = analyze_password(pwd, check_breach=False)
    data = json.loads(render_json(result))

    jsonschema.validate(instance=data, schema=schema)
    assert data["schema_version"] == "1.0"