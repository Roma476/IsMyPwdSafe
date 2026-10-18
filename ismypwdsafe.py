import sys
import math
import shutil
import os
import argparse
import hashlib
import requests


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

def hash_password(password):
    """
    Computes the SHA-1 hash of the input password for secure transmission.
    """
    sha1 = hashlib.sha1()
    sha1.update(password.encode('utf-8'))
    return sha1.hexdigest()

def check_pwned(password):
    prefix = hash_password(password)[:5].upper()
    suffix = hash_password(password)[5:].upper()

    url = f"https://api.pwnedpasswords.com/range/{prefix}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return "API request failed with status code: {}".format(response.status_code)

        lines = response.text.splitlines()
        for line in lines:
            server_suffix, count = line.split(':')
            if server_suffix == suffix:
                return int(count)
        return 0
    except Exception:
        return "You are offline or the API is unreachable. Cannot check if the password has been pwned."

def check_keyboard_spatial(password):
    """
    Real QWERTY keyboard coordinate modeling for spatial walk detection.
    Rows mapped as (row_index, col_index).
    """
    keyboard = {
        '1': (0, 0), '2': (0, 1), '3': (0, 2), '4': (0, 3), '5': (0, 4), '6': (0, 5), '7': (0, 6), '8': (0, 7), '9': (0, 8), '0': (0, 9),
        'q': (1, 0), 'w': (1, 1), 'e': (1, 2), 'r': (1, 3), 't': (1, 4), 'y': (1, 5), 'u': (1, 6), 'i': (1, 7), 'o': (1, 8), 'p': (1, 9),
        'a': (2, 0), 's': (2, 1), 'd': (2, 2), 'f': (2, 3), 'g': (2, 4), 'h': (2, 5), 'j': (2, 6), 'k': (2, 7), 'l': (2, 8),
        'z': (3, 0), 'x': (3, 1), 'c': (3, 2), 'v': (3, 3), 'b': (3, 4), 'n': (3, 5), 'm': (3, 6)
    }
    
    pwd_lower = password.lower()
    coords = [keyboard[c] for c in pwd_lower if c in keyboard]
    
    if len(coords) < 3:
        return False

    # Check if consecutive characters maintain a strict directional step (horizontal/diagonal/vertical)
    straight_walks = 0
    for i in range(len(coords) - 1):
        r1, c1 = coords[i]
        r2, c2 = coords[i+1]
        dr = abs(r2 - r1)
        dc = abs(c2 - c1)
        # Valid single step on a keyboard (horizontal, vertical, or diagonal)
        if (dr == 0 and dc == 1) or (dr == 1 and dc == 0) or (dr == 1 and dc == 1):
            straight_walks += 1
        else:
            straight_walks = 0
            
        if straight_walks >= 3:  # 4 or more keys in a direct geometric sequence
            return True
            
    return False

def get_top150_set():
    return {
        "123456", "12345678", "123456789", "admin", "12345", "Aa123456", "password",
        "123", "1234567890", "qwerty", "qwerty123", "Aa@123456", "1234567", "Password",
        "P@ssw0rd", "admin123", "111111", "Pass@123", "123123", "welcome", "1q2w3e4r",
        "abc123", "Admin@123", "iloveyou", "000000", "password1", "qwerty1", "Abcd@1234",
        "dragon", "monkey", "letmein", "1q2w3e4r5t", "qwertyuiop", "********", "secret",
        "password123", "football", "shadow", "sunshine", "princess", "master", "michael",
        "ashley", "charlie", "1qaz2wsx", "asdfghjkl", "zxcvbnm", "654321", "666666",
        "superman", "batman", "India@123", "trustno1", "hello", "love", "whatever",
        "donald", "liverpool", "arsenal", "chelsea", "jordan", "nicole", "taylor",
        "access", "thomas", "buster", "hockey", "hunter", "soccer", "ranger",
        "andrew", "harley", "tigger", "joshua", "starwars", "matthew", "george",
        "summer", "friday", "cheese", "cookie", "coffee", "pepper", "guitar",
        "chicken", "ginger", "maggie", "jessica", "jennifer", "amanda", "Robert",
        "daniel", "william", "maria", "veronica", "susana", "skibidi", "minecraft",
        "Minecraft", "fortnite", "roblox", "warcraft", "newmember", "newuser",
        "newpass", "temppass", "test", "test123", "guest", "root", "pass",
        "passw0rd", "Password1", "Password123", "eminem", "50cent", "metallica",
        "slipknot", "blink182", "spiderman", "hellokitty", "barbie", "mario",
        "joker", "thor", "elsa", "987654321", "147258369", "112233", "121212",
        "131313", "696969", "777777", "888888", "999999", "aaaaaa", "qqqqqq",
        "london", "manchester", "password!", "qwerty!", "123456!", "computer",
        "internet", "louvre", "diamond", "killer", "yankees", "lakers"
    }

def check_patterns(password):
    """
    Advanced pattern recognition engine:
    1. Exact match and containment check against the 150 most common passwords (with leet-speak normalization)
    2. QWERTY geometric spatial keyboard modeling
    3. Year range detection (1900 - 2050)
    4. Excessive character repetitions
    """
    if not password:
        return None

    leet_map = str.maketrans({
        '@': 'a', '4': 'a', '3': 'e', '0': 'o', '1': 'i', 
        '!': 'i', '$': 's', '5': 's', '7': 't', '8': 'b'
    })
    normalized = password.lower().translate(leet_map)

    top_150_passwords = get_top150_set()

    for item in top_150_passwords:
        if item in password.lower() or item in normalized:
            return f"Top 150 list match ('{item}')"

    if check_keyboard_spatial(password):
        return "Keyboard spatial walk detected (QWERTY layout)"

    for i in range(len(password) - 3):
        chunk = password[i:i+4]
        if chunk.isdigit():
            year = int(chunk)
            if 1900 <= year <= 2050:
                return f"Contains common year ({year})"

    pwd_lower = password.lower()
    for i in range(len(pwd_lower) - 2):
        if pwd_lower[i] == pwd_lower[i+1] == pwd_lower[i+2]:
            return "Excessive character repetition"

    return None


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
        print(" " * block_pad + line)
    
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
    examples.append(f"{base} → {base.capitalize()}=")
    leet = base.replace('a','@').replace('o','0').replace('e','3').replace('i','1')
    examples.append(f"{base} → {leet}")
    examples.append(f"{base} → {base}_hf3f?")
    if len(base) >= 4:
        examples.append(f"{base} → {base[:3]}!{base[3:]}99#")
    else:
        examples.append(f"{base} → {base}!99#$")
    return examples[:4]

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

def print_output(password, C, L, combinations, log10_value, has_low, has_upp, has_num, has_sym, mask_mode=False):
    banner()
    width = get_width()
    col_w = width // 2

    comb_str = f"{combinations:,}" if combinations else f"10^{log10_value:.2f}"
    display_pwd = "*" * L if mask_mode else password  

    pwned_count = check_pwned(password)
    pattern_warning = check_patterns(password)

    # ===== 1. TOP ROW: INPUT STATUS =====
    input_box = make_box("INPUT METRICS", [
        f"Password: {display_pwd}  │  Length: {L} characters  │  Total Charset: {C} options"
    ], width)
    
    for line in input_box:
        print(line)
    print()

    status_low = "[✔] Present" if has_low else "[✘] Missing"
    status_upp = "[✔] Present" if has_upp else "[✘] Missing"
    status_num = "[✔] Present" if has_num else "[✘] Missing"
    status_sym = "[✔] Present" if has_sym else "[✘] Missing"

    # Check top 150 match specifically for the checkbox status
    leet_map = str.maketrans({'@': 'a', '4': 'a', '3': 'e', '0': 'o', '1': 'i', '!': 'i', '$': 's', '5': 's', '7': 't', '8': 'b'})
    norm_pwd = password.lower().translate(leet_map)
    is_in_top150 = any(item in password.lower() or item in norm_pwd for item in get_top150_set())
    status_top150 = "[✘] Present" if is_in_top150 else "[✔] Clean"

    search_lines = [
        f"Combinations : {comb_str}",
        f"Lowercase a-z: {status_low}",
        f"Uppercase A-Z: {status_upp}",
        f"Digits 0-9   : {status_num}",
        f"Symbols !@#$ : {status_sym}",
        f"Top 150 List : {status_top150}",
    ]
    
    if pattern_warning:
        search_lines.append(f"Pattern Risk : [!] {pattern_warning}")
    else:
        search_lines.append(f"Pattern Risk : [+] No structural patterns found")

    # Box Left: SEARCH SPACE & STRUCTURAL ANALYSIS
    box_search = make_box("SEARCH SPACE & STRUCTURAL ANALYSIS", search_lines, col_w)

    # Box Right: Hardware Resistance Graph (Bilanciamo le righe interne per renderlo alto uguale al box di sinistra)
    speeds = [("PC (1K/s)", 1e3), ("Server (1M/s)", 1e6), ("GPU Rig (1B/s)", 1e9), ("Cluster (1T/s)", 1e12)]
    graph_lines = []
    for label, aps in speeds:
        time_seconds = (10**log10_value) / aps
        if time_seconds < 1:
            time_str = "Instant"
            bar_value = 0
        else:
            if time_seconds < 3600: time_str = f"{time_seconds/60:.1f} min"
            elif time_seconds < 86400: time_str = f"{time_seconds/3600:.1f} hours"
            elif time_seconds < 31536000: time_str = f"{time_seconds/86400:.1f} days"
            else: time_str = f"{time_seconds/31536000:.1e} years"
            bar_value = math.log10(time_seconds)
            
        bar = progress_bar(bar_value, 15, col_w-32)
        graph_lines.append(f"{label:<14} [{bar}] {time_str}")
        
    while len(graph_lines) < len(search_lines):
        graph_lines.append("")

    box_hardware = make_box("RESISTANCE BY HARDWARE", graph_lines, col_w)

    merge_boxes(box_search, box_hardware, width)
    print()

    if isinstance(pwned_count, int):
        if pwned_count > 0:
            risk_status = "[!] CRITICAL ALERT: CREDENTIAL EXPOSED IN DARK WEB DATABASE LEAKS!"
            risk_details = f"This exact password was found leaked {pwned_count:,} times online. Hackers already know it."
        else:
            risk_status = "[+] DATABASE CLEAN: NO MATCHES FOUND"
            risk_details = "Good news. This password asset does not appear in any known public data breaches."
    else:
        risk_status = "[x] AN ERROR OCCURRED WHILE CHECKING DARK WEB DATABASES"
        risk_details = f"API Telemetry State: {pwned_count}"

    darkweb_box = make_box("DARKWEB SCANNER", [
        risk_status,
        risk_details
    ], width)
    
    for line in darkweb_box:
        print(line)
    print()

    # ================== 4. FINAL ROW: SECURITY LEVEL ASSESSMENT ==================
    lvl = strength(log10_value, pattern_warning)
    sec = make_box("OVERALL SECURITY ASSESSMENT", [
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
    C, has_low, has_upp, has_num, has_sym = calc_charset(password)
    
    if C == 0:
        print("[!] Could not determine charset.")
        return
        
    L = len(password)
    combinations, log10_value = calc_combinations(C, L)
    
    # Push data variables matrix structures forward into formatting layout routines
    print_output(password, C, L, combinations, log10_value, has_low, has_upp, has_num, has_sym, mask_mode=args.Mask)


if __name__ == "__main__":
    main()
