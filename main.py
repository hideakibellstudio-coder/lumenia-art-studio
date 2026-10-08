"""
Lumenia Root Entrypoint — Ponto Único de Entrada do Monorepo (ARCcC).
=====================================================================
Inicializa o ambiente do projeto e delega para o orquestrador canônico da UI.

No programa instalado, o Velopack roda antes de tudo: ele trata a instalação,
a atualização e a desinstalação (e pode encerrar ou reiniciar o processo).
Em desenvolvimento ele não roda (`__compiled__` só existe no build do Nuitka).
"""

from __future__ import annotations

import sys
import os


def _run_velopack_hooks() -> None:
    if not ("__compiled__" in globals() or getattr(sys, "frozen", False)):
        return
    try:
        import velopack
    except ImportError:
        return
    velopack.App().run()


if __name__ == "__main__":
    _run_velopack_hooks()

    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    from ui.boundary.orchestrator.app_runner import launch
    sys.exit(launch(sys.argv))
