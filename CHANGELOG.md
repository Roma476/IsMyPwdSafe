# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0rc1] - 2026-11-01

### Release candidate

- TestPyPI-only prerelease for verifying the 2.0 contract and the published
  GitHub Action at `@v2.0.0rc1`.
- Contains the same engine, HIBP, exit-code, score-mapping, and JSON-redaction
  behavior described under `2.0.0` below.
- Stable `2.0.0` is published only after this candidate has passed the full
  test matrix, a clean TestPyPI install, and the remote Action smoke tests.

## [2.0.0] - 2026-11-01

### Five decisions that differ from the original 2.0 plan

These are deliberate contract changes, not undocumented implementation details:

1. **`auto` is the default engine.** Resolution is zxcvbn-ts (Node 18+), then
   zxcvbn-python, then exit `4`. `native` is never selected silently.
2. **HIBP is on by default.** An unreachable HIBP service produces `UNKNOWN`,
   `breach.pwned = null`, and exit `5`; it is never reported as clean.
3. **The score mapping is `0 / 25 / 50 / 75 / 100`.** A zxcvbn score of `0`
   maps to `0`, `1` to `25`, `2` to `50`, `3` to `75`, and `4` to `100`.
4. **A pwned password is capped at zero.** The final `score.value` is `0`,
   `score.rating` is `weak`, and `score.capped_by` is `"hibp"`.
5. **JSON redacts matched tokens by default.** `--json` exposes
   `"<redacted>"`; `--json-full` is the explicit opt-in for tokens and
   password fragments.

The public exit codes and score mapping are:

| Code | Meaning |
| ---: | ------- |
| `0` | OK: score >= 50, not pwned, breach status known or disabled |
| `1` | Weak: score < 50 |
| `2` | Usage/input error |
| `3` | Pwned in HIBP |
| `4` | Engine error or no usable zxcvbn engine |
| `5` | HIBP status unknown: fail closed |
| `130` | Interrupted with Ctrl+C |

| zxcvbn | Percentage | Rating |
| -----: | ---------: | ------ |
| `0` | `0` | weak |
| `1` | `25` | weak |
| `2` | `50` | medium |
| `3` | `75` | strong |
| `4` | `100` | strong |

### Added
- `--engine {auto,ts,python,native}`; default `auto`.
- zxcvbn-ts 4.x as the preferred engine, with the official `@zxcvbn-ts/matcher-pwned` HIBP matcher.
- zxcvbn-python fallback (`pip install "ismypwdsafe[python]"`).
- HIBP **enabled by default**, with `--offline` and `--no-breach-check` opt-outs.
- Exit code `5` for an unknown HIBP status. The CLI fails closed instead of reporting the password as safe.
- `--json-full` to explicitly include matched tokens. `--json` redacts them by default.
- Strict JSON contract v2 with `schema_version: "2.0"`, full zxcvbn sequence, feedback, crack times, engine metadata, and breach status.
- Native GitHub Action that passes the password through stdin and fails on weak, pwned, engine-error, and HIBP-unknown results.
- `Add-Padding: true` on HIBP requests.
- Shared `engines/` package with `auto`, `ts`, `python`, and `native` backends.

### Changed
- **BREAKING**: the default engine is `auto`, not an unconditional native fallback. It selects zxcvbn-ts when Node 18+ is available, then zxcvbn-python, and otherwise exits `4`. `native` is never selected silently.
- **BREAKING**: JSON schema is now `2.0`; 1.x fields such as `entropy`, `pattern`, `hardware`, and `base` were removed from the default contract. zxcvbn is the source of truth for score, sequence, feedback, and crack times.
- **BREAKING**: zxcvbn scores map to `{0: 0, 1: 25, 2: 50, 3: 75, 4: 100}`. A pwned password is forced to `0` and exit `3`.
- HIBP is no longer opt-in. The default audit makes one anonymous HIBP range request.
- HIBP failures are reported as `UNKNOWN` (exit `5`) instead of silently computing a score without breach data.
- The terminal UI is now zxcvbn-first: score, why/sequence, feedback, crack times, and breach status.
- The GitHub Action input default is `engine: auto`; it sets up Node only for `auto`/`ts`.

### Deprecated
- `--no-update-check` remains accepted for compatibility but is hidden; the update check is already opt-in.
- `compute_exit_code()` remains as a compatibility shim; read `AuditResult.exit_code` instead.

### Removed
- `BreachResult.count` (deprecated in 1.5.1); use `breach_count`.
- `network.check_pwned()`; use the structured `network.check_breach()`.
- The old default native panels (`SEARCH SPACE`, `HARDWARE`) from the zxcvbn path. The legacy native engine itself remains available with `--engine=native`.

## [1.5.4] - 2026-10-21
### Fixed
- Fixed `UP007` Ruff linting error in `network.py`.
- Added `__future__ import annotations` to ensure Python 3.8 compatibility.
- Bumped version to 1.5.4 due to PyPI immutability on 1.5.3.

## [1.5.3] - 2026-10-21

### Fixed
- Fixed Ruff linting errors that blocked the CI pipeline.

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