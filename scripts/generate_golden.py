"""Regenerate the schema/golden fixtures.

Usage:
    python scripts/generate_golden.py --engine ts
    python scripts/generate_golden.py --engine native
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ismypwdsafe import analyze_password
from ismypwdsafe.engines import EngineError, resolve_engine
from ismypwdsafe.render import render_json

CASES = [
    # Dictionary / top-password patterns
    "123456",
    "password",
    "qwerty",
    "letmein",
    "P@ssw0rd",
    "Password123!",
    "Admin@123",
    "P@ssw0rd2024",
    # Sequences, repeats, dates
    "mnbvcxz",
    "asdfghjkl",
    "2010",
    "abcd1990efgh",
    "password!!!",
    "aaa",
    "1111111111",
    # Strong and mixed
    "correct-horse-battery-staple",
    "correct horse battery staple",
    "vT7#pQ2!mN9x",
    "Tr0ub4dor&3",
    "x9F$kL2@pW5z",
    # Edge cases
    "",
    " ",
    "a",
    "\x00",
    "a\nb",
    "\x1b[31mred\x1b[0m",
    "a" * 10000,
    "🔒🔑",
    "P@ssw0rd\x00",
    # Unicode / confusables
    "пароль",
    "密码",
    "pässwörd",
    "аdmin",
    "pаssword",
    "e\u0301",
    "👨‍👩‍👧",
    "🇮🇹",
    # Long / charset coverage
    "password" * 100,
    "Aa1!Aa1!Aa1!",
    "12345678901234567890",
    "a\tb",
    "a\r\nb",
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--engine",
        choices=["auto", "ts", "python", "native"],
        default="ts",
        help="Engine used to produce the golden values.",
    )
    args = parser.parse_args()
    try:
        engine = resolve_engine(args.engine)
    except EngineError as exc:
        raise SystemExit(str(exc)) from exc

    out_dir = Path(__file__).parent.parent / "tests" / "golden"
    out_dir.mkdir(parents=True, exist_ok=True)
    cases_path = out_dir / "cases.json"
    cases_path.write_text(
        json.dumps(CASES, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    golden_data = []
    for password in CASES:
        result = analyze_password(password, check_breach=False, engine_name=engine)
        golden_data.append(
            {
                "input": password,
                "expected": json.loads(render_json(result)),
            }
        )
    scores_path = out_dir / "scores.json"
    scores_path.write_text(
        json.dumps(golden_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(CASES)} {engine} cases to {cases_path} and {scores_path}")


if __name__ == "__main__":
    main()
