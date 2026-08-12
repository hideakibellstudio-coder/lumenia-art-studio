"""
bisect_layers_crash2.py — Diagnóstico refinado do crash de teardown do Layers.
Uso: python scripts/bisect_layers_crash2.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEAD = (
    "import sys, gc; "
    "from PySide6 import QtWidgets; "
    "from PySide6.QtWidgets import QApplication; "
    "from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt; "
    "a=QApplication(sys.argv);"
)

CASES = [
    ("plain_qtreeview", (
        "v=QtWidgets.QTreeView(); w=QtWidgets.QWidget(); "
        "l=QtWidgets.QVBoxLayout(w); l.addWidget(v); w.show();"
    )),
    ("qtreeview_styled_proxy", (
        "from PySide6.QtWidgets import QProxyStyle, QStyle; "
        "class NS(QProxyStyle):\n"
        "    def drawPrimitive(self, e, o, p, w=None):\n"
        "        if e == QStyle.PE_FrameFocusRect: return\n"
        "        return super().drawPrimitive(e, o, p, w)\n"
        "v=QtWidgets.QTreeView(); s=NS(v.style()); v.setStyle(s); "
        "w=QtWidgets.QWidget(); l=QtWidgets.QVBoxLayout(w); l.addWidget(v); w.show();"
    )),
    ("layertree_sem_model", (
        "from plugins.ui.layers_plugin.view import LayerTreeView; "
        "v=LayerTreeView(); w=QtWidgets.QWidget(); "
        "l=QtWidgets.QVBoxLayout(w); l.addWidget(v); w.show();"
    )),
    ("layertree_com_style", (
        "from plugins.ui.layers_plugin.view import LayerTreeView, NoFocusProxyStyle; "
        "v=LayerTreeView(); v.setStyle(NoFocusProxyStyle(v.style())); "
        "w=QtWidgets.QWidget(); l=QtWidgets.QVBoxLayout(w); l.addWidget(v); w.show();"
    )),
    ("layertree_com_model", (
        "from plugins.ui.layers_plugin.view import LayerTreeView; "
        "from plugins.ui.layers_plugin.manager import LocalLayerManager; "
        "from plugins.ui.layers_plugin.model import LayerModel; "
        "v=LayerTreeView(); v.setModel(LayerModel(LocalLayerManager())); "
        "w=QtWidgets.QWidget(); l=QtWidgets.QVBoxLayout(w); l.addWidget(v); w.show();"
    )),
]

TAIL = (
    "a.processEvents(); w.close(); w.deleteLater(); a.processEvents(); "
    "w=None; v=None; gc.collect(); a.processEvents(); print('done')"
)

for name, body in CASES:
    code = HEAD + body + TAIL
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    tag = "CRASH" if proc.returncode in (-1073741819, -1073740791) else "ok"
    print(f"{name:>22}: exit={proc.returncode}  [{tag}]")