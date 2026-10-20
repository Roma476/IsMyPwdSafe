import sys
import math
import shutil
import os
import argparse
import re
import time
import textwrap
import getpass

from . import __version__
from . import network
from .core import analyze_password



# ================== ANSI COLOR SUPPORT ==================
os.system("")

def _supports_color():
    """
    Detects whether the current terminal supports ANSI colors.
    Respects the NO_COLOR standard (https://no-color.org/) and
    common environment variables used by CI systems.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if not sys.stdout.isatty():
        return False
    if os.name == "nt":
        # Windows: assume modern terminal after os.system("") above
        return True
    # Linux/macOS: check TERM
    term = os.environ.get("TERM", "")
    return term not in ("", "dumb")


USE_COLOR = _supports_color()
ANIMATE = sys.stdout.isatty() and USE_COLOR


class C:
    """ANSI color palette. Empty strings if colors are disabled."""
    RESET   = "\033[0m"       if USE_COLOR else ""
    BOLD    = "\033[1m"       if USE_COLOR else ""
    DIM     = "\033[2m"       if USE_COLOR else ""
    ITALIC  = "\033[3m"       if USE_COLOR else ""
    UNDER   = "\033[4m"       if USE_COLOR else ""

    # Foreground
    BLACK   = "\033[30m"      if USE_COLOR else ""
    RED     = "\033[31m"      if USE_COLOR else ""
    GREEN   = "\033[32m"      if USE_COLOR else ""
    YELLOW  = "\033[33m"      if USE_COLOR else ""
    BLUE    = "\033[34m"      if USE_COLOR else ""
    MAGENTA = "\033[35m"      if USE_COLOR else ""
    CYAN    = "\033[36m"      if USE_COLOR else ""
    WHITE   = "\033[37m"      if USE_COLOR else ""
    GRAY    = "\033[90m"      if USE_COLOR else ""

    # Bright
    BRIGHT_RED     = "\033[91m" if USE_COLOR else ""
    BRIGHT_GREEN   = "\033[92m" if USE_COLOR else ""
    BRIGHT_YELLOW  = "\033[93m" if USE_COLOR else ""
    BRIGHT_BLUE    = "\033[94m" if USE_COLOR else ""
    BRIGHT_MAGENTA = "\033[95m" if USE_COLOR else ""
    BRIGHT_CYAN    = "\033[96m" if USE_COLOR else ""
    BRIGHT_WHITE   = "\033[97m" if USE_COLOR else ""


def colorize(text, *codes):
    """Wrap text in ANSI codes and reset. No-op if colors disabled."""
    if not USE_COLOR or not codes:
        return text
    return "".join(codes) + str(text) + C.RESET


# Convenience helpers
def ok(s):    return colorize(s, C.BRIGHT_GREEN)
def warn(s):  return colorize(s, C.BRIGHT_YELLOW)
def err(s):   return colorize(s, C.BRIGHT_RED)
def info(s):  return colorize(s, C.BRIGHT_CYAN)
def dim(s):   return colorize(s, C.GRAY)
def bold(s):  return colorize(s, C.BOLD)
def accent(s):return colorize(s, C.BRIGHT_MAGENTA, C.BOLD)


ANSI_RE = re.compile(r"\033\[[0-9;]*m")

def visible_len(s):
    return len(ANSI_RE.sub("", s))

def pad_visible(s, width, align="left"):
    v = visible_len(s)
    p = max(width - v, 0)
    if align == "left":
        return s + " " * p
    if align == "right":
        return " " * p + s
    left = p // 2
    return " " * left + s + " " * (p - left)

def truncate_visible(s, width):
    out, vis, i = [], 0, 0
    while i < len(s) and vis < width:
        m = ANSI_RE.match(s, i)
        if m:
            out.append(m.group(0))
            i = m.end()
        else:
            out.append(s[i])
            vis += 1
            i += 1
    return "".join(out) + (C.RESET if USE_COLOR else "")


# ================== ANIMATION ==================

def typewrite(text, delay=0.005, end="\n"):
    """Prints text character by character with a small delay."""
    if not ANIMATE:
        print(text + end.rstrip("\n"))
        return
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(end)
    sys.stdout.flush()

def print_lines_animated(lines, delay=0.015):
    """Prints a list of lines one by one with a small delay."""
    if not ANIMATE:
        for line in lines:
            print(line)
        return
    for line in lines:
        print(line)
        sys.stdout.flush()
        time.sleep(delay)


# ================== TERMINAL ==================

def get_width():
    """
    Retrieves the current terminal column width dynamically.
    """
    return shutil.get_terminal_size((120, 30)).columns

def clear():
    """
    Clears the terminal screen securely depending on the OS platform.
    """
    os.system("cls" if os.name == "nt" else "clear")


# ================== UI ==================

def banner():
    """
    Renders the stylized ASCII Art banner centered on the terminal screen.
    """
    raw_art = [
r"                                                                                                        ",
r"$$$$$$\           $$\      $$\           $$$$$$$\                      $$\  $$$$$$\             $$$$$$\ ",
r"\_$$  _|          $$$\    $$$ |          $$  __$$\                     $$ |$$  __$$\           $$  __$$\ ",
r"  $$ |   $$$$$$$\ $$$$\  $$$$ |$$\   $$\ $$ |  $$ |$$\  $$\  $$\  $$$$$$$ |$$ /  \__| $$$$$$\  $$ /  \__|$$$$$$\ ",
r"  $$ |  $$  _____|$$\$$\$$ $$ |$$ |  $$ |$$$$$$$  |$$ | $$ | $$ |$$  __$$ |\$$$$$$\   \____$$\ $$$$\    $$  __$$\ ",
r"  $$ |  \$$$$$$\  $$ \$$$  $$ |$$ |  $$ |$$  ____/ $$ | $$ | $$ |$$ /  $$ | \____$$\  $$$$$$$ |$$  _|   $$$$$$$$ |",
r"  $$ |   \____$$\ $$ |\$  /$$ |$$ |  $$ |$$ |      $$ | $$ | $$ |$$ |  $$ |$$\   $$ |$$  __$$ |$$ |     $$   ____|",
r"$$$$$$\ $$$$$$$  |$$ | \_/ $$ |\$$$$$$$ |$$ |      \$$$$$\$$$$  |\$$$$$$$ |\$$$$$$  |\$$$$$$$ |$$ |     \$$$$$$$\ ",
r"\______|\_______/ \__|     \__| \____$$ |\__|       \_____\____/  \_______| \______/  \_______|\__|      \_______|",
r"                               $$\   $$ |",
r"                               \$$$$$$  |",
r"                                \______/",
    ]

    art = [line.replace('\xa0', ' ') for line in raw_art]

    clear()
    width = get_width()
    
    max_art_width = max(len(line) for line in art)
    block_pad = max((width - max_art_width) // 2, 0)

    for line in art:
        print(" " * block_pad + colorize(line, C.BRIGHT_CYAN, C.BOLD))
    
    subtitle = "IsMyPwdSafe Engine -> The only password audit that doesn't spy on you."
    pad_sub = max((width - len(subtitle)) // 2, 0)
    
    credits = "Made by Robert Gabriel Friciu"
    pad_cred = max((width - len(credits)) // 2, 0)

    print()
    
    if ANIMATE:
        sys.stdout.write(" " * pad_sub)
        typewrite(colorize(subtitle, C.BRIGHT_MAGENTA, C.ITALIC), delay=0.005)
        
        sys.stdout.write(" " * pad_cred)
        typewrite(colorize(credits, C.GRAY), delay=0.005)
        print()
    else:
        print(" " * pad_sub + colorize(subtitle, C.BRIGHT_MAGENTA, C.ITALIC))
        print(" " * pad_cred + colorize(credits, C.GRAY) + "\n")

def make_box(title, lines, width, title_color=None):
    """
    Generates a structured box layout using Unicode box-drawing characters.
    """
    box = []
    box.append("╔" + "═"*(width-2) + "╗")
    
    tc = title_color if title_color is not None else C.BRIGHT_WHITE
    inner = (width - 2 - len(title)) // 2
    right_pad = (width - 2 - len(title)) - inner
    
    colored_title = (
        " " * inner +
        colorize(title, tc, C.BOLD) +
        " " * right_pad
    )
    box.append("║" + colored_title + "║")
    box.append("╠" + "═"*(width-2) + "╣")
    
    for line in lines:
        padded = pad_visible(line, width-4)
        padded = truncate_visible(padded, width-4)
        box.append("║ " + padded + " ║")
        
    box.append("╚" + "═"*(width-2) + "╝")
    return box

def merge_boxes(left, right, width):
    """
    Prints two independent box objects side-by-side balanced inside the viewport.
    """
    col = width // 2
    left = list(left)
    right = list(right)
    max_rows = max(len(left), len(right))
    left  += ["║" + " "*(col-2) + " ║"] * (max_rows - len(left))
    right += ["║" + " "*(col-2) + " ║"] * (max_rows - len(right))
    for l, r in zip(left, right):
        print(pad_visible(truncate_visible(l, col), col) + pad_visible(truncate_visible(r, col), col))
        if ANIMATE:
            sys.stdout.flush()
            time.sleep(0.012)

def progress_bar(value, max_value, width, colored=False):
    """
    Generates a visual text-based loading bar indicator.
    """
    if max_value == 0 or width <= 0:
        return "░" * max(width, 0)
    ratio = min(max(value / max_value, 0), 1)
    filled = int(ratio * width)
    bar_filled = "█"*filled
    bar_empty  = "░"*(width-filled)
    
    if not colored or not USE_COLOR:
        return bar_filled + bar_empty
        
    if ratio < 0.35:
        col = C.BRIGHT_RED
    elif ratio < 0.65:
        col = C.BRIGHT_YELLOW
    else:
        col = C.BRIGHT_GREEN
    return col + bar_filled + C.RESET + C.GRAY + bar_empty + C.RESET


# ================== PASSWORD EXAMPLES ==================

def format_time(time_seconds):
    """
    Formats seconds into a human-readable string, max 9 chars.
    """
    if time_seconds < 1:
        return "Instant"
    if time_seconds < 60:
        return f"{time_seconds:.1f} s"
    if time_seconds < 3600:
        return f"{time_seconds/60:.1f} min"
    if time_seconds < 86400:
        return f"{time_seconds/3600:.1f} hrs"
    
    years = time_seconds / 31536000
    
    if years < 1000:
        return f"{years:.1f} y"
    
    return "1000+ y"


# ================== OUTPUT ==================

def print_output(result, password, mask_mode=False, view="full"):
    """
    Render an AuditResult.

    view: "full" | "short" | "darkweb".
    """
    width = get_width()
    col_w = width // 2

    if result.error:
        print(err("[!] " + result.error))
        return

    show_full    = view == "full"
    show_darkweb = view in ("full", "darkweb")
    show_overall = view in ("full", "short")

    if show_full:
        banner()

        L = result.input.length
        charset = result.input.charset_size
        comb_str = (
            "{:,}".format(result.entropy.combinations)
            if result.entropy.combinations is not None
            else "10^{:.2f}".format(result.entropy.log10_value)
        )
        display_pwd = "*" * L if mask_mode else password

        pwd_label = colorize("Password: ", C.GRAY)
        pwd_value = colorize(display_pwd, C.BRIGHT_WHITE, C.BOLD)
        len_label = colorize("Length: ", C.GRAY)
        len_value = colorize(str(L), C.BRIGHT_WHITE, C.BOLD)
        cs_label  = colorize("Total Charset: ", C.GRAY)
        cs_value  = colorize(str(charset), C.BRIGHT_WHITE, C.BOLD)

        input_box = make_box("INPUT METRICS", [
            "{}{}  │  {}{} characters  │  {}{} options".format(
                pwd_label, pwd_value, len_label, len_value, cs_label, cs_value)
        ], width)
        print_lines_animated(input_box, delay=0.015)
        print()

        status_low = ok("[✔] Present") if result.input.has_lowercase else err("[✘] Missing")
        status_upp = ok("[✔] Present") if result.input.has_uppercase else err("[✘] Missing")
        status_num = ok("[✔] Present") if result.input.has_digits    else err("[✘] Missing")
        status_sym = ok("[✔] Present") if result.input.has_symbols   else err("[✘] Missing")

        in_top150 = result.pattern.detected and result.pattern.rule == "top150"
        status_top150 = err("[✘] Found") if in_top150 else ok("[✔] Clean")

        search_lines = [
            "Combinations : {}".format(colorize(comb_str, C.BRIGHT_WHITE, C.BOLD)),
            "Lowercase a-z: {}".format(status_low),
            "Uppercase A-Z: {}".format(status_upp),
            "Digits 0-9   : {}".format(status_num),
            "Symbols !@#$ : {}".format(status_sym),
            "Top 150 List : {}".format(status_top150),
        ]
        if result.pattern.detected:
            search_lines.append("Pattern Risk : " + warn("[!] " + result.pattern.detail))
        else:
            search_lines.append("Pattern Risk : " + ok("[+] No structural patterns found"))

        box_search = make_box("SEARCH SPACE & STRUCTURAL ANALYSIS", search_lines, col_w)

        graph_lines = []
        for hw in result.hardware:
            time_str = format_time(hw.seconds)
            bar_value = math.log10(hw.seconds) if hw.seconds > 0 else 0
            bar = progress_bar(bar_value, 12, col_w - 36)
            graph_lines.append(
                "{} [{}] {}".format(
                    colorize("{:<14}".format(hw.label), C.GRAY),
                    colorize(bar, C.WHITE),
                    colorize(time_str, C.BRIGHT_WHITE),
                )
            )

        if result.pattern.detected:
            graph_lines.append("")
            disclaimer_text = (
                "[!] The presence of known patterns makes cracking this password "
                "significantly faster than brute-force estimates. "
                "(in the scale of milliseconds to seconds)"
            )
            for line in textwrap.wrap(disclaimer_text, width=col_w - 4):
                graph_lines.append(warn(line))

        while len(graph_lines) < len(search_lines):
            graph_lines.append("")

        box_hardware = make_box("RESISTANCE BY HARDWARE", graph_lines, col_w)
        merge_boxes(box_search, box_hardware, width)
        print()

    if show_darkweb:
        b = result.breach
        if b.reason == "offline":
            risk_status = warn("[!] OFFLINE MODE: BREACH CHECK SKIPPED")
            risk_details = dim("Run without -o/--offline to check this password against the HIBP breach database.")
        elif b.reason == "disabled":
            risk_status = warn("[!] BREACH CHECK DISABLED (--no-breach-check)")
            risk_details = dim("The HIBP request was skipped on request. Run without --no-breach-check to enable it.")
        elif b.reason == "api_error":
            risk_status = warn("[x] AN ERROR OCCURRED WHILE CHECKING DARK WEB DATABASES")
            risk_details = dim("The HIBP API is unreachable. The audit was computed without the breach cap.")
        elif b.pwned:
            risk_status = colorize(
                "[!] CRITICAL ALERT: CREDENTIAL EXPOSED IN DARK WEB DATABASE LEAKS!",
                C.BRIGHT_RED, C.BOLD,
            )
            risk_details = colorize(
                "This exact password was found leaked {:,} times online. Hackers already know it.".format(b.count),
                C.BRIGHT_RED,
            )
        else:
            risk_status = ok("[+] DATABASE CLEAN: NO MATCHES FOUND")
            risk_details = ok("Good news. This password asset does not appear in any known public data breaches.")

        darkweb_box = make_box("DARKWEB SCANNER", [risk_status, risk_details],
                               width, title_color=C.BRIGHT_MAGENTA)
        if show_full:
            print_lines_animated(darkweb_box, delay=0.02)
        else:
            print("\n".join(darkweb_box))
        print()

    if show_overall:
        s = result.score
        lvl = s.rating.upper()
        score = s.value
        lvl_color = {
            "WEAK":   C.BRIGHT_RED,
            "MEDIUM": C.BRIGHT_YELLOW,
            "STRONG": C.BRIGHT_GREEN,
        }[lvl]

        lvl_fill = score / 100.0
        lvl_colored = colorize("{} {}/100".format(lvl, score), lvl_color, C.BOLD)

        if ANIMATE and show_full:
            bar_width = width - 38
            target_fill = int(bar_width * lvl_fill)

            print("╔" + "═" * (width - 2) + "╗")
            title = "OVERALL SECURITY ASSESSMENT"
            inner = (width - 2 - len(title)) // 2
            right_pad = (width - 2 - len(title)) - inner
            colored_title = " " * inner + colorize(title, C.BRIGHT_WHITE, C.BOLD) + " " * right_pad
            print("║" + colored_title + "║")
            print("╠" + "═" * (width - 2) + "╣")

            for f in range(0, target_fill + 1, max(1, target_fill // 30)):
                bar = lvl_color + "█" * f + C.RESET + C.GRAY + "░" * (bar_width - f) + C.RESET
                sys.stdout.write("\r║ [{}] {} {}".format(
                    bar, lvl_colored, " " * (width - 6 - bar_width - len(lvl) - 8)))
                sys.stdout.flush()
                time.sleep(0.008)
            bar = lvl_color + "█" * target_fill + C.RESET + C.GRAY + "░" * (bar_width - target_fill) + C.RESET
            sys.stdout.write("\r║ [{}] {} {}".format(
                bar, lvl_colored, " " * (width - 6 - bar_width - len(lvl) - 8)))
            sys.stdout.flush()
            print("\n╚" + "═" * (width - 2) + "╝")
        else:
            bar_width = width - 38
            filled = int(bar_width * lvl_fill)
            bar = lvl_color + "█" * filled + C.RESET + C.GRAY + "░" * (bar_width - filled) + C.RESET
            for line in make_box("OVERALL SECURITY ASSESSMENT",
                                 ["[{}] {}".format(bar, lvl_colored)], width):
                print(line)


# ================== MAIN EXECUTION ==================

def main():
    # Enforce standard POSIX/Unix CLI syntax formatting guidelines
    parser = argparse.ArgumentParser(
        description="IsMyPwdSafe CLI Engine - The only password tester that doesn't spy on you.",
        usage="imps [-M] [-o | --no-breach-check] [-s | -dw] <password>",
        add_help=True
    )
    
    # Boolean Privacy Mask Option (Optional, defined before the argument)
    parser.add_argument(
        "-M", "--Mask", 
        action="store_true", 
        help="Completely mask the input password with asterisks in the summary screen box"
    )

    # Offline mode: skip every outbound request (HIBP + GitHub)
    parser.add_argument(
        "-o", "--offline",
        action="store_true",
        help="Disable all network requests. Implies --no-breach-check and --no-update-check"
    )

    # Granular: skip only the HIBP lookup, keep the GitHub update check
    parser.add_argument(
        "--no-breach-check",
        action="store_true",
        help="Skip the HaveIBeenPwned breach lookup, keep the GitHub update check"
    )

    # Granular: skip only the GitHub update check
    parser.add_argument(
        "--no-update-check",
        action="store_true",
        help="Disable the remote update check on startup (implied by --offline)"
    )

    # View modes: mutually exclusive, each renders a single section of the report
    view_group = parser.add_mutually_exclusive_group()
    view_group.add_argument(
        "-s", "--short",
        action="store_true",
        help="Display only the overall security assessment"
    )
    view_group.add_argument(
        "-dw", "--darkweb",
        action="store_true",
        help="Display only the dark web breach check"
    )
    
    # Target Positional Data Input (Required, parsed at the end)
    parser.add_argument(
        "password", 
        type=str, 
        nargs="?", 
        help="The raw text password string to submit for auditing"
    )

    args = parser.parse_args()
    password = args.password

    if args.short:
        view = "short"
    elif args.darkweb:
        view = "darkweb"
    else:
        view = "full"

    skip_breach = args.offline or args.no_breach_check
    skip_update = args.offline or args.no_update_check

    if not password:
        try:
            password = getpass.getpass(prompt="Enter password to audit: ")
        except Exception as e:
            print(err("[!] Error reading password: {}".format(e)))
            return 65
        if not password:
            print(warn("[!] No password provided."))
            return 65

    if not skip_update and view == "full":
        new_ver = network.check_for_updates(__version__)
        if new_ver:
            width = get_width()
            msg = "[!] A new version of IsMyPwdSafe is available: v{} (you have v{})".format(new_ver, __version__)
            print(warn(msg.center(width)))
            print(dim("    Update now: https://github.com/Roma476/IsMyPwdSafe/releases/latest".center(width) + "\n"))

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

    print_output(result, password, mask_mode=args.Mask, view=view)
    return result.exit_code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n" + warn("[!] Audit interrupted by user."))
        sys.exit(130)