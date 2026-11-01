from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, Tuple

from .availability import node_version
from .base import EngineError, EngineResult, score_percent, score_rating

_BUNDLE = Path(__file__).resolve().parent.parent / "js" / "zxcvbn-ts.bundle.js"


class ZxcvbnTsEngine:
    name = "ts"

    def __init__(self) -> None:
        version = node_version()
        if version is None:
            raise EngineError(
                "--engine=ts requires Node.js 18+. Install it with your package "
                "manager, or use --engine=python / --engine=native."
            )
        if version < (18, 0):
            found = ".".join(str(part) for part in version)
            raise EngineError(
                f"--engine=ts requires Node.js 18+, but Node {found} was found."
            )

    def score(self, password: str, *, check_breach: bool = True) -> EngineResult:
        payload = json.dumps(
            {"password": password, "check_breach": check_breach},
            ensure_ascii=False,
        )
        try:
            proc = subprocess.run(  # noqa: S603
                ["node", str(_BUNDLE)],  # noqa: S607
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise EngineError(f"Could not run zxcvbn-ts: {exc}") from exc

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise EngineError(f"zxcvbn-ts failed: {detail or 'unknown error'}")

        try:
            raw: Dict[str, Any] = json.loads(proc.stdout)
            raw_score = int(raw["score"])
        except (ValueError, KeyError, TypeError) as exc:
            raise EngineError(f"zxcvbn-ts returned invalid output: {exc}") from exc

        sequence: Tuple[Dict[str, Any], ...] = tuple(
            item for item in raw.get("sequence", []) if isinstance(item, dict)
        )
        seconds = {
            str(key): value
            for key, value in (raw.get("crack_times_seconds") or {}).items()
        }
        display = {
            str(key): str(value)
            for key, value in (raw.get("crack_times_display") or {}).items()
        }

        return EngineResult(
            engine_name="ts",
            engine_version=raw.get("engine_version"),
            raw_score_0_4=raw_score,
            score_100=score_percent(raw_score),
            rating=score_rating(raw_score),
            guesses=raw.get("guesses"),
            guesses_log10=raw.get("guesses_log10"),
            crack_times_seconds=seconds,
            crack_times_display=display,
            feedback_warning=(raw.get("feedback") or {}).get("warning"),
            feedback_suggestions=tuple(
                (raw.get("feedback") or {}).get("suggestions") or ()
            ),
            sequence=sequence,
            calc_time=raw.get("calc_time"),
            pwned=raw.get("pwned"),
            pwned_count=raw.get("pwned_count"),
            hibp_status=str(raw.get("hibp_status") or "disabled"),
            hibp_error=raw.get("hibp_error"),
        )
