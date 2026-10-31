import json
import shutil
import subprocess
from pathlib import Path

from .base import EngineScore

_BUNDLE = Path(__file__).parent.parent / "js" / "zxcvbn-ts.bundle.js"
_SCORE_MAP = {0: 10, 1: 30, 2: 50, 3: 75, 4: 100}
_RATING_MAP = {0: "weak", 1: "weak", 2: "medium", 3: "strong", 4: "strong"}

class ZxcvbnTsEngine:
    name = "ts"

    def __init__(self) -> None:
        if shutil.which("node") is None:
            raise RuntimeError(
                "--engine=ts requires Node.js 18+. "
                "Install it with your package manager, or use --engine=python."
            )

    def score(self, password: str) -> EngineScore:
        proc = subprocess.run(  # noqa: S603
            ["node", str(_BUNDLE)],  # noqa: S607
            input=json.dumps({"password": password}),
            capture_output=True, text=True, timeout=5, check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"zxcvbn-ts failed: {proc.stderr.strip()}")
        
        r = json.loads(proc.stdout)
        s = r["score"]
        return EngineScore(
            value=_SCORE_MAP[s],
            rating=_RATING_MAP[s],
            raw_score_0_4=s,
            engine_name="ts"
        )