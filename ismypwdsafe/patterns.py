"""Pattern detection: top-150 dictionary, QWERTY walks, years, repetition."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

_DATE_PATTERN = re.compile(
    r'(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}'
)

_LEET_MAP = str.maketrans({
    '@': 'a', '4': 'a', '3': 'e', '0': 'o', '1': 'i',
    '!': 'i', '$': 's', '5': 's', '7': 't', '8': 'b',
})


def normalize_leetspeak(password: str) -> str:
    """Lowercase + leet-speak normalization. Used by detection and by the UI checkbox."""
    return password.lower().translate(_LEET_MAP)


def get_top150_set() -> set[str]:
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

def get_multilingual_set() -> set[str]:
    return {
        # French
        "motdepasse", "bonjour", "soleil",
        # Spanish
        "contraseña", "hola", "futbol",
        # German
        "passwort", "schatz", "hallo", "liebe", "sommer",
        # Italian
        "parola", "ciao", "estate",
        # Russian
        "пароль", "привет", "любовь", "лето",
        # Chinese/Japanese
        "密码", "パスワード", "你好", "こんにちは",
        # Portuguese
        "senha", "obrigado",
        # Dutch
        "wachtwoord",
        # Polish
        "hasło",
    }

_KEYBOARD = {
    '1': (0, 0), '2': (0, 1), '3': (0, 2), '4': (0, 3), '5': (0, 4),
    '6': (0, 5), '7': (0, 6), '8': (0, 7), '9': (0, 8), '0': (0, 9),
    'q': (1, 0), 'w': (1, 1), 'e': (1, 2), 'r': (1, 3), 't': (1, 4),
    'y': (1, 5), 'u': (1, 6), 'i': (1, 7), 'o': (1, 8), 'p': (1, 9),
    'a': (2, 0), 's': (2, 1), 'd': (2, 2), 'f': (2, 3), 'g': (2, 4),
    'h': (2, 5), 'j': (2, 6), 'k': (2, 7), 'l': (2, 8),
    'z': (3, 0), 'x': (3, 1), 'c': (3, 2), 'v': (3, 3), 'b': (3, 4),
    'n': (3, 5), 'm': (3, 6),
}


def check_keyboard_spatial(password: str) -> bool:
    """Keyboard model. True if 4+ adjacent keys form a walk."""
    coords = [_KEYBOARD[c] for c in password.lower() if c in _KEYBOARD]
    if len(coords) < 4:
        return False
        
    current_run = 0
    max_run = 0
    
    for i in range(len(coords) - 1):
        r1, c1 = coords[i]
        r2, c2 = coords[i + 1]
        dr = abs(r2 - r1)
        dc = abs(c2 - c1)
        
        # Adjacent keys (horizontal, vertical, diagonal)
        if (dr <= 1 and dc <= 1) and not (dr == 0 and dc == 0):
            current_run += 1
            max_run = max(max_run, current_run)
        else:
            current_run = 0
            
    return max_run >= 3


def check_patterns(password: str) -> Optional[str]:
    """Deprecated: use detect_pattern instead."""
    return detect_pattern(password).detail

@dataclass(frozen=True)
class PatternResult:
    detected: bool
    rule: Optional[str]   # "top150" | "qwerty_walk" | "common_year" | "repetition" | None
    detail: Optional[str]  # human-readable warning, None when not detected
    rules_fired: List[str] = field(default_factory=list)


def detect_pattern(password: str) -> PatternResult:
    """Structured version of check_patterns. Evaluates all rules."""
    if not password:
        return PatternResult(False, None, None, [])
        
    # Normalize to NFC to handle combining characters (e.g. "e" + combining acute)
    password = unicodedata.normalize("NFC", password)

    normalized = normalize_leetspeak(password)
    rules_fired: List[str] = []
    detail = None
    primary_rule = None

    # 1. Top 150 dictionary (sorted by length descending)
    for item in sorted(get_top150_set(), key=len, reverse=True):
        if item in password.lower() or item in normalized:
            rules_fired.append("top150")
            if primary_rule is None:
                primary_rule = "top150"
                detail = f"Top 150 most used passwords list match ('{item}')"
            break

    # 2. Multilingual dictionary (sorted by length descending, deterministic)
    pwd_lower = password.lower()
    for item in sorted(get_multilingual_set(), key=len, reverse=True):
        if len(item) < 6:
            matched = (pwd_lower == item)              # exact only for short words
        else:
            matched = (item in pwd_lower)              # substring for long words
            
        if matched:
            if "top150" not in rules_fired:
                rules_fired.append("top150")
            if primary_rule is None:
                primary_rule = "top150"
                detail = f"Multilingual dictionary match ('{item}')"
            break

    # 3. Structured Dates
    if _DATE_PATTERN.search(password):
        if "common_year" not in rules_fired:
            rules_fired.append("common_year")
        if primary_rule is None:
            primary_rule = "common_year"
        detail = "Contains a structured date"

    # 4. Keyboard Walk / Zig-Zag
    if check_keyboard_spatial(password):
        rules_fired.append("qwerty_walk")
        if primary_rule is None:
            primary_rule = "qwerty_walk"
            detail = "Keyboard spatial walk detected (QWERTY layout)"

    # 5. Common Year (e.g. 1990)
    for i in range(len(password) - 3):
        chunk = password[i:i + 4]
        if chunk.isdigit():
            year = int(chunk)
            if 1900 <= year <= 2050:
                if "common_year" not in rules_fired:
                    rules_fired.append("common_year")
                if primary_rule is None:
                    primary_rule = "common_year"
                    detail = f"Contains common year ({year})"
                break

    # 6. Character Repetition (e.g. aaa, 111)
    for i in range(len(pwd_lower) - 2):
        if pwd_lower[i] == pwd_lower[i + 1] == pwd_lower[i + 2]:
            if "repetition" not in rules_fired:
                rules_fired.append("repetition")
            if primary_rule is None:
                primary_rule = "repetition"
                detail = "Excessive character repetition"
            break

    detected = len(rules_fired) > 0
    return PatternResult(detected, primary_rule, detail, rules_fired)
