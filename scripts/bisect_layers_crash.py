"""
bisect_layers_crash.py — Diagnóstico fino do crash de teardown do LayersPanel.
Uso: python scripts/bisect_layers_crash.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES = {
    "manager+model": (
        "from plugins.ui.layers_plugin.manager import LocalLayerManager; "
        "from plugins.ui.layers_plugin.model import LayerModel; "
        "m=LocalLayerManager(); mdl=LayerModel(m)"
    ),
    "+view": (
        "from plugins.ui.layers_plugin.manager import LocalLayerManager; "
        "from plugins.ui.layers_plugin.model import LayerModel; "
        "from plugins.ui.layers_plugin.view import LayerTreeView; "
        "m=LocalLayerManager(); mdl=LayerModel(m); "
        "v=LayerTreeView(); v.setModel(mdl); w=QtWidgets.QWidget(); "
        "lay=QtWidgets.QVBoxLayout(w); lay.addWidget(v); w.show()"
    ),
    "+delegate": (
        "from plugins.ui.layers_plugin.manager import LocalLayerManager; "
        "from plugins.ui.layers_plugin.model import LayerModel; "
        "from plugins.ui.layers_plugin.view import LayerTreeView; "
        "from plugins.ui.layers_plugin.delegate import LayerItemDelegate; "
        "m=LocalLayerManager(); mdl=LayerModel(m); "
        "v=LayerTreeView(); v.setModel(mdl); v.setItemDelegate(LayerItemDelegate(v)); "
        "w=QtWidgets.QWidget(); lay=QtWidgets.QVBoxLayout(w); lay.addWidget(v); w.show()"
    ),
    "+header+paper": (
        "from plugins.ui.layers_plugin.manager import LocalLayerManager; "
        "from plugins.ui.layers_plugin.model import LayerModel; "
        "from plugins.ui.layers_plugin.view import LayerTreeView; "
        "from plugins.ui.layers_plugin.delegate import LayerItemDelegate; "
        "from plugins.ui.layers_plugin.header import LayersHeader; "
        "from plugins.ui.layers_plugin.grid import LayersPrimaryBox, LayersSecondaryBar; "
        "from plugins.ui.layers_plugin.paper import PaperLayerWidget; "
        "m=LocalLayerManager(); mdl=LayerModel(m); "
        "v=LayerTreeView(); v.setModel(mdl); v.setItemDelegate(LayerItemDelegate(v)); "
        "w=QtWidgets.QWidget(); lay=QtWidgets.QVBoxLayout(w); lay.addWidget(v); w.show()"
    ),
}

SNIPPET = (
    "import sys; from PySide6 import QtWidgets; "
    "from PySide6.QtWidgets import QApplication; "
    "a=QApplication(sys.argv); {case}; "
    "a.processEvents(); w.close(); w.deleteLater(); a.processEvents(); print('t1')"
)

for name, case in CASES.items():
    code = SNIPPET.format(case=case)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"{name:>14}: exit={proc.returncode}")