"""Directory-plugin shim for installing this repository directly in Hermes."""

from __future__ import annotations

import sys
from pathlib import Path

_SOURCE = Path(__file__).parent / "src"
if str(_SOURCE) not in sys.path:
    sys.path.insert(0, str(_SOURCE))

from academic_research.hermes_plugin import register  # noqa: E402

__all__ = ["register"]
