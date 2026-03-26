"""Pytest configuration to adjust the Python path for imports.

This file ensures that the ``phase10`` package is discoverable when
running tests.  Without this, modules under ``phase10/`` would not be
found because they are not installed in site‑packages.
"""

from __future__ import annotations

import os
import sys


# Add the repository root (parent of ``phase10``) to sys.path so that the
# ``phase10`` package can be imported during tests.  Without this,
# ``pytest`` cannot find modules under ``phase10`` because they are not
# installed in the standard library path.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
