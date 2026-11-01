$ErrorActionPreference = "Stop"

Write-Host "1. Running tests..." -ForegroundColor Cyan
python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "2. Running linter..." -ForegroundColor Cyan
python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "3. Running type checker..." -ForegroundColor Cyan
python -m mypy ismypwdsafe/
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "4. Checking version..." -ForegroundColor Cyan
python -c "from ismypwdsafe import __version__; print('Current version:', __version__)"

Write-Host "5. Checking JSON schema contract..." -ForegroundColor Cyan
$jsonOutput = imps --offline --json "test"
$jsonOutput | python -c "import sys, json; assert json.load(sys.stdin)['schema_version'] == '2.0'; print('JSON schema OK')"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "6. Checking Node.js and JS bundle..." -ForegroundColor Cyan
node --version
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -c "from importlib.resources import files; assert files('ismypwdsafe').joinpath('js/zxcvbn-ts.bundle.js').is_file(); print('JS bundle OK')"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "All checks passed! Ready to tag." -ForegroundColor Green