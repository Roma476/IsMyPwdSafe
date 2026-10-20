import json
from pathlib import Path
from typing import Any, List

import jsonschema
import pytest

GOLDEN_DIR = Path(__file__).parent / "golden"
SCORES_PATH = GOLDEN_DIR / "scores.json"
SCHEMA_PATH = Path(__file__).parent.parent / "schema" / "result.schema.json"


def load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def test_json_schema_against_golden() -> None:
    if not SCORES_PATH.exists():
        pytest.skip("Golden scores not generated. Run scripts/generate_golden.py")

    schema = load_json(SCHEMA_PATH)
    golden_data: List[dict] = load_json(SCORES_PATH)

    for case in golden_data:
        if "error" in case:
            continue
            
        pwd = case["input"]
        # Validate the expected output directly to ensure the schema is correct
        try:
            jsonschema.validate(instance=case["expected"], schema=schema)
        except jsonschema.ValidationError as e:
            pytest.fail(f"JSON schema validation failed for input '{pwd}': {e.message}")