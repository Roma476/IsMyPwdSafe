"""``imps scan``: audit passwords and tokens in dotenv-style files.

The scanner is deliberately separate from the single-password CLI.  It has its
own documents, output, and exit-code precedence, and it never emits a secret.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import __version__, network
from .core import AuditResult, analyze_password
from .scan_parser import classify_key, parse_env_text

SCAN_SCHEMA_VERSION = "1.0"
EXIT_CRITICAL = 6

DEFAULT_INCLUDE_PATTERNS = (".env", ".env.*", "*.env", "*.env.*")
EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "node_modules",
    "site-packages",
    "venv",
    ".venv",
}
MAX_FILE_BYTES = 1024 * 1024
MAX_VALUE_CHARS = 1024

_TOKEN_PREFIXES: Tuple[Tuple[str, str], ...] = (
    ("sk_live_", "Stripe live secret key"),
    ("sk_test_", "Stripe test secret key"),
    ("rk_live_", "Stripe restricted key"),
    ("whsec_", "Stripe webhook secret"),
    ("ghp_", "GitHub personal access token"),
    ("gho_", "GitHub OAuth token"),
    ("ghu_", "GitHub user token"),
    ("ghs_", "GitHub server token"),
    ("github_pat_", "GitHub fine-grained token"),
    ("xoxb-", "Slack bot token"),
    ("xoxp-", "Slack user token"),
    ("xoxa-", "Slack app token"),
    ("xoxr-", "Slack refresh token"),
)
_AWS_ACCESS_KEY_RE = re.compile(r"^AKIA[0-9A-Z]{16}$")
_GOOGLE_API_KEY_RE = re.compile(r"^AIza[0-9A-Za-z_-]{35}$")
_JWT_RE = re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")


class ScanUsageError(RuntimeError):
    """Bad paths, missing git, or other usage-level scan failures."""


@dataclass(frozen=True)
class ScanOptions:
    paths: Tuple[str, ...] = ()
    engine: str = "auto"
    min_score: int = 50
    check_breach: bool = True
    offline: bool = False
    include_patterns: Tuple[str, ...] = DEFAULT_INCLUDE_PATTERNS
    include_untracked: bool = False
    no_git: bool = False
    timeout: float = 60.0
    concurrency: int = 4


@dataclass(frozen=True)
class ScanFinding:
    path: str
    line: int
    key: str
    kind: str
    score: Optional[int]
    rating: Optional[str]
    patterns: Tuple[str, ...]
    breach: Optional[network.BreachResult]
    token_format: Optional[str]
    message: Optional[str]
    # Internal-only binding to the deduplicated HIBP request.  It is not part of
    # the JSON contract and is never rendered.
    fingerprint: Optional[str] = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class ScanResult:
    findings: Tuple[ScanFinding, ...]
    files: Tuple[str, ...]
    exit_code: int
    summary: Dict[str, int]
    warnings: Tuple[str, ...]
    incomplete: bool
    unchecked_values: int
    engine_error: Optional[str]


def _display_path(path: Path, cwd: Path) -> str:
    try:
        return path.resolve().relative_to(cwd.resolve()).as_posix()
    except (OSError, ValueError):
        return path.resolve().as_posix()


def _matches_pattern(
    path: Path, patterns: Iterable[str], root: Optional[Path] = None
) -> bool:
    name = path.name
    posix = path.as_posix()
    if root is not None:
        try:
            posix = path.resolve().relative_to(root.resolve()).as_posix()
        except (OSError, ValueError):
            pass
    for pattern in patterns:
        if "/" in pattern:
            if fnmatch.fnmatch(posix, pattern):
                return True
        elif fnmatch.fnmatch(name, pattern):
            return True
    return False


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _walk_files(root: Path, patterns: Sequence[str]) -> List[Path]:
    found: List[Path] = []
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        dirs[:] = sorted(
            directory
            for directory in dirs
            if directory not in EXCLUDED_DIRS and not (current_path / directory).is_symlink()
        )
        for name in sorted(files):
            path = current_path / name
            if path.is_symlink() or _is_excluded(path):
                continue
            if _matches_pattern(path, patterns, root):
                found.append(path)
    return found


def _git_output(cwd: Path, args: Sequence[str]) -> str:
    try:
        proc = subprocess.run(  # noqa: S603
            ["git", *args],  # noqa: S607
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ScanUsageError(f"git is unavailable: {exc}") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or "").strip()
        raise ScanUsageError(detail or "git command failed")
    return proc.stdout


def _git_files(cwd: Path, include_untracked: bool) -> List[Path]:
    try:
        inside = _git_output(cwd, ["rev-parse", "--is-inside-work-tree"]).strip()
    except ScanUsageError as exc:
        raise ScanUsageError(
            "not a git repository; use --no-git to scan matching files, "
            "or pass explicit paths"
        ) from exc
    if inside != "true":
        raise ScanUsageError(
            "not a git repository; use --no-git to scan matching files, "
            "or pass explicit paths"
        )

    names = [name for name in _git_output(cwd, ["ls-files", "-z"]).split("\0") if name]
    if include_untracked:
        # Include both ordinary untracked files and files ignored by
        # .gitignore.  The latter is the common case for a local .env, and the
        # user explicitly opted in with --include-untracked.
        names.extend(
            name
            for name in _git_output(
                cwd, ["ls-files", "-z", "--others", "--exclude-standard"]
            ).split("\0")
            if name
        )
        names.extend(
            name
            for name in _git_output(
                cwd, ["ls-files", "-z", "--others", "--ignored", "--exclude-standard"]
            ).split("\0")
            if name
        )
    # git returns paths relative to the current directory.
    return [cwd / name for name in names]


def discover_files(
    options: ScanOptions, *, cwd: Optional[Path] = None
) -> List[Path]:
    """Discover files according to the scan contract.

    With no paths, only tracked files are scanned.  Explicit files are always
    scanned, and explicit directories are walked recursively.  ``--no-git``
    opts into walking the current directory without git.
    """
    root = (cwd or Path.cwd()).resolve()
    patterns = tuple(options.include_patterns)
    found: List[Path] = []

    if options.paths:
        for raw in options.paths:
            path = Path(raw)
            if not path.is_absolute():
                path = root / path
            if not path.exists():
                raise ScanUsageError(f"path not found: {raw}")
            if path.is_dir():
                found.extend(_walk_files(path, patterns))
            elif path.is_file():
                if path.is_symlink():
                    continue
                found.append(path)
            else:
                raise ScanUsageError(f"not a regular file or directory: {raw}")
    elif options.no_git:
        found.extend(_walk_files(root, patterns))
    else:
        for path in _git_files(root, options.include_untracked):
            if _is_excluded(path):
                continue
            if _matches_pattern(path, patterns, root):
                found.append(path)

    unique: Dict[str, Path] = {}
    for path in found:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        unique.setdefault(key, path)
    return sorted(unique.values(), key=lambda item: str(item))


def _read_text(path: Path) -> Optional[str]:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\0" in raw:
        return None
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("utf-8-sig", errors="replace")


def _token_format(value: str) -> str:
    for prefix, label in _TOKEN_PREFIXES:
        if value.startswith(prefix):
            return label
    if _AWS_ACCESS_KEY_RE.match(value):
        return "AWS access key"
    if _GOOGLE_API_KEY_RE.match(value):
        return "Google API key"
    if _JWT_RE.match(value):
        return "JWT"
    return "unknown"


def _patterns_from_result(result: AuditResult) -> Tuple[str, ...]:
    patterns = {
        str(match.get("pattern"))
        for match in result.sequence
        if isinstance(match, dict) and match.get("pattern")
    }
    # A pure brute-force match is the absence of a recognizable pattern.
    patterns.discard("bruteforce")
    return tuple(sorted(patterns))[:6]


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _breach_results(
    values: Dict[str, str], options: ScanOptions
) -> Tuple[Dict[str, network.BreachResult], int]:
    """Check unique password values, respecting the global deadline."""
    if options.offline:
        reason = "offline"
        return (
            {key: network.BreachResult(False, None, None, reason) for key in values},
            0,
        )
    if not options.check_breach:
        reason = "disabled"
        return (
            {key: network.BreachResult(False, None, None, reason) for key in values},
            0,
        )
    if not values:
        return {}, 0

    results: Dict[str, network.BreachResult] = {}
    futures: Dict[Future[network.BreachResult], str] = {}
    pending: Set[Future[network.BreachResult]] = set()
    executor = ThreadPoolExecutor(max_workers=max(1, int(options.concurrency)))
    try:
        for key, value in values.items():
            futures[executor.submit(network.check_breach, value)] = key
        done, pending = wait(futures.keys(), timeout=max(0.0, options.timeout))
        for future in done:
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception:  # noqa: BLE001 - HIBP failures are not fatal here
                results[key] = network.BreachResult(True, None, None, "api_error")
        for future in pending:
            key = futures[future]
            results[key] = network.BreachResult(True, None, None, "scan_timeout")
            future.cancel()
        if pending:
            executor.shutdown(wait=False)
        else:
            executor.shutdown(wait=True)
    except Exception:  # noqa: BLE001 - never traceback on network setup
        for key in values:
            results.setdefault(key, network.BreachResult(True, None, None, "api_error"))
        executor.shutdown(wait=False)
    return results, len(pending)


def _summary(findings: Sequence[ScanFinding], files: Sequence[str]) -> Dict[str, int]:
    passwords = [item for item in findings if item.kind == "password"]
    tokens = [item for item in findings if item.kind == "token"]
    critical = [item for item in findings if item.kind == "critical"]
    return {
        "files": len(files),
        "values": len(passwords) + len(tokens),
        "weak": sum(
            1
            for item in passwords
            if item.score is not None and item.score < 50
        ),
        "medium": sum(
            1
            for item in passwords
            if item.score is not None and 50 <= item.score < 75
        ),
        "strong": sum(
            1
            for item in passwords
            if item.score is not None and item.score >= 75
        ),
        "pwned": sum(
            1 for item in findings if item.breach is not None and item.breach.pwned
        ),
        "unknown": sum(
            1
            for item in findings
            if item.breach is not None
            and item.breach.checked
            and item.breach.pwned is None
        ),
        "critical": len(critical),
    }


def _scan_exit(
    findings: Sequence[ScanFinding],
    *,
    min_score: int,
    engine_error: Optional[str],
    incomplete: bool,
) -> int:
    if any(item.kind == "critical" for item in findings):
        return EXIT_CRITICAL
    if any(item.breach is not None and item.breach.pwned for item in findings):
        return 3
    if incomplete or any(
        item.breach is not None
        and item.breach.checked
        and item.breach.pwned is None
        for item in findings
    ):
        return 5
    if engine_error:
        return 4
    if any(
        item.kind == "password"
        and item.score is not None
        and item.score < min_score
        for item in findings
    ):
        return 1
    return 0


def scan_files(options: ScanOptions, *, cwd: Optional[Path] = None) -> ScanResult:
    """Scan files and return findings without ever retaining a raw value."""
    root = (cwd or Path.cwd()).resolve()
    files = discover_files(options, cwd=root)

    findings: List[ScanFinding] = []
    warnings: List[str] = []
    password_values: Dict[str, str] = {}
    engine_error: Optional[str] = None
    skipped_large = 0
    unparseable_lines = 0
    empty_values = 0
    references = 0
    placeholders = 0

    for path in files:
        display = _display_path(path, root)
        text = _read_text(path)
        if text is None:
            warnings.append(f"{display}: skipped (unreadable, binary, or too large)")
            continue
        parsed = parse_env_text(text)
        unparseable_lines += parsed.unparseable_lines
        empty_values += parsed.empty_values
        references += parsed.references
        placeholders += parsed.placeholders
        warnings.extend(f"{display}: {warning}" for warning in parsed.warnings)

        for critical in parsed.critical:
            findings.append(
                ScanFinding(
                    path=display,
                    line=critical.line,
                    key=critical.key,
                    kind="critical",
                    score=None,
                    rating=None,
                    patterns=(),
                    breach=None,
                    token_format=critical.key_format,
                    message=(
                        "private key found in a tracked or explicitly scanned file; "
                        "move it to a secret manager and rotate it"
                    ),
                )
            )

        critical_keys = {critical.key for critical in parsed.critical}
        for entry in parsed.entries:
            if entry.key in critical_keys:
                # The raw PEM block is already reported as CRITICAL.  Do not
                # also show it as a token-like value.
                continue
            kind = classify_key(entry.key)
            if kind is None:
                continue
            if len(entry.value) > MAX_VALUE_CHARS:
                skipped_large += 1
                warnings.append(
                    f"{display}:{entry.line} {entry.key}: skipped value longer than "
                    f"{MAX_VALUE_CHARS} characters"
                )
                continue

            if kind == "token":
                token_format = _token_format(entry.value)
                message = None
                if token_format == "unknown":  # noqa: S105 - format label, not a password
                    message = (
                        "unrecognized token format; no strength score is inferred"
                    )
                elif len(entry.value) < 20:
                    message = (
                        "token-like value is shorter than 20 characters; "
                        "no strength score is inferred"
                    )
                findings.append(
                    ScanFinding(
                        path=display,
                        line=entry.line,
                        key=entry.key,
                        kind="token",
                        score=None,
                        rating=None,
                        patterns=(),
                        breach=None,
                        token_format=token_format,
                        message=message,
                    )
                )
                continue

            result = analyze_password(
                entry.value,
                check_breach=False,
                engine_name=options.engine,
            )
            if result.score is None:
                # Do not surface the engine's raw exception text here.  An
                # engine could include the input in an error message, and scan
                # output is not allowed to contain values.
                engine_error = "scoring engine failed; no score was produced"
                findings.append(
                    ScanFinding(
                        path=display,
                        line=entry.line,
                        key=entry.key,
                        kind="password",
                        score=None,
                        rating=None,
                        patterns=(),
                        breach=None,
                        token_format=None,
                        message=engine_error,
                    )
                )
                continue
            fingerprint = _fingerprint(entry.value)
            password_values[fingerprint] = entry.value
            findings.append(
                ScanFinding(
                    path=display,
                    line=entry.line,
                    key=entry.key,
                    kind="password",
                    score=result.score.value,
                    rating=result.score.rating,
                    patterns=_patterns_from_result(result),
                    breach=None,
                    token_format=None,
                    message=None,
                    fingerprint=fingerprint,
                )
            )

    breach_map, unchecked_values = _breach_results(password_values, options)

    final_findings: List[ScanFinding] = []
    for item in findings:
        if item.kind != "password" or item.fingerprint is None:
            final_findings.append(item)
            continue
        breach = breach_map.get(item.fingerprint)
        if breach is not None and breach.pwned:
            final_findings.append(
                replace(
                    item,
                    score=0,
                    rating="weak",
                    breach=breach,
                    message=None,
                )
            )
        else:
            final_findings.append(replace(item, breach=breach))

    summary = _summary(final_findings, [_display_path(path, root) for path in files])
    summary.update(
        {
            "unparseable_lines": unparseable_lines,
            "empty_values": empty_values,
            "references": references,
            "placeholders": placeholders,
            "skipped_large": skipped_large,
        }
    )
    exit_code = _scan_exit(
        final_findings,
        min_score=options.min_score,
        engine_error=engine_error,
        incomplete=unchecked_values > 0,
    )
    display_files = tuple(_display_path(path, root) for path in files)
    return ScanResult(
        findings=tuple(final_findings),
        files=display_files,
        exit_code=exit_code,
        summary=summary,
        warnings=tuple(warnings),
        incomplete=unchecked_values > 0,
        unchecked_values=unchecked_values,
        engine_error=engine_error,
    )


def _breach_label(breach: Optional[network.BreachResult]) -> str:
    if breach is None:
        return "HIBP: not applicable"
    if breach.reason == "offline":
        return "HIBP: offline"
    if breach.reason == "disabled":
        return "HIBP: disabled"
    if breach.reason == "scan_timeout":
        return "HIBP: unknown (timeout)"
    if breach.reason == "api_error":
        return "HIBP: unknown (network error)"
    if breach.pwned:
        return f"HIBP: pwned ({breach.breach_count or 'many'})"
    return "HIBP: clean"


def render_scan_text(result: ScanResult) -> str:
    lines: List[str] = []
    lines.append(f"IsMyPwdSafe scan · {len(result.files)} file(s)")
    lines.append("")
    if not result.findings:
        lines.append("No password-like or token-like values found.")
    for item in result.findings:
        location = f"{item.path}:{item.line}"
        if item.kind == "critical":
            lines.append(f"CRITICAL  {location}  {item.key}  private key found")
            if item.message:
                lines.append(f"          {item.message}")
            continue
        if item.kind == "token":
            label = item.token_format or "unknown"
            lines.append(
                f"{location}  {item.key}  —  token  {label}  HIBP: not applicable"
            )
            if item.message:
                lines.append(f"          {item.message}")
            continue
        patterns = ", ".join(item.patterns) if item.patterns else "—"
        score = "—" if item.score is None else f"{item.score}/100"
        rating = item.rating or "—"
        lines.append(
            f"{location}  {item.key}  {score}  {rating}  {patterns}  "
            f"{_breach_label(item.breach)}"
        )
        if item.message:
            lines.append(f"          {item.message}")

    summary = result.summary
    lines.append("")
    lines.append(
        f"{summary['files']} files · {summary['values']} values · "
        f"{summary['weak']} weak · {summary['medium']} medium · "
        f"{summary['strong']} strong · {summary['pwned']} pwned · "
        f"{summary['critical']} critical"
    )
    if result.incomplete:
        lines.append(
            f"HIBP incomplete: {result.unchecked_values} unique value(s) not checked "
            "before the scan timeout."
        )
    if summary.get("unparseable_lines"):
        lines.append(f"{summary['unparseable_lines']} unparseable line(s) skipped.")
    for warning in result.warnings[:5]:
        lines.append(f"warning: {warning}")
    if len(result.warnings) > 5:
        lines.append(f"warning: {len(result.warnings) - 5} more warning(s)")
    return "\n".join(lines)


def scan_result_to_dict(result: ScanResult) -> Dict[str, object]:
    findings: List[Dict[str, object]] = []
    for item in result.findings:
        findings.append(
            {
                "path": item.path,
                "line": item.line,
                "key": item.key,
                "kind": item.kind,
                "score": item.score,
                "rating": item.rating,
                "patterns": list(item.patterns),
                "breach": asdict(item.breach) if item.breach is not None else None,
                "token_format": item.token_format,
                "message": item.message,
            }
        )
    return {
        "schema_version": SCAN_SCHEMA_VERSION,
        "kind": "scan",
        "tool_version": __version__,
        "exit_code": result.exit_code,
        "summary": result.summary,
        "findings": findings,
        "warnings": list(result.warnings),
        "incomplete": result.incomplete,
        "unchecked_values": result.unchecked_values,
        "engine_error": result.engine_error,
    }


def render_scan_json(result: ScanResult) -> str:
    return json.dumps(
        scan_result_to_dict(result),
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
    )


def _build_scan_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imps scan",
        description=(
            "Audit password-like values in dotenv files. The scan never prints "
            "the values it reads."
        ),
        usage="imps scan [options] [path ...]",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories. With no paths, scan tracked .env files.",
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "ts", "python", "native"],
        default="auto",
        help="Scoring engine for password-like values (default: auto).",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=50,
        help="Fail when a password score is below this value (default: 50).",
    )
    parser.add_argument(
        "--no-breach-check",
        action="store_true",
        help="Skip HIBP for password-like values.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Disable HIBP and all other network calls.",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="Additional file-name or path glob(s) to scan.",
    )
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="Include untracked and ignored files in git discovery.",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="Walk the current directory instead of using git discovery.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Global HIBP deadline in seconds (default: 60).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Maximum concurrent HIBP requests (default: 4).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the scan JSON document. Values are never included.",
    )
    parser.add_argument(
        "--json-full",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output and return only the exit code.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def scan_main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_scan_parser()
    args = parser.parse_args(argv)
    if args.json_full:
        parser.error("--json-full is not supported by scan; scan never emits values")
    if not 0 <= args.min_score <= 100:
        parser.error("--min-score must be between 0 and 100")
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    if args.timeout < 0:
        parser.error("--timeout must be zero or greater")

    patterns = tuple(DEFAULT_INCLUDE_PATTERNS) + tuple(args.include)
    options = ScanOptions(
        paths=tuple(args.paths),
        engine=args.engine,
        min_score=args.min_score,
        check_breach=not args.no_breach_check,
        offline=args.offline,
        include_patterns=patterns,
        include_untracked=args.include_untracked,
        no_git=args.no_git,
        timeout=args.timeout,
        concurrency=args.concurrency,
    )
    try:
        result = scan_files(options)
    except ScanUsageError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        if args.json:
            print(render_scan_json(result))
        else:
            print(render_scan_text(result))
    return result.exit_code


__all__ = [
    "DEFAULT_INCLUDE_PATTERNS",
    "EXIT_CRITICAL",
    "SCAN_SCHEMA_VERSION",
    "ScanFinding",
    "ScanOptions",
    "ScanResult",
    "ScanUsageError",
    "discover_files",
    "render_scan_json",
    "render_scan_text",
    "scan_files",
    "scan_main",
    "scan_result_to_dict",
]
