<h1 align="center"> IsMyPwdSafe - The only password audit that doesn't spy on you.</h1>

<p align="center">
  <a href="https://github.com/Roma476/IsMyPwdSafe">
    <img alt="IsMyPwdSafe full audit output" title="IsMyPwdSafe" src="docs/screenshots/hero.png">
  </a>
  <p align="center">A privacy-first command-line password auditor.<br>Entropy math, pattern detection and breach lookup - all from your terminal.</p>
  <p align="center">
    <a href="https://pypi.org/project/ismypwdsafe/"><img height="40" alt="Install from PyPI" src="https://img.shields.io/badge/pipx_install-ismypwdsafe-729dff?style=for-the-badge&logo=pypi&logoColor=white"></a>
    &nbsp;&nbsp;&nbsp;
    <a href="https://pypi.org/project/ismypwdsafe/"><img height="40" alt="PyPI version" src="https://img.shields.io/pypi/v/ismypwdsafe?style=for-the-badge&color=63e6b4"></a>
  </p>
</p>

[![PyPI](https://img.shields.io/pypi/v/ismypwdsafe?style=flat-square&color=blue)](https://pypi.org/project/ismypwdsafe/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-63e6b4?style=flat-square)](LICENSE)
[![Platforms](https://img.shields.io/badge/platforms-Windows_%7C_macOS_%7C_Linux-729dff?style=flat-square)](#installation)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](https://github.com/Roma476/IsMyPwdSafe/issues)
[![Runtime deps](https://img.shields.io/badge/deps-1_(requests)-63e6b4?style=flat-square)](pyproject.toml)
[![Network calls](https://img.shields.io/badge/network_calls-1_(0_with_--offline)-729dff?style=flat-square)](#privacy-and-network-behavior)
[![CI](https://github.com/Roma476/IsMyPwdSafe/actions/workflows/ci.yml/badge.svg)](https://github.com/Roma476/IsMyPwdSafe/actions/workflows/ci.yml)

**Read this before you run it:** Passing the password as an argument (`imps "your-password"`) will put it in your shell history, terminal scrollback, and any logs. **To avoid this, simply run `imps` without arguments.** The tool will securely prompt you for the password using a hidden input (like `sudo`), keeping it entirely out of your history. This tool is an audit utility - **it is not a password manager.** Do not use it as one.

> **Project status - v1.5.3, actively developed.** This release is the last 1.x before the engine rewrite. It adds a machine-readable contract (--json + schema), offline-first privacy (update check is now opt-in), golden scores for regression testing, and a strict CI pipeline.

---

## Quick Start

### 1. Install

The only runtime dependency is `requests`. `pipx` gives you a global `imps` command in an isolated venv:

```bash
pipx install ismypwdsafe
```

`pip` works too if you prefer a shared environment:

```bash
pip install ismypwdsafe
```

From source, or without installing at all:

```bash
git clone https://github.com/Roma476/IsMyPwdSafe.git
cd IsMyPwdSafe
pip install .
# or
python -m ismypwdsafe.main "correct-horse-battery-staple"
```

### 2. Run an audit

```bash
$ imps 
Enter password to audit: 
# (The terminal automatically hides your keystrokes as you type)
```

If you prefer to pass the password as an inline argument (e.g., for scripts or non-interactive environments):

```bash
imps "correct-horse-battery-staple"
```

<img alt="IsMyPwdSafe full audit output" title="IsMyPwdSafe" src="docs/screenshots/good.png">

The engine computes the charset, the number of possible combinations, the estimated time to crack on four hardware profiles and the HaveIBeenPwned result. All in one pass, all locally apart from the single HIBP HTTP request (the GitHub update check is opt-in).

### 3. Run an audit on a known-weak password

```bash
imps "password"
```

Two independent things fire here. The pattern engine matches `password` against the top-150 dictionary and caps the score at 30. The HaveIBeenPwned lookup finds the password in breach data and caps at 10. The final result is a `WEAK 10/100` with two separate warnings in the DARKWEB SCANNER panel and the SEARCH SPACE panel:

<img alt="IsMyPwdSafe pattern and search space warning" title="IsMyPwdSafe" src="docs/screenshots/password.png">

<img alt="IsMyPwdSafe darkweb scanner warning" title="IsMyPwdSafe" src="docs/screenshots/password-dw.png">

### 4. Mask the password in the output

If you are auditing on a shared screen or a recording:

```bash
imps -M "MySecretPassword!"
```

<img alt="IsMyPwdSafe masked output" title="IsMyPwdSafe" src="docs/screenshots/masked.png">

The password appears as `************` in the INPUT METRICS panel. Everything else is computed normally.

### 5. Pick a view mode

If you only care about the final verdict, or only about the breach check, skip the rest of the report:

```bash
imps -s "correct-horse-battery-staple"     # only the OVERALL SECURITY ASSESSMENT
imps -dw "password"                        # only the DARKWEB SCANNER
```
The view modes are mutually exclusive: -s and -dw together are rejected by the parser. Both views are scriptable: they do not clear the terminal, do not animate, and do not trigger the update check.

### 6. Audit without touching the network

If you do not want the 5-character SHA-1 prefix of your password to leave the machine - even though it is only a k-anonymity prefix - you have a few options to control the network:

```bash
imps --no-breach-check "password"    # HIBP skipped
imps -o "password"                   # all network requests skipped
imps --check-updates "password"      # enable the opt-in GitHub update check
```

In every skip case the DARKWEB panel reports why it has no result, and the score is computed without the breach cap, exactly like the API-failure path.

### 7. Use it as a library

The analysis pipeline is importable. `analyze_password` returns a structured `AuditResult` and performs no I/O unless you ask it to:

```python
from ismypwdsafe import analyze_password

result = analyze_password("correct-horse-battery-staple", check_breach=False)

print(result.score.value) # 100
print(result.score.rating) # "strong"
print(result.pattern.detected) # False
print(result.breach.checked) # False
```

`check_breach=True` (the default) performs the HIBP request; `check_breach=False` keeps the call fully offline. The result object is the same one the CLI renders, so anything the terminal shows is available as a field.

### 8. Machine-readable output

For scripts and CI pipelines, use `--json` to get a versioned, structured output. The schema is available in `schema/result.schema.json`.

```bash
imps --json "correct-horse-battery-staple"
```

You can also pipe the password from stdin using imps -:
```bash
echo "my-password" | imps --json -
```

<p align="right">(<a href="#top">back to top</a>)</p>

---

## CLI reference

```text
imps [-M] [-o | --no-breach-check] [-s | -dw] [--check-updates] [--json] <password>
```

| Flag | Argument | Description |
| ---- | -------- | ----------- |
| `-M`, `--Mask` | - | Replace the password with asterisks in the INPUT METRICS panel. Useful on shared screens and recordings. |
| `-s`, `--short` | - | Render only the OVERALL SECURITY ASSESSMENT. No banner, no boxes, no update check. Scriptable. |
| `-dw`, `--darkweb` | - | Render only the DARKWEB SCANNER panel. Scriptable. Mutually exclusive with `-s`. |
| `-o`, `--offline` | - | Skip **all** outbound requests. Implies `--no-breach-check`. |
| `--no-breach-check` | - | Skip only the HIBP lookup. |
| `--check-updates` | - | Enable the opt-in GitHub update check (disabled by default). |
| `--json` | - | Output the result as a machine-readable JSON document. Implies non-interactive. |
| *password* | optional | The raw text password to audit. If omitted, `imps` prompts with a hidden input. |

### Network behaviour matrix

| Command | HIBP | GitHub |
| ------- | :--: | :----: |
| `imps "pwd"` | ✓ | ✗ |
| `imps --no-breach-check "pwd"` | ✗ | ✗ |
| `imps --check-updates "pwd"` | ✓ | ✓ |
| `imps -o "pwd"` | ✗ | ✗ |

`--offline` is the shortcut for the air-gapped case; the two `--no-*-check` flags are the granular controls. In all skip cases the audit still runs, the pattern engine still runs, and the score is computed without the breach cap.

The CLI is a thin layer over the `ismypwdsafe` package. Every flag maps to a field of `AuditResult`; nothing is computed twice.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## What IsMyPwdSafe can do

| Feature | Description |
| ------- | ----------- |
| [Entropy estimation](#charset-and-entropy) | Charset detection and `C^L` combination count with log10 fallback for large search spaces |
| [Top-150 dictionary](#rule-1-top-150-dictionary) | Substring match against the 150 most-used passwords, with leet-speak normalization |
| [QWERTY walk detection](#rule-2-qwerty-spatial-walk) | Real keyboard coordinate model catching `qwerty`, `1qaz2wsx`, `zxcvbn` and similar walks |
| [Common year detection](#rule-3-common-year) | Flags 4-digit runs in the 1900-2050 range |
| [Character repetition](#rule-4-character-repetition) | Flags three or more identical consecutive characters |
| [HaveIBeenPwned range lookup](#privacy-and-network-behavior) | k-anonymity breach check; only a 5-character SHA-1 prefix leaves the machine |
| [Hardware resistance graph](#scoring) | Estimated time-to-crack on PC, server, GPU rig and cluster |
| [Privacy mask mode](#4-mask-the-password-in-the-output) | `-M` / `--Mask` replaces the password with asterisks in all output |
| [Short view](#5-pick-a-view-mode) | `-s` / `--short` renders only the overall assessment. Scriptable. |
| [Darkweb view](#5-pick-a-view-mode) | `-dw` / `--darkweb` renders only the breach check. Scriptable. |
| [Offline mode](#6-audit-without-touching-the-network) | `-o` / `--offline` skips both network requests in a single switch |
| [Granular network control](#6-audit-without-touching-the-network) | `--no-breach-check` disables HIBP. `--check-updates` enables the GitHub check. |
| [Secure interactive prompt](#2-run-an-audit) | Run `imps` without arguments to enter the password via a hidden prompt, preventing shell history leaks |
| [Importable engine](#7-use-it-as-a-library) | `from ismypwdsafe import analyze_password` returns a structured `AuditResult` with no CLI overhead |
| [Modular architecture](#project-layout) | Core, patterns, network, UI and CLI live in separate modules; the engine has no terminal dependencies |

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Use Cases

- **Personal audit** - check your own passwords without pasting them into an unknown web form. Useful before migrating to a password manager.
- **Security training** - show colleagues the actual difference between `Summer2024!` and `correct-horse-battery-staple` in entropy numbers and time-to-crack instead of vague "strong/weak" labels.
- **Assessing leaked credentials** - when a plaintext password turns up in a dump or during a CTF, check how strong it actually is before deciding whether to report it as critical.
- **Pre-deployment checks** - quick scan of default passwords or example strings before they ship in a config file.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Detection engine

The score is not a linear function of length. It combines a mathematical entropy estimate with a set of pattern rules that catch the cases where entropy is misleading - `Password123` has non-trivial entropy on paper but is trivially guessable because the pattern is known.

### Charset and entropy

Each character contributes to the charset once:

| Class | Contribution |
| ----- | ------------ |
| Digits `0-9` | +10 |
| Lowercase `a-z` | +26 |
| Uppercase `A-Z` | +26 |
| Printable ASCII symbols | +33 |

Non-ASCII characters do not contribute to the estimate - the search space is modelled over printable ASCII only. Total combinations are `C^L` and entropy in base 10 is `L * log10(C)`.

For large search spaces the raw `C^L` overflows the display width, so the engine switches to log-space representation (`10^x`). The switch is decided by `must_use_log(C, L)`:

| Condition | Behaviour |
| --------- | --------- |
| `C > 95` and `L >= 3` | log-space |
| `C ∈ {62, 63}` and `L >= 5` | log-space |
| Otherwise | `L >= 4` → log-space |

That is why some outputs show `10^39.65` instead of a full integer - it is precise and it fits the panel.

### Rule 1: Top-150 dictionary

Substring match against the top-150 most-used passwords. Before matching, the input is lowercased and normalized through a leet-speak translation table:

```
@ → a    4 → a    3 → e    0 → o    1 → i
! → i    $ → s    5 → s    7 → t    8 → b
```

So `P@ssw0rd` becomes `password` and is caught. `MyPassword123` also matches because `password123` is a substring of the normalized input. This is the most aggressive rule - it is why so many "clever" passwords still score low.

### Rule 2: QWERTY spatial walk

Each key is mapped to a `(row, column)` coordinate on a real QWERTY keyboard:

```
row 0:  1 2 3 4 5 6 7 8 9 0
row 1:  q w e r t y u i o p
row 2:  a s d f g h j k l
row 3:  z x c v b n m
```

The engine looks for at least 4 consecutive keys moving in the same direction - horizontal, vertical or diagonal. When it finds a run, the password gets flagged. This catches the entire family of keyboard walks that look random to a human but are not:

```bash
imps "qwertyuiop"    # horizontal walk
imps "1qaz2wsx"      # diagonal walk
imps "mnbvcxz"       # horizontal reverse walk
imps "1qaz"          # vertical walk
```

### Rule 3: Common year

Scans for a 4-digit run in the `1900-2050` range. `MyPassword2024` and `Summer1990!` both trip this rule even if the surrounding text is clean. This is not a hard match against a list of years - it catches any 4-digit number in the plausible-year range, which is the pattern most people add to a base word when a site forces a "number" requirement.

### Rule 4: Character repetition

Any three or more identical consecutive characters. Catches `aaa`, `111`, `...` and the family of `password!!!` variants. Padding is not entropy.

### Scoring

```
base_score = min(100, max(0, log10_value * 5))

if pattern_detected:    base_score = min(base_score, 30)
if pwned_count > 0:     base_score = min(base_score, 10)
```

| Score | Rating |
| ----- | ------ |
| 0-9 | WEAK (pwned) |
| 10-29 | WEAK (pattern) |
| 30-49 | WEAK |
| 50-69 | MEDIUM |
| 70-100 | STRONG |

The score is capped, not weighted. A single pattern match is treated as a binary event because in practice, once one obvious pattern exists, the rest of the string is no longer the bottleneck - the attacker is running a dictionary or a walk generator, not a brute-force sweep.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Privacy and network behavior

By default, the tool makes **one outbound HTTP request** (HaveIBeenPwned). A second request (GitHub) is made only if you explicitly pass `--check-updates`.

### 1. HaveIBeenPwned Range API

The plaintext password and the full SHA-1 hash never leave the machine. Only a 5-character prefix is transmitted, following the [k-anonymity model recommended by HIBP](https://haveibeenpwned.com/API/v3#PwnedPasswords) and used by Firefox, 1Password and Bitwarden:

```
sha1    = SHA1(password)
prefix  = sha1[:5].upper()
suffix  = sha1[5:].upper()

GET https://api.pwnedpasswords.com/range/{prefix}
  → server returns ~800 candidate suffixes
  → local match of `suffix` against the response
```

- **Transmitted:** the 5-character SHA-1 prefix.
- **Not transmitted:** plaintext password, full hash, length, character composition, any IP-linked identifier.
- **Timeout:** 5 seconds.
- **On failure:** the DARKWEB panel shows a warning and the score is computed without the breach cap. The rest of the audit runs normally.
- **Disable with:** `--no-breach-check` (or `-o/--offline`).

### 2. GitHub version check

A single `GET` to `raw.githubusercontent.com/Roma476/IsMyPwdSafe/main/version.txt` at startup. No identifier, no analytics, no telemetry. It exists solely to warn if a newer version is available. 1.5-second timeout, silent failure. Enable with `--check-updates`.

### Granular network control

The two requests are controlled independently, with `--offline` as the shortcut:

```bash
imps --no-breach-check "your-password"    # HIBP skipped
imps --check-updates "your-password"      # Enable GitHub version check
imps -o "your-password"                   # both skipped, fully air-gapped
```

| Command | HIBP | GitHub |
| ------- | :--: | :----: |
| `imps "pwd"` | ✓ | ✗ |
| `imps --no-breach-check "pwd"` | ✗ | ✗ |
| `imps --check-updates "pwd"` | ✓ | ✓ |
| `imps -o "pwd"` | ✗ | ✗ |

In every skip case:

- The audit still runs. The pattern engine still runs. The hardware resistance graph still runs.
- The DARKWEB panel reports **why** it has no result (`OFFLINE MODE` vs `BREACH CHECK DISABLED (--no-breach-check)` vs a real network error).
- The overall score is computed **without** the breach cap, exactly like the API-failure path.

### What the tool does not do

- No telemetry, no analytics, no crash reporting
- No account, no email, no local history of past audits
- No file writes (no logs, no cache, no config on first run)

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Known limitations

- **Shell history.** If you pass the password inline (`imps "pass"`), it ends up in bash/zsh history and terminal scrollback. **Workaround:** Just run `imps` without arguments to use the secure interactive prompt, or prefix the command with a space (requires `HISTCONTROL=ignorespace`).
- **The default still makes one network call.** `--no-breach-check` disables the HIBP lookup; `-o/--offline` disables it. A `--quiet` pair that composes cleanly with the network flags is on the roadmap.
- **ASCII only.** The charset is estimated over printable ASCII. Non-ASCII passwords are underestimated in entropy.
- **Finite pattern list.** Top-150 plus four structural rules. An uncommon password is not automatically strong - it is only not *obviously* weak.
- **Crack times are theoretical.** They assume a constant hash rate on a given hardware profile. They do not model rainbow tables, targeted dictionaries, GPU-specific optimizations or side channels.
- **DARKWEB depends on HIBP.** If the API changes behaviour the panel reports it, but the tool does not update itself.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Checks

```bash
# Minimal run
imps "test"

# Strong password, no pattern
imps "correct-horse-battery-staple"

# Walk pattern - should show pattern warning
imps "qwertyuiop"

# Known breach - should show red alert in the DARKWEB SCANNER
imps "123456"

# Mask mode
imps -M "password"

# View modes
imps -s "correct-horse-battery-staple"     # only overall assessment
imps -dw "password"                        # only darkweb scanner

# Network control
imps --no-breach-check "password"          # HIBP skipped
imps --check-updates "password"            # Enable GitHub update check
imps -o "password"                         # both skipped

# Scriptable, network-free, one line
imps -o -s "password"
```

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Testing

```bash
pip install -e ".[test]"
pytest
```

The test suite runs offline. `network.check_breach` and `network.check_for_updates` are mocked in `tests/conftest.py`, and a `no_network` fixture fails any test that accidentally performs an HTTP request. CI runs on Windows, macOS and Linux across Python 3.8, 3.10 and 3.12.

The suite also includes golden scores for regression testing and property-based tests with Hypothesis. To regenerate the golden scores after an intentional engine change, run `python scripts/generate_golden.py`.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Project layout

```text
IsMyPwdSafe/
├── ismypwdsafe/
│   ├── __init__.py      # __version__, public API re-exports
│   ├── core.py          # AuditResult data model, analyze_password, entropy math
│   ├── patterns.py      # top-150 dictionary, QWERTY walks, years, repetition
│   ├── network.py       # HaveIBeenPwned range lookup, GitHub version check
│   ├── render.py        # JSON rendering for the machine contract
│   ├── ui.py            # ANSI helpers, boxes, animation, print_output
│   ├── cli.py           # argparse, orchestration, exit codes, entry()
│   └── main.py          # compatibility shim, removed in 2.0
├── schema/
│   └── result.schema.json
├── scripts/
│   ├── generate_golden.py
│   └── bench.py
├── tests/
│   ├── conftest.py
│   ├── golden/
│   ├── test_cli.py
│   ├── test_core.py
│   ├── test_edge_cases.py
│   ├── test_golden.py
│   ├── test_json.py
│   ├── test_network.py
│   ├── test_patterns.py
│   └── test_properties.py
├── .github/workflows/   # CI and Trusted Publishing
├── docs/screenshots/
├── CONTRIBUTING.md
├── SECURITY.md
├── CHANGELOG.md
├── .gitignore
├── LICENSE
├── pyproject.toml
├── version.txt
└── README.md
```

The split is deliberate. `core.py` and `patterns.py` contain no I/O and no ANSI: they can be imported and tested in isolation. `network.py` is the only module that talks to the network, and it can be mocked with a single import. `ui.py` is the only module that writes to stdout. `cli.py` is the only module that parses argv.

`tests/` mirrors the module split: one file per module. The suite is offline by construction, so it runs on a plane and in CI without flakiness.

`main.py` is a three-line shim that keeps `python -m ismypwdsafe.main` working; it will be removed in 2.0 when the `imps` entry point is the only documented invocation.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Roadmap

Actively in progress:

- **v2.0.0 Engine Rewrite** - weighted scoring (zxcvbn-like), full Unicode/emoji support, and a GitHub Action for CI/CD pipelines. This will be a major release with breaking changes to the scoring logic.

Out of scope by design: password storage, account systems, cloud sync.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Contributing

Contributions are welcome. Bug reports, feature requests and pull requests all help.

**If you want to contribute but the codebase is new to you**, open an issue first and describe what you would like to do - new pattern rules, additional hardware profiles in the resistance graph and new flags are all good entry points. Nothing here is locked in.

```bash
git clone https://github.com/YOUR-USERNAME/IsMyPwdSafe.git
cd IsMyPwdSafe
python -m venv .venv
source .venv/bin/activate     # Linux/macOS
.venv\Scripts\activate        # Windows
pip install -e .

imps "test-password"
python -m ismypwdsafe.main "test-password"
```

The `python -m ismypwdsafe.main` form works without an installed console script, and it is what you should use when you are editing `cli.py` and have not reinstalled yet.

For non-trivial changes please open an issue first to agree on the approach.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## Contact

- **Issues / ideas:** [github.com/Roma476/IsMyPwdSafe/issues](https://github.com/Roma476/IsMyPwdSafe/issues)
- **Pull requests:** [github.com/Roma476/IsMyPwdSafe/pulls](https://github.com/Roma476/IsMyPwdSafe/pulls)

If you have a feature in mind that is not on the roadmap, or you disagree with something already on it, say so - the roadmap above is a plan, not a contract.

<p align="right">(<a href="#top">back to top</a>)</p>

---

## License

Released under the MIT License. See [`LICENSE`](LICENSE) for the full text.