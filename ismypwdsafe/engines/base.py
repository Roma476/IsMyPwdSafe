from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EngineScore:
    value: int              # 0-100 (mappato)
    rating: str             # "weak" | "medium" | "strong"
    raw_score_0_4: int | None
    engine_name: str        # "ts" | "python" | "native"

class EngineBackend(Protocol):
    def score(self, password: str) -> EngineScore: ...