"""Compatibility shim. The CLI now lives in ismypwdsafe.cli."""
import sys

from .cli import entry


if __name__ == "__main__":
    sys.exit(entry())