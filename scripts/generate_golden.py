import json
from pathlib import Path

from ismypwdsafe import analyze_password
from ismypwdsafe.render import render_json

CASES = [
    # Top 150 / Dictionary
    "123456", "password", "12345678", "qwerty", "123456789", "12345", "1234",
    "111111", "1234567", "dragon", "123123", "baseball", "abc123", "football",
    "monkey", "letmein", "696969", "shadow", "master", "666666", "qwertyuiop",
    "123321", "mustang", "1234567890", "michael", "654321", "superman",
    "1qaz2wsx", "7777777", "121212", "000000", "qazwsx", "123qwe", "killer",
    "trustno1", "jordan", "jennifer", "zxcvbnm", "asdfgh", "hunter", "buster",
    "soccer", "harley", "batman", "andrew", "tigger", "sunshine", "iloveyou",
    "2000", "charlie", "robert", "thomas", "hockey", "ranger", "daniel",
    "starwars", "klaster", "112233", "george", "computer", "michelle",
    "jessica", "pepper", "1111", "zxcvbn", "555555", "11111111", "131313",
    "freedom", "777777", "pass", "maggie", "159753", "aaaaaa", "ginger",
    "princess", "joshua", "cheese", "amanda", "summer", "love", "ashley",
    "6969", "nicole", "chelsea", "biteme", "matthew", "access", "yankees",
    "987654321", "dallas", "austin", "thunder", "taylor", "matrix",
    # Qwerty walks
    "mnbvcxz", "asdfghjkl", "poiuytr",
    # Years
    "2010", "1990", "summer2024", "password2023", "abcd1990efgh",
    # Repetition
    "password!!!", "aaa", "zzzzzz", "...", "1111111111",
    # Mixed / Patterns
    "P@ssw0rd", "Password123!", "Admin@123", "P@ssw0rd2024",
    # Random strong
    "correct-horse-battery-staple", "vT7#pQ2!mN9x", "x9F$kL2@pW5z",
    # Edge cases
    "", " ", "a", "\x00", "a\nb", "\x1b[31mred\x1b[0m",
    "a" * 10000, "🔒🔑", "P@ssw0rd\x00",
    # Unicode
    "пароль", "密码", "pässwörd",
    # Homoglyph / confusables
    "аdmin", "pаssword", "аdm1n",
    # Combining chars
    "e\u0301", "p\u00e4ssword",
    # Emoji ZWJ sequences
    "👨‍👩‍👧", "🇮🇹",
    # Long dictionary password
    "password" * 100,
    # All charsets
    "Aa1!Aa1!Aa1!",
    # Long digits only
    "12345678901234567890",
    # Internal spaces
    "correct horse battery staple",
    # Control characters
    "a\tb", "a\r\nb",
]

def main() -> None:
    out_dir = Path(__file__).parent.parent / "tests" / "golden"
    out_dir.mkdir(parents=True, exist_ok=True)

    cases_path = out_dir / "cases.json"
    with open(cases_path, "w", encoding="utf-8") as f:
        json.dump(CASES, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(CASES)} cases to {cases_path}")

    golden_data = []
    for pwd in CASES:
        try:
            result = analyze_password(pwd, check_breach=False)
            golden_data.append({
                "input": pwd,
                "expected": json.loads(render_json(result))
            })
        except Exception as e:
            print(f"Error analyzing {pwd!r}: {e}")
            golden_data.append({
                "input": pwd,
                "error": str(e)
            })

    scores_path = out_dir / "scores.json"
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(golden_data, f, indent=2, ensure_ascii=False)
    print(f"Wrote golden scores to {scores_path}")

if __name__ == "__main__":
    main()