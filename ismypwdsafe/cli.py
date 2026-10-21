"""Command-line interface: argparse, update check, exit code orchestration."""
from __future__ import annotations

import argparse
import getpass
import sys

from . import __version__, network
from .core import analyze_password
from .render import render_json
from .ui import dim, err, get_width, print_output, warn


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="IsMyPwdSafe CLI Engine - The only password tester that doesn't spy on you.",
        usage="imps [-M] [-o | --no-breach-check] [-s | -dw] <password>",
        add_help=True,
    )
    parser.add_argument(
        "-M", "--Mask",
        action="store_true",
        help="Completely mask the input password with asterisks in the summary screen box",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output the result as a machine-readable JSON document",
    )
    parser.add_argument(
        "-o", "--offline",
        action="store_true",
        help="Disable all network requests. Implies --no-breach-check and --no-update-check",
    )
    parser.add_argument(
        "--no-breach-check",
        action="store_true",
        help="Skip the HaveIBeenPwned breach lookup, keep the GitHub update check",
    )
    parser.add_argument(
        "--check-updates",
        action="store_true",
        help="Check for newer versions on startup (disabled by default for privacy)",
    )
    view_group = parser.add_mutually_exclusive_group()
    view_group.add_argument(
        "-s", "--short",
        action="store_true",
        help="Display only the overall security assessment",
    )
    view_group.add_argument(
        "-dw", "--darkweb",
        action="store_true",
        help="Display only the dark web breach check",
    )
    parser.add_argument(
        "password",
        type=str,
        nargs="?",
        help="The raw text password string to submit for auditing",
    )
    # deprecated
    parser.add_argument(
        "--no-update-check",
        action="store_true",
        help=argparse.SUPPRESS, # Hides from help text, but still works for backwards compatibility
    )
    return parser


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    password = args.password

    if args.no_update_check:
        print(
            "Warning: --no-update-check is deprecated and is now the default behavior. "
            "Use --check-updates to enable the check.",
            file=sys.stderr
        )

    if args.short:
        view = "short"
    elif args.darkweb:
        view = "darkweb"
    else:
        view = "full"

    skip_breach = args.offline or args.no_breach_check

    if password == "-":  # noqa: S105
        password = sys.stdin.read().rstrip("\n")
    elif not password:
        try:
            password = getpass.getpass(prompt="Enter password to audit: ")
        except Exception as e:
            print(err(f"[!] Error reading password: {e}"))
            return 65
        if not password:
            print(warn("[!] No password provided."))
            return 65

    if args.check_updates and view == "full" and not args.json:
        new_ver = network.check_for_updates(__version__)
        if new_ver:
            width = get_width()
            msg = f"[!] A new version of IsMyPwdSafe is available: v{new_ver} (you have v{__version__})"  # noqa: E501
            print(warn(msg.center(width)))
            print(dim("    Update now: https://github.com/Roma476/IsMyPwdSafe/releases/latest".center(width) + "\n"))  # noqa: E501

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
        tool_version=__version__,
    )

    if args.json:
        print(render_json(result))
    else:
        print_output(result, password, mask_mode=args.Mask, view=view)
    return result.exit_code


def entry() -> int:
    """Console-script entry point. Handles KeyboardInterrupt."""
    try:
        return main()
    except KeyboardInterrupt:
        print("\n" + warn("[!] Audit interrupted by user."))
        return 130