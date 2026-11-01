from __future__ import annotations

from typing import Dict, Type

from .availability import node_version, python_available, ts_available
from .base import EngineBackend, EngineError, EngineResult
from .native import NativeEngine
from .python import PythonZxcvbnEngine
from .ts import ZxcvbnTsEngine

ENGINES = ("auto", "ts", "python", "native")


def resolve_engine(requested: str) -> str:
    """Resolve auto/ts/python/native to a concrete available engine."""
    name = requested or "auto"
    if name not in ENGINES:
        raise EngineError(
            f"Unknown engine '{name}'. Choose one of: {', '.join(ENGINES)}."
        )

    if name == "auto":
        if ts_available():
            return "ts"
        if python_available():
            return "python"
        raise EngineError(
            "No zxcvbn engine is available. Install Node.js 18+ for the "
            "recommended zxcvbn-ts engine, or install the Python fallback with "
            "'pip install ismypwdsafe[python]'. You can also use "
            "'--engine=native' explicitly."
        )

    if name == "ts":
        version = node_version()
        if version is None:
            raise EngineError(
                "--engine=ts requires Node.js 18+. Install it with your "
                "package manager, or use --engine=python / --engine=native."
            )
        if version < (18, 0):
            found = ".".join(str(part) for part in version)
            raise EngineError(
                f"--engine=ts requires Node.js 18+, but Node {found} was found. "
                "Upgrade Node or use --engine=python / --engine=native."
            )
    elif name == "python" and not python_available():
        raise EngineError(
            "--engine=python requires the 'zxcvbn' package. Install it with: "
            "pip install ismypwdsafe[python]"
        )

    return name


def make_engine(name: str) -> EngineBackend:
    concrete = resolve_engine(name)
    classes: Dict[str, Type[EngineBackend]] = {
        "ts": ZxcvbnTsEngine,
        "python": PythonZxcvbnEngine,
        "native": NativeEngine,
    }
    return classes[concrete]()


__all__ = [
    "EngineBackend",
    "EngineError",
    "EngineResult",
    "NativeEngine",
    "PythonZxcvbnEngine",
    "ZxcvbnTsEngine",
    "node_version",
    "python_available",
    "resolve_engine",
    "ts_available",
]
