"""
bisect_panel_crash.py — Diagnóstico: qual painel causa crash no teardown offscreen.
Uso: python scripts/bisect_panel_crash.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = {
    "nenhum": "",
    "color": "from plugins.ui.color_plugin.panel import ColorWheelPanel; wc.add_panel('c','Cor',ColorWheelPanel(initial_color=None),'left')",
    "brush": "from plugins.ui.brush_plugin.panel import BrushSettingsPanel; wc.add_panel('b','Pincel',BrushSettingsPanel(),'left')",
    "navigator": "from plugins.ui.navigator_plugin.panel import NavigatorPanel; wc.add_panel('n','Nav',NavigatorPanel(),'right')",
    "layers": "from plugins.ui.layers_plugin.panel import LayersPanel; wc.add_panel('l','Camadas',LayersPanel(),'right')",
}

SNIPPET = (
    "import sys; "
    "from PySide6.QtWidgets import QApplication; "
    "from ui.core.components.workspace import WorkspaceContainer; "
    "a=QApplication(sys.argv); "
    "wc=WorkspaceContainer(); "
    "{case}; "
    "wc.close(); wc.deleteLater(); a.processEvents(); print('t1'); a.quit()"
)

for name, case in CASES.items():
    code = SNIPPET.format(case=case)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"{name:>10}: exit={proc.returncode} (0xC0000409={proc.returncode == -1073740791} | AV={proc.returncode == -1073741819})")