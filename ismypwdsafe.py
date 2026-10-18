import sys
import math
import shutil
import os
import argparse

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
    Calculates the potential character set (search space) size.
    Fixed to properly handle symbols and prevent false positives with Unicode characters.
    """
    number = lower = upper = symbol = False
    total = 0
    for char in password:
        # Enforce standard ASCII range checks to prevent bugs with accented letters
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
    return total


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
    art = [
r"$$$$$$\           $$\      $$\           $$$$$$$\                      $$\  $$$$$$\             $$$$$$\\",
r"\_$$  _|          $$$\    $$$ |          $$  __$$\                     $$ |$$  __$$\           $$  __$$\\",
r"  $$ |   $$$$$$$\ $$$$\  $$$$ |$$\   $$\ $$ |  $$ |$$\  $$\  $$\  $$$$$$$ |$$ /  \__| $$$$$$\  $$ /  \__|$$$$$$\\",
r"  $$ |  $$  _____|$$\$$\$$ $$ |$$ |  $$ |$$$$$$$  |$$ | $$ | $$ |$$  __$$ |\$$$$$$\   \____$$\ $$$$\    $$  __$$\\",
r"  $$ |  \$$$$$$\  $$ \$$$  $$ |$$ |  $$ |$$  ____/ $$ | $$ | $$ |$$ /  $$ | \____$$\  $$$$$$$ |$$  _|   $$$$$$$$ |",
r"  $$ |   \____$$\ $$ |\$  /$$ |$$ |  $$ |$$ |      $$ | $$ | $$ |$$ |  $$ |$$\   $$ |$$  __$$ |$$ |     $$   ____|",
r"$$$$$$\ $$$$$$$  |$$ | \_/ $$ |\$$$$$$$ |$$ |      \$$$$$\$$$$  |\$$$$$$$ |\$$$$$$  |\$$$$$$$ |$$ |     \$$$$$$$\\",
r"\______|\_______/ \__|     \__| \____$$ |\__|       \_____\____/  \_______| \______/  \_______|\__|      \_______|",
r"                               $$\   $$ |",
r"                               \$$$$$$  |",
r"                                \______/",
    ]
    clear()
    width = get_width()
    for line in art:
        pad = max((width - len(line)) // 2, 0)
        print(" " * pad + line)
    
    subtitle = "IsMyPwdSafe Engine -> The only password audit that doesn't spy on you."
    pad_sub = max((width - len(subtitle)) // 2, 0)
    print("\n" + " " * pad_sub + subtitle)
    
    credits = "Made by Robert Gabriel Friciu"
    pad_cred = max((width - len(credits)) // 2, 0)
    print(" " * pad_cred + credits + "\n")


def make_box(title, lines, width):
    """
    Generates a structured box layout using Unicode box-drawing characters.
    """
    box = []
    box.append("╔" + "═"*(width-2) + "╗")
    box.append("║" + title.center(width-2) + "║")
    box.append("╠" + "═"*(width-2) + "╣")
    for line in lines:
        box.append("║ " + line.ljust(width-4)[:width-4] + " ║")
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
        print(l[:col].ljust(col) + r[:col].ljust(col))


def progress_bar(value, max_value, width):
    """
    Generates a visual text-based loading bar indicator.
    """
    if max_value == 0 or width <= 0:
        return "░" * max(width, 0)
    ratio = min(max(value / max_value, 0), 1)
    filled = int(ratio * width)
    return "█"*filled + "░"*(width-filled)


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
    examples.append(f"{base} → {base.capitalize()}!")
    leet = base.replace('a','@').replace('o','0').replace('e','3').replace('i','1')
    examples.append(f"{base} → {leet}")
    examples.append(f"{base} → {base}_Secure2026!")
    if len(base) >= 4:
        examples.append(f"{base} → {base[:3]}!{base[3:]}99#")
    else:
        examples.append(f"{base} → {base}!99#$")
    return examples[:5]

def strength(log10_value):
    """
    Translates mathematical entropy into human-readable assessment rankings.
    """
    if log10_value < 10:
        return "WEAK"
    elif log10_value < 14:
        return "MEDIUM"
    return "STRONG"


# ================== OUTPUT ==================

def print_output(password, C, L, combinations, log10_value, mask_mode=False):
    """
    Renders the complete audit assessment report interface layout.
    """
    banner()
    width = get_width()
    col_w = width // 2

    comb_str = f"{combinations:,}" if combinations else f"10^{log10_value:.2f}"

    # Conditional Privacy Logic based on user CLI flag setting
    if mask_mode:
        display_pwd = "*" * L
    else:
        display_pwd = password  # Default show 

    # ===== TOP ROW =====
    box1 = make_box("INPUT STATUS", [
        f"Password : {display_pwd}",
        f"Length   : {L}",
        f"Charset  : {C}",
    ], col_w)

    box2 = make_box("SEARCH SPACE", [
        f"Combinations : {comb_str}",
        f"log10        : {log10_value:.2f}",
        "",
        "Entropy: " + progress_bar(log10_value, 20, col_w-19)
    ], col_w)

    merge_boxes(box1, box2, width)
    print()

    # ===== SPEED GRAPH (COMPUTATIONAL RESISTANCE) =====
    speeds = [("PC (1K/s)", 1e3), ("Server (1M/s)", 1e6), ("GPU Rig (1B/s)", 1e9), ("Cluster (1T/s)", 1e12)]
    graph_lines = []
    
    for label, aps in speeds:
        time_seconds = (10**log10_value) / aps
        
        # User-friendly relative time parsing representation
        if time_seconds < 1:
            time_str = "Instant"
        elif time_seconds < 3600:
            time_str = f"{time_seconds/60:.1f} min"
        elif time_seconds < 86400:
            time_str = f"{time_seconds/3600:.1f} hours"
        elif time_seconds < 31536000:
            time_str = f"{time_seconds/86400:.1f} days"
        else:
            time_str = f"{time_seconds/31536000:.1e} years"
            
        log_t = math.log10(max(time_seconds, 1e-5))
        bar = progress_bar(log_t + 5, 20, col_w-32)
        graph_lines.append(f"{label:<14} [{bar}] {time_str}")

    box3 = make_box("RESISTANCE BY HARDWARE", graph_lines, col_w)

    # ===== PASSWORD IMPROVEMENTS =====
    tips = list(suggestions(password))
    while len(tips) < len(graph_lines):
        tips.append("")
    box4 = make_box("PASSWORD IMPROVEMENTS", tips, col_w)

    merge_boxes(box3, box4, width)
    print()

    # ===== GLOBAL SECURITY SUMMARY =====
    lvl = strength(log10_value)
    sec = make_box("SECURITY LEVEL ASSESSMENT", [
        f"[{progress_bar(log10_value, 16, width-38)}] {lvl}"
    ], width)
    for line in sec:
        print(line)


# ================== MAIN EXECUTION ==================

def main():
    # Enforce standard POSIX/Unix CLI syntax formatting guidelines
    parser = argparse.ArgumentParser(
        description="IsMyPwdSafe CLI Engine - The only password tester that doesn't spy on you.",
        usage="imps [-M | --Mask] <password>",
        add_help=True
    )
    
    # Boolean Privacy Mask Option (Optional, defined before the argument)
    parser.add_argument(
        "-M", "--Mask", 
        action="store_true", 
        help="Completely mask the input password with asterisks in the summary screen box"
    )
    
    # Target Positional Data Input (Required, parsed at the end)
    parser.add_argument(
        "password", 
        type=str, 
        nargs="?", 
        help="The raw text password string to submit for auditing"
    )

    args = parser.parse_args()
    
    # Catch empty constraints inputs parameters gracefully and fallback to error manual screen
    if not args.password:
        print("Usage: imps [-M | --Mask] <password>")
        print("Run 'imps -h' or 'imps --help' for comprehensive instructions manual.")
        return

    password = args.password
    C = calc_charset(password)
    
    if C == 0:
        print("[!] Could not determine charset.")
        return
        
    L = len(password)
    combinations, log10_value = calc_combinations(C, L)
    
    # Push data variables matrix structures forward into formatting layout routines
    print_output(password, C, L, combinations, log10_value, mask_mode=args.Mask)


if __name__ == "__main__":
    main()
