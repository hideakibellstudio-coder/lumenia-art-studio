"""
bisect_view_cumulative.py — Reproduz LayerTreeView passo a passo (cumulativo).
Uso: python scripts/bisect_view_cumulative.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEAD = (
    "import sys, gc; "
    "from PySide6 import QtWidgets; "
    "from PySide6.QtWidgets import QApplication, QTreeView, QAbstractItemView; "
    "from PySide6.QtCore import Qt; "
    "a=QApplication(sys.argv);"
)

TEMPLATE = (
    "v=QTreeView(); {attrs}"
    "w=QtWidgets.QWidget(); l=QtWidgets.QVBoxLayout(w); l.addWidget(v); w.show();"
    "a.processEvents(); w.close(); w.deleteLater(); a.processEvents(); "
    "w=None; v=None; gc.collect(); a.processEvents(); print('done')"
)

B1 = "v.setHeaderHidden(True); v.setIndentation(16); v.setRootIsDecorated(False); "
B2 = "v.setAnimated(True); v.setAllColumnsShowFocus(True); "
B3 = "v.setSelectionMode(QAbstractItemView.SingleSelection); "
B4 = (
    "v.setDragEnabled(True); v.setAcceptDrops(True); v.setDropIndicatorShown(True); "
    "v.setDragDropMode(QAbstractItemView.InternalMove); "
)
B5 = (
    "from PySide6.QtWidgets import QProxyStyle, QStyle; "
    "class NS(QProxyStyle):\n"
    "    def drawPrimitive(self, element, option, painter, widget=None):\n"
    "        if element == QStyle.PE_FrameFocusRect:\n"
    "            return\n"
    "        super().drawPrimitive(element, option, painter, widget)\n"
    "_style=NS(v.style()); v.setStyle(_style); "
)
B6 = "v.setStyleSheet('QTreeView { outline:none; background-color: transparent; }'); "

CASES = [
    ("base_repo", B1),
    ("+animado+foco", B1 + B2),
    ("+selecao", B1 + B2 + B3),
    ("+drag", B1 + B2 + B3 + B4),
    ("+proxy_estilo", B1 + B2 + B3 + B4 + B5),
    ("+qss_branch", B1 + B2 + B3 + B4 + B5 + B6),
]

for name, attrs in CASES:
    code = HEAD + TEMPLATE.format(attrs=attrs)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    tag = "CRASH" if proc.returncode in (-1073741819, -1073740791) else "ok"
    print(f"{name:>14}: exit={proc.returncode}  [{tag}]")