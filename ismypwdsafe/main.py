import sys
import math
import shutil
import os
import argparse
import re
import time
import textwrap
import getpass

from . import patterns
from . import network

__version__ = "1.2.0"


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


# ================== CORE LOGIC ==================

def must_use_log(C, L):
    """
    Determines whether to switch to logarithmic calculations 
    to prevent integer overflow when processing large combinations.
    """
    if C > 95:
        return L >= 3
    if C in (62, 63):
        return L >= 5
    return L >= 4

def calc_charset(password):
    """
    Calculates the potential character set size and returns individual flags.
    """
    number = lower = upper = symbol = False
    total = 0
    for char in password:
        if char.isdigit() and not number:
            number = True
            total += 10
        elif char.islower() and not lower:
            lower = True
            total += 26
        elif char.isupper() and not upper:
            upper = True
            total += 26
        elif not char.isalnum() and ord(char) < 128 and not symbol:
            symbol = True
            total += 33
            
    return total, lower, upper, number, symbol

def calc_combinations(C, L):
    """
    Computes total possible key combinations and the log10 equivalent value.
    """
    log10_value = L * math.log10(C) if C > 0 else 0
    if must_use_log(C, L):
        return None, log10_value
    else:
        return C ** L, log10_value


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

def suggestions(password):
    """
    Generates alternative variants to strengthen the input password.
    """
    if not password:
        return ["(no password provided)"]
    examples = []
    base = password
    examples.append(f"{base} → {base}123!")
    examples.append(f"{base} → {base.capitalize()}=")
    leet = base.replace('a','@').replace('o','0').replace('e','3').replace('i','1')
    examples.append(f"{base} → {leet}")
    examples.append(f"{base} → {base}_hf3f?")
    if len(base) >= 4:
        examples.append(f"{base} → {base[:3]}!{base[3:]}99#")
    else:
        examples.append(f"{base} → {base}!99#$")
    return examples[:4]

def calculate_score(log10_value, pattern_warning, pwned_count):
    """
    Computes a 0-100 security score combining entropy, patterns, and breach history.
    """
    base_score = int(min(100, max(0, log10_value * 5)))
    
    if pattern_warning:
        base_score = min(base_score, 30)
        
    if isinstance(pwned_count, int) and pwned_count > 0:
        base_score = min(base_score, 10)
        
    return base_score

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

def strength(log10_value, pattern_warning):
    """
    Translates mathematical entropy into human-readable assessment rankings.
    """
    if pattern_warning or log10_value < 10:
        return "WEAK"
    elif log10_value < 14:
        return "MEDIUM"
    return "STRONG"


# ================== OUTPUT ==================

def print_output(password, charset, L, combinations, log10_value,
                 has_low, has_upp, has_num, has_sym,
                 mask_mode=False, view="full", offline=False,
                 no_breach_check=False):
    """
    Renders the audit report.

    view can be:
      - "full"    : banner, input metrics, search/hardware, darkweb, overall
      - "short"   : overall assessment only
      - "darkweb" : darkweb scanner only

    offline=True skips every outbound request (HIBP and GitHub).
    no_breach_check=True skips only the HIBP lookup, leaving the GitHub
    update check active. Both flags leave pwned_count as None, so the
    overall score is computed without the breach cap.
    """
    width = get_width()
    col_w = width // 2

    pwned_count = None
    if not offline and not no_breach_check:
        pwned_count = network.check_pwned(password)
    pattern_warning = patterns.check_patterns(password)

    show_full    = view == "full"
    show_darkweb = view in ("full", "darkweb")
    show_overall = view in ("full", "short")

    if show_full:
        banner()

        comb_str = f"{combinations:,}" if combinations else f"10^{log10_value:.2f}"
        display_pwd = "*" * L if mask_mode else password

        # ===== 1. TOP ROW: INPUT STATUS =====
        pwd_label = colorize("Password: ", C.GRAY)
        pwd_value = colorize(display_pwd, C.BRIGHT_WHITE, C.BOLD)
        len_label = colorize("Length: ", C.GRAY)
        len_value = colorize(f"{L}", C.BRIGHT_WHITE, C.BOLD)
        cs_label  = colorize("Total Charset: ", C.GRAY)
        cs_value  = colorize(f"{charset}", C.BRIGHT_WHITE, C.BOLD)

        input_box = make_box("INPUT METRICS", [
            f"{pwd_label}{pwd_value}  │  {len_label}{len_value} characters  │  {cs_label}{cs_value} options"
        ], width)
        
        print_lines_animated(input_box, delay=0.015)
        print()

        status_low = ok("[✔] Present") if has_low else err("[✘] Missing")
        status_upp = ok("[✔] Present") if has_upp else err("[✘] Missing")
        status_num = ok("[✔] Present") if has_num else err("[✘] Missing")
        status_sym = ok("[✔] Present") if has_sym else err("[✘] Missing")

        # Check top 150 match specifically for the checkbox status
        norm_pwd = patterns.normalize_leetspeak(password)
        is_in_top150 = any(item in password.lower() or item in norm_pwd for item in patterns.get_top150_set())
        status_top150 = err("[✘] Found") if is_in_top150 else ok("[✔] Clean")

        search_lines = [
            f"Combinations : {colorize(comb_str, C.BRIGHT_WHITE, C.BOLD)}",
            f"Lowercase a-z: {status_low}",
            f"Uppercase A-Z: {status_upp}",
            f"Digits 0-9   : {status_num}",
            f"Symbols !@#$ : {status_sym}",
            f"Top 150 List : {status_top150}",
        ]
        
        if pattern_warning:
            search_lines.append("Pattern Risk : " + warn("[!] " + pattern_warning))
        else:
            search_lines.append("Pattern Risk : " + ok("[+] No structural patterns found"))

        # Box Left: SEARCH SPACE & STRUCTURAL ANALYSIS
        box_search = make_box("SEARCH SPACE & STRUCTURAL ANALYSIS", search_lines, col_w)

        # Box Right: Hardware Resistance Graph
        speeds = [("PC (1K/s)", 1e3), ("Server (1M/s)", 1e6), ("GPU Rig (1B/s)", 1e9), ("Cluster (1T/s)", 1e12)]
        graph_lines = []
        
        for label, aps in speeds:
            time_seconds = (10**log10_value) / aps
            time_str = format_time(time_seconds)
            bar_value = math.log10(time_seconds) if time_seconds > 0 else 0
                
            bar = progress_bar(bar_value, 12, col_w-36)
            graph_lines.append(f"{colorize(f'{label:<14}', C.GRAY)} [{colorize(bar, C.WHITE)}] {colorize(time_str, C.BRIGHT_WHITE)}")
            
        if pattern_warning:
            graph_lines.append("")
            disclaimer_text = "[!] The presence of known patterns makes cracking this password significantly faster than brute-force estimates. (in the scale of milliseconds to seconds)"
            wrapped_lines = textwrap.wrap(disclaimer_text, width=col_w-4)
            for line in wrapped_lines:
                graph_lines.append(warn(line))
            
        while len(graph_lines) < len(search_lines):
            graph_lines.append("")

        box_hardware = make_box("RESISTANCE BY HARDWARE", graph_lines, col_w)

        merge_boxes(box_search, box_hardware, width)
        print()

    if show_darkweb:
        if offline:
            risk_status = warn("[!] OFFLINE MODE: BREACH CHECK SKIPPED")
            risk_details = dim("Run without -o/--offline to check this password against the HIBP breach database.")
        elif no_breach_check:
            risk_status = warn("[!] BREACH CHECK DISABLED (--no-breach-check)")
            risk_details = dim("The HIBP request was skipped on request. Run without --no-breach-check to enable it.")
        elif isinstance(pwned_count, int):
            if pwned_count > 0:
                risk_status = colorize("[!] CRITICAL ALERT: CREDENTIAL EXPOSED IN DARK WEB DATABASE LEAKS!", C.BRIGHT_RED, C.BOLD)
                risk_details = colorize(f"This exact password was found leaked {pwned_count:,} times online. Hackers already know it.", C.BRIGHT_RED)
            else:
                risk_status = ok("[+] DATABASE CLEAN: NO MATCHES FOUND")
                risk_details = ok("Good news. This password asset does not appear in any known public data breaches.")
        else:
            risk_status = warn("[x] AN ERROR OCCURRED WHILE CHECKING DARK WEB DATABASES")
            risk_details = dim(f"API Telemetry State: {pwned_count}")

        darkweb_box = make_box("DARKWEB SCANNER", [
            risk_status,
            risk_details
        ], width, title_color=C.BRIGHT_MAGENTA)

        if show_full:
            print_lines_animated(darkweb_box, delay=0.02)
        else:
            print("\n".join(darkweb_box))
        print()

    if show_overall:
        lvl = strength(log10_value, pattern_warning)
        score = calculate_score(log10_value, pattern_warning, pwned_count)

        lvl_color = {
            "WEAK":   C.BRIGHT_RED,
            "MEDIUM": C.BRIGHT_YELLOW,
            "STRONG": C.BRIGHT_GREEN,
        }[lvl]

        lvl_fill = score / 100.0
        lvl_colored = colorize(f"{lvl} {score}/100", lvl_color, C.BOLD)

        if ANIMATE and show_full:
            bar_width = width - 38
            target_fill = int(bar_width * lvl_fill)

            print("╔" + "═"*(width-2) + "╗")
            title = "OVERALL SECURITY ASSESSMENT"
            inner = (width - 2 - len(title)) // 2
            right_pad = (width - 2 - len(title)) - inner
            colored_title = " " * inner + colorize(title, C.BRIGHT_WHITE, C.BOLD) + " " * right_pad
            print("║" + colored_title + "║")
            print("╠" + "═"*(width-2) + "╣")

            for f in range(0, target_fill + 1, max(1, target_fill // 30)):
                bar = lvl_color + "█" * f + C.RESET + C.GRAY + "░" * (bar_width - f) + C.RESET
                sys.stdout.write("\r║ [{}] {} {}".format(bar, lvl_colored, " " * (width - 6 - bar_width - len(lvl) - 8)))
                sys.stdout.flush()
                time.sleep(0.008)
            bar = lvl_color + "█" * target_fill + C.RESET + C.GRAY + "░" * (bar_width - target_fill) + C.RESET
            sys.stdout.write("\r║ [{}] {} {}".format(bar, lvl_colored, " " * (width - 6 - bar_width - len(lvl) - 8)))
            sys.stdout.flush()
            print("\n╚" + "═"*(width-2) + "╝")
        else:
            bar_width = width - 38
            filled = int(bar_width * lvl_fill)
            bar = lvl_color + "█" * filled + C.RESET + C.GRAY + "░" * (bar_width - filled) + C.RESET
            sec = make_box("OVERALL SECURITY ASSESSMENT", [
                f"[{bar}] {lvl_colored}"
            ], width)
            for line in sec:
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

    # --offline implies both granular skips
    skip_breach = args.offline or args.no_breach_check
    skip_update = args.offline or args.no_update_check

    # Catch empty constraints inputs and prompt for password securely if not provided
    if not args.password:
        try:
            password = getpass.getpass(prompt="Enter password to audit: ")
        except Exception as e:
            print(err(f"[!] Error reading password: {e}"))
            return

        if not password:
            print(warn("[!] No password provided."))
            return

    # Update Checker (safe, silent, timeouts after 1.5s).
    # Skipped for non-full views (scriptable output) and when requested.
    if not skip_update and view == "full":
        new_ver = network.check_for_updates(__version__)
        if new_ver:
            width = get_width()
            msg = f"[!] A new version of IsMyPwdSafe is available: v{new_ver} (you have v{__version__})"
            print(warn(msg.center(width)))
            print(dim("    Update now: https://github.com/Roma476/IsMyPwdSafe/releases/latest".center(width) + "\n"))

    C, has_low, has_upp, has_num, has_sym = calc_charset(password)
    
    if C == 0:
        print("[!] Could not determine charset.")
        return
        
    L = len(password)
    combinations, log10_value = calc_combinations(C, L)

    # Pass computed values to the output renderer
    print_output(password, C, L, combinations, log10_value,
                 has_low, has_upp, has_num, has_sym,
                 mask_mode=args.Mask, view=view,
                 offline=args.offline, no_breach_check=args.no_breach_check)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n" + warn("[!] Audit interrupted by user."))
        sys.exit(130) # Exit code 130 for SIGINT (Ctrl+C)