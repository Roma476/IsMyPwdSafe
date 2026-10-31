from .base import EngineScore

_SCORE_MAP = {0: 10, 1: 30, 2: 50, 3: 75, 4: 100}
_RATING_MAP = {0: "weak", 1: "weak", 2: "medium", 3: "strong", 4: "strong"}

class PythonZxcvbnEngine:
    name = "python"

    def __init__(self) -> None:
        try:
            import zxcvbn  # type: ignore[import-untyped]
        except ImportError as e:
            raise RuntimeError(
                "--engine=python requires the 'zxcvbn' package. "
                "Install it with: pip install ismypwdsafe[python]"
            ) from e
        self._zxcvbn = zxcvbn.zxcvbn

    def score(self, password: str) -> EngineScore:
        result = self._zxcvbn(password)
        s = result['score']
        return EngineScore(
            value=_SCORE_MAP[s],
            rating=_RATING_MAP[s],
            raw_score_0_4=s,
            engine_name="python"
        )