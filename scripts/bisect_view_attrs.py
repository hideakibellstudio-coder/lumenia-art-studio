"""
bisect_view_attrs.py — Isola o atributo do LayerTreeView que causa o crash.
Uso: python scripts/bisect_view_attrs.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEAD = (
    "import sys, gc; "
    "from PySide6 import QtWidgets; "
    "from PySide6.QtWidgets import QApplication, QTreeView, QAbstractItemView; "
    "a=QApplication(sys.argv);"
)

TEMPLATE = (
    "v=QTreeView(); {attrs}"
    "w=QtWidgets.QWidget(); l=QtWidgets.QVBoxLayout(w); l.addWidget(v); w.show();"
    "a.processEvents(); w.close(); w.deleteLater(); a.processEvents(); "
    "w=None; v=None; gc.collect(); a.processEvents(); print('done')"
)

CASES = [
    ("set_animated", "v.setAnimated(True); "),
    ("drag_internal_move", (
        "v.setDragEnabled(True); v.setAcceptDrops(True); "
        "v.setDropIndicatorShown(True); v.setDragDropMode(QAbstractItemView.InternalMove); "
    )),
    ("style_proxy_ref", (
        "from PySide6.QtWidgets import QProxyStyle, QStyle; "
        "class NS(QProxyStyle):\n"
        "    def drawPrimitive(self, e, o, p, w=None):\n"
        "        if e == QStyle.PE_FrameFocusRect: return\n"
        "        return super().drawPrimitive(e, o, p, w)\n"
        "_s=NS(v.style()); v.setStyle(_s); "
    )),
    ("stylesheet_branch", (
        'v.setStyleSheet("QTreeView { outline:none; } '
        'QTreeView::branch:has-children:!has-siblings:closed { image:none; }"); '
    )),
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
    print(f"{name:>22}: exit={proc.returncode}  [{tag}]")