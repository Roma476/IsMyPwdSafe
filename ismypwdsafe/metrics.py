"""Low-level metrics: charset detection and combination counting."""
from __future__ import annotations

import math
import unicodedata
from typing import Optional

SCRIPT_CHARSETS = {
    "CYRILLIC": 33,
    "GREEK": 24,
    "ARABIC": 28,
    "HEBREW": 22,
    "CJK": 5000,
    "EMOJI": 1000,
    "LATIN": 200,
    "OTHER": 500,
}


def must_use_log(charset_size: int, length: int) -> bool:
    if charset_size > 95:
        return length >= 3
    if charset_size in (62, 63):
        return length >= 5
    return length >= 4


def calc_charset(password: str) -> tuple[int, bool, bool, bool, bool, bool]:
    number = lower = upper = symbol = False
    has_non_ascii = False
    total = 0

    non_ascii_chars = []

    for char in password:
        if ord(char) > 127:
            has_non_ascii = True
            non_ascii_chars.append(char)
            continue

        if char.isdigit() and not number:
            number = True
            total += 10
        elif char.islower() and not lower:
            lower = True
            total += 26
        elif char.isupper() and not upper:
            upper = True
            total += 26
        elif not char.isalnum() and not symbol:
            symbol = True
            total += 33

    if has_non_ascii:
        scripts = set()
        for char in non_ascii_chars:
            cp = ord(char)
            if (
                (0x1F300 <= cp <= 0x1FAFF)
                or (0x2600 <= cp <= 0x27BF)
                or (0x1F1E6 <= cp <= 0x1F1FF)
                or (0x1F3FB <= cp <= 0x1F3FF)
            ):
                scripts.add("EMOJI")
            else:
                try:
                    name = unicodedata.name(char)
                    script = name.split()[0]
                    if script in SCRIPT_CHARSETS:
                        scripts.add(script)
                    else:
                        scripts.add("OTHER")
                except ValueError:
                    scripts.add("OTHER")

        if scripts:
            max_script = max(scripts, key=lambda s: SCRIPT_CHARSETS.get(s, 500))
            total += SCRIPT_CHARSETS.get(max_script, 500)

    return total, lower, upper, number, symbol, has_non_ascii


def calc_combinations(charset_size: int, length: int) -> tuple[Optional[int], float]:
    log10_value = length * math.log10(charset_size) if charset_size > 0 else 0
    if must_use_log(charset_size, length):
        return None, log10_value
    return charset_size ** length, log10_value