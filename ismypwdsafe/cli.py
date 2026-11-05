"""Command-line interface: argparse, input handling, and exit codes."""
from __future__ import annotations

import argparse
import getpass
import sys
from typing import Optional

from . import __version__, network
from .core import analyze_password
from .render import render_json
from .ui import dim, err, get_width, print_output, warn


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="imps",
        description="IsMyPwdSafe - zxcvbn, but readable. Your password stays local.",
        usage="imps [options] [password|-]",
        epilog=(
            "Subcommands:\n"
            "  imps scan [options] [path ...]\n"
            "      Audit .env files without printing values. Use 'imps -- scan'\n"
            "      to audit the literal password 'scan'.\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    parser.add_argument(
        "--engine",
        choices=["auto", "ts", "python", "native"],
        default="auto",
        help=(
            "Scoring engine. auto (default) uses zxcvbn-ts when Node 18+ is "
            "available, then zxcvbn-python. native is the explicit legacy "
            "heuristic and is never selected automatically."
        ),
    )
    parser.add_argument(
        "-M",
        "--Mask",
        action="store_true",
        help="Mask the password and matched tokens in the terminal UI.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Machine-readable JSON. Matched tokens are redacted by default.",
    )
    parser.add_argument(
        "--json-full",
        action="store_true",
        help="JSON including matched tokens. Use with care: this can reveal the password.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress all output and only return the exit code.",
    )
    parser.add_argument(
        "-o",
        "--offline",
        action="store_true",
        help="Disable all network requests (HIBP and update check).",
    )
    parser.add_argument(
        "--no-breach-check",
        action="store_true",
        help="Skip the HaveIBeenPwned lookup but allow explicit update checks.",
    )
    parser.add_argument(
        "--check-updates",
        action="store_true",
        help="Check GitHub for a newer version (disabled by default for privacy).",
    )
    view_group = parser.add_mutually_exclusive_group()
    view_group.add_argument(
        "-s",
        "--short",
        action="store_true",
        help="Show the score, breach verdict, and engine line.",
    )
    view_group.add_argument(
        "-dw",
        "--darkweb",
        action="store_true",
        help="Display only the breach check.",
    )
    parser.add_argument(
        "password",
        nargs="?",
        help="Password to audit. Use '-' to read it from stdin.",
    )
    parser.add_argument(
        "--no-update-check",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _read_password(args: argparse.Namespace) -> Optional[str]:
    if args.password == "-":  # noqa: S105
        return sys.stdin.read().rstrip("\r\n")
    if args.password:
        return str(args.password)
    if not sys.stdin.isatty():
        return None
    try:
        return getpass.getpass(prompt="Enter password to audit: ")
    except Exception as exc:  # noqa: BLE001 - no traceback for terminal errors
        print(err(f"[!] Error reading password: {exc}"), file=sys.stderr)
        return None


def main(argv: Optional[list[str]] = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "scan":
        from .scan import scan_main

        return scan_main(raw_argv[1:])

    parser = _build_parser()
    args = parser.parse_args(raw_argv)
    if args.json_full:
        args.json = True

    if args.short:
        view = "short"
    elif args.darkweb:
        view = "darkweb"
    else:
        view = "full"

    if args.no_update_check and not args.quiet:
        print(
            "Warning: --no-update-check is deprecated and is now the default. "
            "Use --check-updates to enable it.",
            file=sys.stderr,
        )

    skip_breach = args.offline or args.no_breach_check
    password = _read_password(args)
    if password is None:
        password = ""

    if (
        args.check_updates
        and not args.offline
        and view == "full"
        and not args.json
        and not args.quiet
    ):
        new_ver = network.check_for_updates(__version__)
        if new_ver:
            width = get_width()
            msg = (
                f"[!] A new version of IsMyPwdSafe is available: v{new_ver} "
                f"(you have v{__version__})"
            )
            print(warn(msg.center(width)))
            print(
                dim(
                    "    Update now: "
                    "https://github.com/Roma476/IsMyPwdSafe/releases/latest".center(width)
                    + "\n"
                )
            )

    if args.offline:
        breach_reason = "offline"
    elif args.no_breach_check:
        breach_reason = "disabled"
    else:
        breach_reason = None

    result = analyze_password(
        password,
        check_breach=not skip_breach,
        breach_skip_reason=breach_reason,
        engine_name=args.engine,
    )

    if not args.quiet:
        if args.json:
            print(render_json(result, include_tokens=args.json_full))
        else:
            print_output(result, password, mask_mode=args.Mask, view=view)

    return result.exit_code


def entry() -> int:
    """Console-script entry point. Handles interrupts and closed pipes."""
    try:
        return main()
    except KeyboardInterrupt:
        print("\n" + warn("[!] Audit interrupted by user."), file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0
