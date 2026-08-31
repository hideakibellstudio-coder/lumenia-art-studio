"""
Lumenia Root Entrypoint — Ponto Único de Entrada do Monorepo (ARCcC).
=====================================================================
Inicializa o ambiente do projeto e delega para o orquestrador canônico da UI.
"""

from __future__ import annotations

import sys
import os

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    from ui.boundary.orchestrator.app_runner import launch
    sys.exit(launch(sys.argv))
