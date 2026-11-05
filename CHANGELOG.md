# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.1] - 2026-11-05

### Fixed

- Shortened the GitHub Action description to satisfy GitHub Marketplace's
  125-character metadata limit. The CLI, scan behavior, JSON contract, privacy,
  and network behavior are unchanged.

## [2.1.0] - 2026-11-05

### Added

- `imps scan`: audit `.env`/dotenv-style files without printing, logging, or
  storing secret values. The scan reports paths, line numbers, key names,
  scores, pattern labels, token formats, and HIBP status only.
- Git-aware discovery: by default only tracked `.env`, `.env.*`, `*.env`, and
  `*.env.*` files are scanned. Explicit paths always work; `--include-untracked`
  opts into untracked and ignored local files; `--no-git` supports non-git
  directories.
- Separate scan JSON contract (`schema_version: "1.0"`, `kind: "scan"`) in
  [`schema/scan.schema.json`](schema/scan.schema.json) and the full scan
  specification in [`docs/scan-spec.md`](docs/scan-spec.md).
- Scan exit codes: `6` for a private key, `4` for an unusable scoring engine,
  `3` for a pwned password, `5` for incomplete/unknown HIBP, `1` below the
  score threshold, and `2` for usage errors.
- HIBP for password-like findings with unique-value deduplication, four
  concurrent requests, a five-second per-request timeout, and a 60-second global
  deadline. A timeout keeps completed findings and reports `incomplete`.
- `TOKEN` findings are labeled honestly: no numeric score and no HIBP lookup.
  Private-key blocks are `CRITICAL`, exit `6`, and are never sent to HIBP.
- The composite GitHub Action now supports `mode: scan` with `file:line`
  annotations, an annotation limit, and a values-free JSON artifact. The
  existing `mode: audit` behavior remains the default.
- A custom line-oriented dotenv parser preserves line numbers, handles quotes,
  comments, `export`, continuations, CRLF/BOM, references, and placeholders
  without interpolation.

### Changed

- The default package install now includes `zxcvbn-python`, so
  `pipx install ismypwdsafe` has a usable scoring engine without Node.js.
  `--engine=ts` and the `auto`-to-ts branch still require Node 18+.
- Added PyPI classifiers, keywords, and project URLs for discoverability.

### Deferred to 2.1.2

- Pre-commit integration using only staged files and offline mode by default.
- A key-plus-fingerprint allowlist for non-sensitive fixtures. It will never
  store or match raw values.

## [2.0.1] - 2026-11-01

### Changed

- Documentation, contract, and terminal-report patch, plus a zxcvbn-ts
  reporting fix. Final scores, exit codes, privacy, and network behavior are
  unchanged.
- The terminal report now uses the full terminal width, centers section titles,
  and places time-to-crack and pattern matches side by side on wide terminals.
  Empty zxcvbn sections are omitted for the native engine.
- The original gradual reveal is back, with a more deliberate rhythm: banner
  and report lines fade through a multi-step luminance ramp, section titles
  resolve visibly from scrambled characters, sections are spaced with short
  beats, and the summary score bar fills with eased motion and a moving
  highlight. Animation stays disabled for non-TTY output and when `NO_COLOR`
  is set.
- Breach details are shown once, in `BREACH CHECK`, instead of being repeated
  in the score, pattern matches, and feedback sections.
- The score line shows one rating (`STRONG 100/100`) instead of repeating the
  same result as both a percentage and a zxcvbn `0-4` score. The pattern
  section is labelled `PATTERN MATCHES` instead of the ambiguous `WHY`.
- The `ts` engine now keeps zxcvbn's own sequence, guesses, feedback, and
  crack-time estimates when HIBP is enabled. The breach check still caps the
  final score at `0` and exits with code `3`, but it no longer replaces the
  pattern breakdown with a synthetic `pwned` match. This matches the `python`
  engine and makes `PATTERN MATCHES` useful for pwned weak passwords.
- The terminal help for `-s/--short` now says it shows the score, breach
  verdict, and engine line.
- The Python API is now documented and exported consistently: `render_json` and
  `result_to_dict` are available from the package root, and the package ships
  `py.typed`.
- zxcvbn-python's `calc_time` (a `timedelta`) is now converted to milliseconds
  instead of being dropped as `null`; `calc_time` remains milliseconds in the
  JSON contract, and the legacy native engine still reports `null`.

### Documentation

- Documented `calc_time` as **milliseconds**. The field name is unchanged in
  the 2.0 schema; `calc_time_ms` is deferred to a future minor release.
- Added the complete JSON error envelope for exit codes `2`, `4`, `5`, and
  `130`, including which fields are `null`.
- Documented the `--engine=native` JSON shape: `engine_version: null`,
  `raw_score_0_4: null`, empty `sequence`, empty feedback values, and
  `calc_time: null`.
- Added the `engine_version` table for `ts`, `python`, and `native`.
- Clarified `-s`, `-M`, `-dw`, and `-q` behavior. In particular, `-q` does not
  change input handling, and `-M` affects only the terminal UI.
- Clarified that Node.js 18+ is required only for `--engine=ts`, not for the
  default `auto` path when zxcvbn-python is installed.
- Reordered the README to be demo-first, demoted the legacy native engine, and
  added a terminal demo GIF.

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
- GitHub Action that passes the password through stdin and fails on weak, pwned, engine-error, and HIBP-unknown results.
- `Add-Padding: true` on HIBP requests.
- Shared `engines/` package with `auto`, `ts`, `python`, and `native` backends.

### Changed
- **BREAKING**: the default engine is `auto`, not an unconditional native fallback. It selects zxcvbn-ts when Node 18+ is available, then zxcvbn-python, and otherwise exits `4`. `native` is never selected silently.
- **BREAKING**: JSON schema is now `2.0`; 1.x fields such as `entropy`, `pattern`, `hardware`, and `base` were removed from the default contract. zxcvbn is the source of truth for score, sequence, feedback, and crack times.
- **BREAKING**: zxcvbn scores map to `{0: 0, 1: 25, 2: 50, 3: 75, 4: 100}`. A pwned password is forced to `0` and exit `3`.
- HIBP is no longer opt-in. The default audit makes one anonymous HIBP range request.
- HIBP failures are reported as `UNKNOWN` (exit `5`) instead of silently computing a score without breach data.
- The terminal UI is now zxcvbn-first: score, why/sequence, feedback, crack times, and breach status.
- `-s/--short` now includes the breach verdict and engine line; 1.x showed only the score.
- `-M/--Mask` now masks matched zxcvbn tokens in the terminal UI, not only the password.
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