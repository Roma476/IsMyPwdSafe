"""Compatibility shim. The CLI now lives in ismypwdsafe.cli."""
from __future__ import annotations

import sys

from .cli import entry

if __name__ == "__main__":
    sys.exit(entry())