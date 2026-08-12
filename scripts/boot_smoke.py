"""
boot_smoke.py — Teste de fumaça do boot da casca (sem janela real).
Uso:  python scripts/boot_smoke.py
Requer QPA offscreen (definido aqui) → não abre janela visível.
Valida: MainWindow cria, plugins carregam, workspace monta, engine init não crasha.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from ui.boundary.orchestrator.main_window import MainWindow  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.processEvents()

    central = window.centralWidget()
    print(f"[boot_smoke] centralWidget  = {type(central).__name__ if central else None}")
    if central is not None:
        print(f"[boot_smoke] tem canvas      = {hasattr(central, 'canvas_widget')}")
        print(f"[boot_smoke] left_dock       = {hasattr(central, 'left_dock')}")
        print(f"[boot_smoke] right_dock      = {hasattr(central, 'right_dock')}")

    plugin_manager = getattr(window, "plugin_manager", None)
    if plugin_manager is not None:
        print(f"[boot_smoke] plugins ativos  = {sorted(plugin_manager.active_instances.keys())}")

    app.processEvents()
    window.close()
    app.processEvents()
    print("[boot_smoke] BOOT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())