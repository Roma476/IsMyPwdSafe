$ErrorActionPreference = "Stop"

Write-Host "1. Running tests..." -ForegroundColor Cyan
python -m pytest -q

Write-Host "2. Running linter..." -ForegroundColor Cyan
python -m ruff check .

Write-Host "3. Running type checker..." -ForegroundColor Cyan
python -m mypy ismypwdsafe/

Write-Host "4. Checking version..." -ForegroundColor Cyan
python -c "from ismypwdsafe import __version__; print('Current version:', __version__)"

Write-Host "5. Checking JSON schema contract..." -ForegroundColor Cyan
$jsonOutput = imps --json "test"
$jsonOutput | python -c "import sys, json; assert json.load(sys.stdin)['schema_version'] == '1.0'; print('JSON schema OK')"

Write-Host "All checks passed! Ready to tag." -ForegroundColor Green