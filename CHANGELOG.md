# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.1] - 2026-10-21
### Fixed
- Fixed version mismatch in `__init__.py` and `version.txt`.

## [1.5.1] - 2026-10-21
### Fixed
- Fixed mypy strict typing errors in CI (added `types-requests`).
- Fixed `--no-update-check` deprecation to avoid breaking existing scripts.
- Fixed README network calls badge.

### Deprecated
- `BreachResult.count` is deprecated, use `breach_count` instead. It will be removed in v2.0.0.
- `--no-update-check` is deprecated and is now the default behavior. Use `--check-updates` instead.

## [1.5.0] - 2026-10-20
### Added
- `--json` flag for machine-readable output.
- `schema/result.schema.json` to validate the JSON output.
- Support for reading passwords from stdin (`imps -`).
- Golden scores (`tests/golden/`) to prevent engine regressions.
- Property-based testing with Hypothesis.
- Benchmark script (`scripts/bench.py`).
- `SECURITY.md` and `CONTRIBUTING.md`.

### Changed
- **Behavior change:** The remote update check (GitHub) is now **opt-in**. It is disabled by default to guarantee zero outbound requests, and can be enabled with `--check-updates`.
- Refactored the pattern engine to expose `rules_fired` in the output.
- Enforced strict linting (`ruff`) and typing (`mypy`) across the core modules.

### Fixed
- Fixed an `OverflowError` in hardware estimates for extremely long passwords (10,000+ chars).
- Fixed deterministic matching order for top-150 patterns.

## [1.4.1] - 2026-10-20
### Fixed
- `cli.main()` now accepts `argv` for testing.
- Pattern tests no longer collide with the top-150 dictionary.
- Gate PyPI publish on the test suite.

## [1.4.0] - 2026-10-20
### Added
- Initial test suite with `pytest`.
- CI workflow on Windows, macOS, and Linux.

## [1.3.0] - 2026-10-20
### Added
- Refactored the codebase into modular components (`core`, `patterns`, `network`, `ui`, `cli`).
- The engine is now importable as a Python library (`from ismypwdsafe import analyze_password`).