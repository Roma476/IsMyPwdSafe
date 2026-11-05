# Python API

IsMyPwdSafe is a CLI/CI tool with an importable Python API. The API returns the
same normalized result as `imps --json`; it does not render terminal output. It
is not a cross-language SDK or an HTTP service.

## Install

```bash
pip install ismypwdsafe
```

The default install includes zxcvbn-python. The `python` extra remains accepted
for compatibility. The default `auto` engine still uses zxcvbn-ts when Node.js
18+ is available; otherwise it falls back to zxcvbn-python. `native` is the
explicit legacy engine.

## Basic use

```python
from ismypwdsafe import analyze_password, render_json, result_to_dict

result = analyze_password(
    "correct-horse-battery-staple",
    check_breach=False,
    engine_name="auto",
)

if result.error:
    raise RuntimeError(result.error)

if result.score is None:
    raise RuntimeError(f"no score (exit {result.exit_code})")

print(result.score.value)
print(result.score.rating)
print(result.exit_code)
print(result.engine_used)

payload = result_to_dict(result)
print(payload["score"])
print(render_json(result))
```

`analyze_password()` returns a frozen `AuditResult` dataclass. It also exposes
`guesses`, `crack_times_seconds`, `crack_times_display`, `feedback`, `sequence`,
`engine_requested`, `engine_used`, `engine_version`, `engine_fallback`, and
`calc_time` (milliseconds; `null` for the legacy native engine).

`score`, `input`, and `breach` are `None` only for the documented error
envelopes; check `result.error` and `result.exit_code` instead of assuming
success. Invalid input and engine failures are returned as `AuditResult` error
results, not raised as exceptions.

## Public surface

These names are supported for Python callers in the 2.x line:

| Name | Purpose |
| ---- | ------- |
| `analyze_password` | Run the audit and return an `AuditResult`. |
| `AuditResult` | Normalized, typed result object. |
| `result_to_dict` | Convert to a JSON-safe dictionary. |
| `render_json` | Render the versioned JSON contract. |
| `SCHEMA_VERSION` | JSON schema version (`2.0`). |
| `__version__` | Installed package version. |

Modules such as `ismypwdsafe.engines`, `ismypwdsafe.network`, and
`ismypwdsafe.ui` are implementation details unless documented otherwise.
`imps scan` is a CLI feature; its versioned output is documented in
[`scan-spec.md`](scan-spec.md) and [`schema/scan.schema.json`](../schema/scan.schema.json).

The package ships `py.typed`, so type checkers can use the annotations.

## Network behavior

`check_breach=True` is the default and performs the same HIBP k-anonymity
request as the CLI:

```python
result = analyze_password(password)
```

Use `check_breach=False` when the caller must not make network requests:

```python
result = analyze_password(
    password,
    check_breach=False,
    breach_skip_reason="disabled",
    engine_name="python",
)
```

The raw password is never sent to HIBP; only the five-character SHA-1 prefix is
sent. See the main README for the exact privacy model.

## Engines

| `engine_name` | Requirement | Notes |
| ------------- | ----------- | ----- |
| `auto` | Node 18+ or zxcvbn-python | Prefers zxcvbn-ts; never selects `native` silently. |
| `ts` | Node.js 18+ | Uses the bundled zxcvbn-ts artifact. |
| `python` | `ismypwdsafe[python]` | Pure-Python zxcvbn fallback. |
| `native` | none | Legacy 1.x heuristic; no zxcvbn sequence or crack-time data. |

If no usable engine is available, `analyze_password()` returns an error result
with exit code `4` rather than raising or pretending to score the password.

## JSON for other languages

For non-Python callers, use the CLI contract:

```bash
imps --json "my-password"
```

The JSON schema is versioned independently from the package. See
[`schema/result.schema.json`](../schema/result.schema.json) and the main README
for the error envelopes and redaction rules.

`render_json()` redacts matched tokens by default. Pass `include_tokens=True`
only when the caller explicitly needs them; this can expose the password or
fragments of it.
