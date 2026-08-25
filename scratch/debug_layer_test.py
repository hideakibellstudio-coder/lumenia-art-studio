import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

print("1. Creating MainWindow...")
from ui.boundary.orchestrator.main_window import MainWindow
mw = MainWindow()
print("2. Creating document...")
mw.dm.new_document(800, 600, "Doc Teste")
print("3. Getting layers panel & facade...")
panel = mw.workspace._layers_panel
backend = mw.workspace.canvas_widget.bridge_client
from ui.core.engine.registry import EngineRegistry
backend = EngineRegistry.instance().get_backend()
facade = backend._facade
print(f"4. Initial layer count C++: {facade.get_drawing_layer_count()}, Py: {len(panel.layer_manager.layers)}")

print("5. Calling panel.add_layer('Camada Teste 1')...")
panel.add_layer("Camada Teste 1")
print(f"6. After add - C++: {facade.get_drawing_layer_count()}, Py: {len(panel.layer_manager.layers)}")

print("7. Deleting layer...")
active = panel.layer_manager.get_active_layer()
panel.layer_manager.remove_layer(active.uid)
panel._sync_to_native_engine("delete", active.uid)
print(f"8. After delete - C++: {facade.get_drawing_layer_count()}, Py: {len(panel.layer_manager.layers)}")
print("DONE ALL STEPS!")
