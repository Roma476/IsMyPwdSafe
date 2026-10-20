"""Pattern detection: top-150 dictionary, QWERTY walks, years, repetition."""
from typing import NamedTuple, Optional

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
    """Real QWERTY coordinate model. True if 4+ keys move in one direction."""
    coords = [_KEYBOARD[c] for c in password.lower() if c in _KEYBOARD]
    if len(coords) < 3:
        return False
    straight_walks = 0
    for i in range(len(coords) - 1):
        r1, c1 = coords[i]
        r2, c2 = coords[i + 1]
        dr = abs(r2 - r1)
        dc = abs(c2 - c1)
        if (dr == 0 and dc == 1) or (dr == 1 and dc == 0) or (dr == 1 and dc == 1):
            straight_walks += 1
        else:
            straight_walks = 0
        if straight_walks >= 3:
            return True
    return False


def check_patterns(password: str) -> Optional[str]:
    """
    Returns the human-readable warning for the first matching rule, or None.
    Rules are checked in order: top-150, QWERTY walk, common year, repetition.
    """
    if not password:
        return None

    normalized = normalize_leetspeak(password)
    top_150 = get_top150_set()

    for item in top_150:
        if item in password.lower() or item in normalized:
            return f"Top 150 most used passwords list match ('{item}')"

    if check_keyboard_spatial(password):
        return "Keyboard spatial walk detected (QWERTY layout)"

    for i in range(len(password) - 3):
        chunk = password[i:i + 4]
        if chunk.isdigit():
            year = int(chunk)
            if 1900 <= year <= 2050:
                return f"Contains common year ({year})"

    pwd_lower = password.lower()
    for i in range(len(pwd_lower) - 2):
        if pwd_lower[i] == pwd_lower[i + 1] == pwd_lower[i + 2]:
            return "Excessive character repetition"

    return None


class PatternResult(NamedTuple):
    detected: bool
    rule: Optional[str]   # "top150" | "qwerty_walk" | "common_year" | "repetition" | None
    detail: Optional[str]  # human-readable warning, None when not detected


def detect_pattern(password: str) -> PatternResult:
    """Structured version of check_patterns. First matching rule wins."""
    if not password:
        return PatternResult(False, None, None)

    normalized = normalize_leetspeak(password)
    for item in get_top150_set():
        if item in password.lower() or item in normalized:
            return PatternResult(
                True, "top150",
                f"Top 150 most used passwords list match ('{item}')",
            )

    if check_keyboard_spatial(password):
        return PatternResult(True, "qwerty_walk", "Keyboard spatial walk detected (QWERTY layout)")

    for i in range(len(password) - 3):
        chunk = password[i:i + 4]
        if chunk.isdigit():
            year = int(chunk)
            if 1900 <= year <= 2050:
                return PatternResult(True, "common_year", f"Contains common year ({year})")

    pwd_lower = password.lower()
    for i in range(len(pwd_lower) - 2):
        if pwd_lower[i] == pwd_lower[i + 1] == pwd_lower[i + 2]:
            return PatternResult(True, "repetition", "Excessive character repetition")

    return PatternResult(False, None, None)
