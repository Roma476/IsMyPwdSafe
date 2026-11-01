<h1 align="center">IsMyPwdSafe</h1>

<p align="center"><strong>zxcvbn, but readable.</strong></p>

<p align="center">
  A privacy-first password audit for developers and CI/CD.<br>
  zxcvbn-ts by default, HIBP enabled by default, semantic exit codes, strict JSON, and a native GitHub Action.
</p>

<p align="center">
  <a href="https://pypi.org/project/ismypwdsafe/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/ismypwdsafe?style=for-the-badge&color=63e6b4"></a>
  <a href="https://pypi.org/project/ismypwdsafe/"><img alt="Install with pipx" src="https://img.shields.io/badge/pipx_install-ismypwdsafe-729dff?style=for-the-badge&logo=pypi&logoColor=white"></a>
</p>

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Node.js 18+ for zxcvbn-ts](https://img.shields.io/badge/node-18%2B-5FA04E?style=flat-square&logo=nodedotjs&logoColor=white)](#scoring-engines)
[![License: MIT](https://img.shields.io/badge/license-MIT-63e6b4?style=flat-square)](LICENSE)
[![CI](https://github.com/Roma476/IsMyPwdSafe/actions/workflows/ci.yml/badge.svg)](https://github.com/Roma476/IsMyPwdSafe/actions/workflows/ci.yml)

> **Version 2.0.0rc1 (release candidate).** This is a major release: zxcvbn is now the source of truth for score, sequence, feedback, and crack times. The old native heuristic remains available only with `--engine=native`. The stable `2.0.0` tag is created only after the release candidate has been tested on TestPyPI and through the GitHub Action.

**Read this first:** passing the password as an argument (`imps "my-password"`) exposes it to shell history, terminal scrollback, and process listings. Run `imps` without arguments to use the hidden prompt, or pipe from stdin with `imps -`. This is an audit tool, not a password manager.

---

## A note on humility

IsMyPwdSafe is a small wrapper around other people's excellent work. The hard
parts - zxcvbn, the language dictionaries, and the HaveIBeenPwned range API -
are not ours. What we try to add is a readable report, a small privacy budget,
and predictable failure modes.

It can help you notice that a password is a dictionary word, a keyboard walk, a
date, a repeat, or a known breach. It **cannot prove that a password is safe**.
A clean result is not a certificate, an audit opinion, or a guarantee. It means
"this particular heuristic did not find a problem in this particular run".

We would rather say `UNKNOWN` and exit `5` than tell you a password is safe when
the breach check did not run. That is the main design principle behind 2.0, and
it is also why the tool is occasionally annoying in CI.

---

## The five 2.0 decisions that differ from the original plan

While building 2.0 we changed five decisions. They are listed here because they
are part of the contract, not hidden implementation details.

| # | Decision | Why | Cost |
| - | -------- | --- | ---- |
| 1 | `auto` is the default engine, not `ts` and not `native`. | A normal install should use the best available zxcvbn engine without silently changing the meaning of the result. | If neither zxcvbn-ts nor zxcvbn-python is available, the command fails with exit `4`. |
| 2 | HIBP is **on by default**, and an unreachable HIBP is `UNKNOWN` with exit `5`. | A missing breach check must not be confused with a clean breach check. | One anonymous range request per audit; `--offline` is required for a strictly local run. |
| 3 | zxcvbn's `0-4` score maps to `0 / 25 / 50 / 75 / 100`. | The percentage is easier to read than a bare `0-4`, and the weak/medium/strong boundary is explicit. | The number is a presentation choice, not extra evidence; it does not make zxcvbn more precise. |
| 4 | A pwned password is forced to score `0`, rating `weak`, with `score.capped_by = "hibp"`. | "Strong but already breached" must not look safe in a dashboard or a CI summary. | The zxcvbn details are still reported, but the final score is deliberately dominated by the breach. |
| 5 | `--json` redacts matched tokens by default; `--json-full` is the explicit opt-in. | JSON often ends up in logs, artifacts, and issue comments. The default should not leak password fragments. | Users who need the matched tokens must ask for them and handle the output carefully. |

The exact exit-code table and score mapping are documented below. If you build a
CI policy on this tool, use those tables rather than assumptions from 1.x.

---

## Quick start

### Install

```bash
pipx install ismypwdsafe
```

`pip` works too:

```bash
pip install ismypwdsafe
```

For the optional zxcvbn-python fallback:

```bash
pipx install "ismypwdsafe[python]"
```

### Run

```bash
imps                         # hidden prompt
imps --offline               # hidden prompt, no network calls
imps - < password.txt        # password from stdin
imps --json - < password.txt # machine-readable output
```

The CLI default engine is `auto`:

1. zxcvbn-ts 4.x, if Node.js 18+ is on `PATH`;
2. otherwise zxcvbn-python, if installed;
3. otherwise exit `4` with an explanation.

`native` is **never selected silently**. Use `--engine=native` only for the legacy 1.x heuristic.

```bash
imps --engine=ts "correct-horse-battery-staple"
imps --engine=python "correct-horse-battery-staple"   # needs: pip install "ismypwdsafe[python]"
imps --engine=native "correct-horse-battery-staple"   # legacy heuristic, explicit only
```

### Node.js

Node.js is not bundled or downloaded. Install it with your platform package manager:

```bash
# macOS
brew install node

# Debian / Ubuntu
sudo apt install nodejs npm

# Windows
winget install OpenJS.NodeJS.LTS
```

Verify with `node --version`. If Node is unavailable and you do not have the Python fallback installed, `imps` fails with exit `4` rather than pretending the native heuristic is zxcvbn.

---

## What it reports

The default zxcvbn path renders:

- zxcvbn score `0-4` and a readable `0-100` percentage;
- estimated time to crack under four attacker models;
- **why** the score is low: dictionary matches, keyboard walks, repeats, dates, sequences, regexes, and brute force;
- zxcvbn feedback (warning + suggestions);
- HIBP breach status.

The native engine keeps the 1.x entropy and pattern model but does not produce zxcvbn sequence, feedback, or crack-time data.

### Engine identity is part of the result

"Available" is not the same as "used". The JSON contains both values:

- `engine_requested` is what you asked for (`auto`, `ts`, `python`, or `native`);
- `engine_used` is the engine that actually produced the result;
- `engine_version` is the version reported by that engine;
- `engine_fallback` is `true` only when `auto` fell back to zxcvbn-python
  because zxcvbn-ts was unavailable.

If `auto` cannot find any zxcvbn engine, the command exits `4` and `engine_used`
is `null`. It does **not** quietly run the native heuristic. Consumers should
branch on `engine_used`, not on `engine_requested`.

### Score mapping

| zxcvbn | Percentage | Rating |
| ------ | ---------: | ------ |
| `0` | `0` | weak |
| `1` | `25` | weak |
| `2` | `50` | medium |
| `3` | `75` | strong |
| `4` | `100` | strong |

If HIBP says the password is pwned, the final score is forced to `0` and the result uses exit code `3`. The reason is exposed as `score.capped_by = "hibp"`.

---

## HaveIBeenPwned is ON by default

By default `imps` makes exactly one outbound request: HIBP's Pwned Passwords range API.

- The password and the full SHA-1 hash never leave the machine.
- Only the first five characters of the SHA-1 hash are sent.
- Responses use `Add-Padding: true`.
- The local suffix match happens in memory.
- Timeout: 5 seconds.

Skip it explicitly:

```bash
imps --no-breach-check "my-password"   # skip HIBP
imps --offline "my-password"           # skip HIBP and the optional update check
```

If HIBP cannot be reached, `imps` does **not** call the password safe:

- the report says `UNKNOWN`;
- the JSON has `breach.checked = true`, `breach.pwned = null`, `breach.reason = "api_error"`;
- the exit code is `5`.

The zxcvbn score is still shown, but CI must treat exit `5` as a failure.

The GitHub update check is opt-in and separate: `--check-updates`.

| Command | HIBP | GitHub update check |
| ------- | :--: | :-----------------: |
| `imps "pwd"` | yes | no |
| `imps --no-breach-check "pwd"` | no | no |
| `imps --check-updates "pwd"` | yes | yes |
| `imps --offline "pwd"` | no | no |

---

## CLI reference

```text
imps [--engine {auto,ts,python,native}] [-M] [-o | --no-breach-check]
     [-s | -dw] [--check-updates] [--json | --json-full | -q] [password|-]
```

| Flag | Description |
| ---- | ----------- |
| `--engine` | `auto` (default), `ts`, `python`, or `native`. |
| `-M`, `--Mask` | Mask the password and matched tokens in the terminal UI. |
| `-s`, `--short` | Show only the score and breach verdict. |
| `-dw`, `--darkweb` | Show only the breach check. |
| `-o`, `--offline` | Skip HIBP and all other network calls. |
| `--no-breach-check` | Skip only HIBP. |
| `--check-updates` | Enable the opt-in GitHub version check. |
| `--json` | Strict JSON output; matched tokens are redacted. |
| `--json-full` | JSON including matched tokens. Use with care. |
| `-q`, `--quiet` | Suppress all output; return only the exit code. |
| `password` | Password to audit. Omit for hidden prompt; use `-` for stdin. |

The password argument is optional. In a non-interactive shell with no password and no stdin, `imps` exits `2` instead of hanging.

---

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0` | OK: score >= 50, not pwned, breach status known or disabled |
| `1` | Weak: score < 50 |
| `2` | Usage/input error, including an empty password |
| `3` | Pwned: found in HIBP |
| `4` | Engine error: no usable engine, Node too old, engine failure |
| `5` | HIBP status unknown: do not treat the password as safe |
| `130` | Interrupted with Ctrl+C |

For CI, use `-q` when you only need the code, or `--json` when you need the data:

```bash
imps -q --engine=ts - < password.txt
echo $?
```

---

## JSON contract v2.0

`--json` emits a strict, versioned document validated against [`schema/result.schema.json`](schema/result.schema.json). Non-finite floats are converted to `null`; the output never contains `Infinity` or `NaN`.

By default, `sequence[].token`, `matched_word`, `base_token`, `sub_display`, `regex_match`, and `subs` are replaced with `"<redacted>"`. Use `--json-full` only when you explicitly need the matched tokens.

The default JSON has no top-level `password` field, and the password is not
included in `input`, `breach`, `feedback`, or the redacted `sequence`. The test
suite checks this with a unique marker password against the selected engine; see
[`tests/test_privacy.py`](tests/test_privacy.py). `--json-full` may reveal
password fragments through `sequence[].token`, so treat it as sensitive output.

Example (abridged):

```json
{
  "schema_version": "2.0",
  "tool_version": "2.0.0rc1",
  "exit_code": 0,
  "error": null,
  "input": {
    "length": 28,
    "charset_size": 59,
    "has_lower": true,
    "has_upper": false,
    "has_number": false,
    "has_symbol": true,
    "has_non_ascii": false
  },
  "score": {
    "value": 100,
    "rating": "strong",
    "raw_score_0_4": 4,
    "capped_by": null
  },
  "guesses": 100000000001.0,
  "guesses_log10": 11.0,
  "crack_times_seconds": {
    "online_throttling_100_per_hour": 3600000000036.0,
    "online_no_throttling_10_per_second": 10000000000.1,
    "offline_slow_hashing_1e4_per_second": 10000000.0001,
    "offline_fast_hashing_1e10_per_second": 10.0000000001
  },
  "crack_times_display": {
    "online_throttling_100_per_hour": "centuries",
    "online_no_throttling_10_per_second": "centuries",
    "offline_slow_hashing_1e4_per_second": "4 months",
    "offline_fast_hashing_1e10_per_second": "10 seconds"
  },
  "feedback": {
    "warning": null,
    "suggestions": []
  },
  "sequence": [
    {
      "pattern": "bruteforce",
      "token": "<redacted>",
      "i": 0,
      "j": 27,
      "guesses": 100000000000
    }
  ],
  "breach": {
    "checked": true,
    "pwned": false,
    "breach_count": 0,
    "reason": null
  },
  "engine_requested": "auto",
  "engine_used": "ts",
  "engine_version": "4.2.0",
  "engine_fallback": false,
  "calc_time": 12.0,
  "redacted": true
}
```

The library returns the same data:

```python
from ismypwdsafe import analyze_password

result = analyze_password(
    "correct-horse-battery-staple",
    check_breach=False,
    engine_name="ts",  # or "auto", "python", "native"
)
print(result.score.value)
print(result.score.rating)
print(result.engine_used)
print(result.breach.checked)
```

`check_breach=True` is the default. `engine_name="auto"` follows the same no-silent-native rule as the CLI.

---

## GitHub Action

```yaml
name: Password audit
on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Audit password
        id: audit
        uses: Roma476/IsMyPwdSafe@v2
        with:
          password: ${{ secrets.PASSWORD_TO_AUDIT }}
          engine: auto          # auto | ts | python | native
          node-version: "20"
          min-score: 70
          offline: false        # true skips HIBP

      - name: Print result
        run: echo "Score ${{ steps.audit.outputs.score }} (${{ steps.audit.outputs.rating }})"
```

The Action passes the password through stdin, not as a process argument. It fails closed on weak, pwned, engine-error, and HIBP-unknown results.

| Input | Default | Description |
| ----- | ------- | ----------- |
| `password` | required | Always pass through GitHub Secrets. |
| `engine` | `auto` | `auto`, `ts`, `python`, or `native`. |
| `node-version` | `20` | Node version for `auto`/`ts`. |
| `min-score` | `70` | Fail below this score. |
| `offline` | `false` | Skip HIBP and all network calls. |

| Output | Description |
| ------ | ----------- |
| `score` | `0-100` score. |
| `rating` | `weak`, `medium`, or `strong`. |
| `exit-code` | The `imps` exit code. |

---

## Privacy

- No telemetry, analytics, crash reporting, accounts, or local audit history.
- No logs, cache, or config written on first run.
- One request by default: HIBP k-anonymity. The GitHub update check is opt-in.
- `--offline` disables all outbound requests.
- JSON is token-redacted by default.

### What is sent to HIBP

```text
sha1    = SHA1(password)        # local only
prefix  = sha1[:5].upper()      # transmitted
suffix  = sha1[5:].upper()      # matched locally
```

Not transmitted: plaintext password, full SHA-1, password length, character composition, account, or identifier. HIBP receives the prefix and the HTTP metadata inherent to any request.

---

## What a clean result does not mean

This is the most important section in the README.

A password that scores `100`, is not found in HIBP, and has a long crack-time
estimate is **not proven safe**. It has passed one heuristic and one partial
breach corpus at one point in time. That is all.

In particular:

- **zxcvbn is a heuristic.** It is very good at recognising common patterns and
  bad at knowing your personal context. A password can be strong by its model
  and still be reused across five services.
- **A clean HIBP result is not a guarantee.** HIBP is a large corpus, not every
  breach. A password can be absent from HIBP and still be compromised or reused.
- **HIBP availability matters.** If HIBP is unreachable, the result is
  `UNKNOWN`, `breach.pwned` is `null`, and the exit code is `5`. The zxcvbn score
  is still shown, but it is not a safety verdict.
- **Crack times are scenarios, not predictions.** They assume fixed hash rates
  and do not model rainbow tables, targeted dictionaries, GPU optimisations,
  side channels, or the attacker who already knows something about you.
- **The native engine is legacy.** `--engine=native` uses the 1.x ASCII-oriented
  entropy model and a finite pattern list. It is retained for compatibility, not
  recommended for new use.
- **Node is external.** `--engine=auto`/`ts` needs Node.js 18+. Without Node and
  without zxcvbn-python, `imps` exits `4`.
- **Bundled languages are English.** The shipped zxcvbn-ts bundle includes the
  `language-common` and `language-en` dictionaries. It does not claim 20+
  bundled languages.
- **This is not a password manager, a policy engine, or a compliance tool.** It
  audits one password at a time; it does not store, generate, rotate, or
  centrally enforce credentials. It also cannot tell whether a password is
  reused, shared, written on a sticky note, or sent over an insecure channel.

If you need a guarantee, you need a password manager, a reviewed policy,
multi-factor authentication, and an incident process. This tool can be one
small input to that work, not a replacement for it.

---

## Compatibility and verification

| Area | What is covered |
| ---- | --------------- |
| Python runtime | `>=3.8` in package metadata; CI covers 3.8, 3.10, and 3.12 |
| Recommended engine | Node.js 18+ and zxcvbn-ts 4.2.0 |
| Fallback engine | zxcvbn-python 4.4+ (`pip install "ismypwdsafe[python]"`) |
| Operating systems | CI coverage on Ubuntu, macOS, and Windows |
| JSON contract | validated against `schema/result.schema.json` |
| zxcvbn-ts bundle | rebuilt and checked for reproducibility in CI on Node 18 and 20 |
| HIBP failure path | unit tests plus a simulated missing-`fetch` run; exit `5` |
| Action | smoke-tested with strong, weak, and below-threshold passwords |

"CI covers" means the workflow is configured to run those jobs; it is not a
claim that every combination has been manually exercised on every machine. The
2.0.0 release candidate is published to TestPyPI before the stable tag, and the
GitHub Action is tested against that tag before `v2.0.0` is created.

---

## Development

```bash
git clone https://github.com/Roma476/IsMyPwdSafe.git
cd IsMyPwdSafe
python -m pip install -e ".[test,dev]"
pytest
```

Node 18+ is required for the golden suite that covers the `ts` engine. Without Node, those golden tests are skipped; the `native` and `python` paths still run.

Rebuild the zxcvbn-ts bundle after changing `ismypwdsafe/js/score.mjs` or the JS dependencies:

```bash
cd ismypwdsafe/js
npm ci
npm run build
```

Regenerate golden fixtures:

```bash
python scripts/generate_golden.py --engine ts
```

Project layout:

```text
ismypwdsafe/
├── engines/          # auto resolution, ts, python, native
├── js/               # score.mjs, package.json, committed zxcvbn-ts bundle
├── core.py           # result model, HIBP overlay, exit codes
├── render.py         # strict JSON + redaction
├── cli.py            # argparse, stdin, output
├── ui.py             # terminal report
├── network.py        # HIBP + optional update check
└── metrics.py        # native/legacy metrics
```

---

## Release process

The release is intentionally boring. `version.txt` is the single source of
truth, and a tag is only created after the candidate has been exercised.

1. Set `version.txt` to the candidate version (for example `2.0.0rc1`) and update
   the changelog.
2. Run the full local checks:
   ```bash
   pytest
   ruff check .
   mypy ismypwdsafe
   python -m build
   ```
3. Push the candidate tag. The publish workflow sends tags containing `a`, `b`,
   or `rc` to TestPyPI.
4. Install from TestPyPI in a clean environment and run the GitHub Action with
   the candidate tag, for example:
   ```yaml
   uses: Roma476/IsMyPwdSafe@v2.0.0rc1
   ```
5. Let the candidate sit for a short soak period. Check the TestPyPI artifact,
   the Action result, and the CLI output before promoting it.
6. Only then create the stable tag (`v2.0.0`), publish to PyPI, and merge the
   release branch into `main`.

PyPI and TestPyPI publishing uses GitHub OIDC Trusted Publishing. The repository
must have the `pypi` and `testpypi` environments, and the corresponding trusted
publishers must be configured on PyPI/TestPyPI for this repository and the
`publish.yml` workflow. No long-lived PyPI token belongs in GitHub secrets.

---

## License

MIT. See [LICENSE](LICENSE).
