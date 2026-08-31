"""
ui.main — Shim de Compatibilidade para AppRunner (ARCcC).
=========================================================
Delega a execução para ui.boundary.orchestrator.app_runner.
"""

from __future__ import annotations

import sys
import os

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from ui.boundary.orchestrator.app_runner import launch

if __name__ == "__main__":
    sys.exit(launch(sys.argv))
