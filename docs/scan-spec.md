# `imps scan` specification

Status: implemented for `2.1.0`; `2.1.1` is an Action Marketplace metadata
patch. Pre-commit integration and the allowlist are planned for `2.1.2`.

`imps scan` audits password-like values in dotenv-style files. It is designed
for a repository checkout and CI, not for scanning an entire workstation. The
scanner never writes a raw value to stdout, stderr, JSON, a log, a GitHub
annotation, or an error message.

## Non-goals

- It is not a password manager, a secret manager, or a generic secret scanner.
- It does not prove that a value is safe.
- It does not look for credentials in source code, YAML, JSON, shell scripts,
  or arbitrary text. The supported input is dotenv-style `KEY=VALUE` files.
- It is not a replacement for secret scanning. A committed real token should be
  rotated even after the scanner reports it.

## Discovery

With no positional paths:

- If the current directory is a git work tree, scan only tracked files whose
  basename matches `.env`, `.env.*`, `*.env`, or `*.env.*`.
- Files ignored by git are not included by default.
- `--include-untracked` adds untracked and ignored files. This is the opt-in for
  a local `.env` that is intentionally ignored.
- Outside a git work tree, the command exits `2` and explains that `--no-git`
  or explicit paths are required.
- `--no-git` walks the current directory recursively.

Explicit paths are always authoritative:

- An explicit file is scanned even if its name does not match the default
  patterns and even if git ignores it.
- An explicit directory is walked recursively using the include patterns.
- A missing path is a usage error with exit `2`.

The walker skips `.git`, `.hg`, `.svn`, virtual environments, dependency
directories, build output, caches, symlinks, binary files, and files larger than
1 MiB. A value longer than 1024 characters is skipped with a warning; a PEM
block is still detected from the raw file text.

Additional `--include GLOB` patterns are appended to the defaults. A glob that
contains `/` is matched against the path; otherwise it is matched against the
basename.

## Parsing

The parser is deliberately line-oriented so findings can carry a line number.
It does not interpolate variables.

Supported:

- blank lines and `#` comments;
- `export KEY=VALUE`;
- unquoted values, single-quoted values, and double-quoted values;
- inline comments after quoted values;
- inline comments in unquoted values when `#` is preceded by whitespace;
- common double-quoted escapes;
- backslash line continuations;
- UTF-8 with a BOM and CRLF line endings;
- `${VAR}`, `$VAR`, empty values, and obvious placeholders are counted and
  skipped.

Malformed lines are counted and reported as warnings without echoing their
contents. A quoted value that is unterminated, or that has non-comment trailing
characters, is not scored.

### Key classification

Classification is by key name, never by value heuristics.

| Kind | Key words |
| ---- | --------- |
| `password` | `PASSWORD`, `PASSWD`, `PASSPHRASE`, `PWD`, `PASS` |
| `token` | `SECRET`, `TOKEN`, `API_KEY`, `ACCESS_KEY`, `PRIVATE_KEY`, `CLIENT_SECRET`, `AUTH_TOKEN` |

Keys with `HASH`, `SALT`, `FILE`, `PATH`, `URL`, `URI`, `EMAIL`, `USER`,
`USERNAME`, `LENGTH`, `MIN`, `MAX`, `RESET`, `EXPIRY`, `TTL`, `STRENGTH`,
`POLICY`, `ENABLED`, `VERSION`, `ALGORITHM`, or `ID` after the credential word
are skipped. Example: `DB_PASSWORD_HASH` and `PASSWORD_RESET_TOKEN` are not
passwords, while `USER_PASSWORD` still is.

`PASSWORD` values are scored with the selected zxcvbn engine. `TOKEN` values
have no numeric strength score and are not sent to HIBP; HIBP is a password
corpus, not an API-key leak database. The report shows a format label when one
is recognized (for example GitHub, Stripe, Slack, AWS, Google, or JWT) and says
`HIBP: not applicable`. An unrecognized token still appears, with a warning that
no strength score is inferred.

### Private keys

A private-key header is a `CRITICAL` finding and exit `6`. The scanner reports
the key name and line, never the key material. Recognized formats include RSA,
EC, DSA, OpenSSH, PKCS#8, encrypted PEM, PGP private-key blocks, and SSH2
private-key blocks. A PEM block is never sent to HIBP.

## HIBP

- HIBP is on by default for `PASSWORD` findings.
- `--no-breach-check` sets `breach.reason = "disabled"`.
- `--offline` sets `breach.reason = "offline"`.
- Neither `disabled` nor `offline` produces exit `5`.
- Only unique values are checked. Duplicate values share one request.
- Concurrency is four by default, each request has a five-second timeout, and
  the whole scan has a 60-second deadline.
- On a global timeout, completed findings are retained, pending values get
  `breach.reason = "scan_timeout"`, `incomplete = true`, and
  `unchecked_values` is the number of unique values not checked.
- An HIBP API error gets `breach.reason = "api_error"`.

## Exit codes

The scan uses this precedence:

```text
6 critical private key
3 at least one HIBP-pwned password
5 incomplete or unknown HIBP status
4 no usable scoring engine / engine failure
1 at least one password below --min-score
0 otherwise
2 usage error, missing path, or no git repository without --no-git
```

`--min-score` defaults to `50`. A pwned password is forced to score `0` and
`rating = "weak"` for display, but the breach is the reason for exit `3`.

A usage error (`2`) is not represented by a scan JSON document; the message is
on stderr. `--json-full` is not supported by scan and is a usage error.

## Output

The human report contains paths, line numbers, key names, scores, ratings,
pattern labels, format labels, and breach status. It never contains values or
value fragments.

`--json` emits a strict document with:

- `schema_version: "1.0"` and `kind: "scan"`;
- `tool_version`, `exit_code`, `summary`, `findings`, `warnings`;
- `incomplete`, `unchecked_values`, and `engine_error`.

Each finding contains `path`, `line`, `key`, `kind`, `score`, `rating`,
`patterns`, `breach`, `token_format`, and `message`. `breach` is `null` for
tokens and critical findings. See [`schema/scan.schema.json`](../schema/scan.schema.json).

`--quiet` suppresses both the human report and JSON. `--json` and `--quiet` can
be combined; quiet wins.

## 2.1.2 follow-up

The allowlist will be based on a key name plus a fingerprint of the value, never
the raw value:

```text
path + key + fingerprint(value)
```

Pre-commit will receive only staged file paths, will default to offline mode,
and will not use discovery. The allowlist is for non-sensitive fixtures, not a
way to bless a live credential.
