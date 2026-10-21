#!/usr/bin/env bash
set -euo pipefail

echo "1. Running tests..."
python -m pytest -q

echo "2. Running linter..."
python -m ruff check .

echo "3. Running type checker..."
python -m mypy ismypwdsafe/

echo "4. Checking version..."
python -c "from ismypwdsafe import __version__; print('Current version:', __version__)"

echo "5. Checking JSON schema contract..."
imps --json "test" | python -c "import sys,json; assert json.load(sys.stdin)['schema_version']=='1.0'; print('JSON schema OK')"

echo "✅ All checks passed! Ready to tag."
