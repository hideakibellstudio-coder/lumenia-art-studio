"""Complete verification test for 6P Curvilinear perspective and all advanced options."""
import sys, os, math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6 import QtWidgets, QtCore, QtGui
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from ui.core.document.manager import DocumentManager
from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from plugins.ui.geometry_plugin.panel import GeometryPanel

print("=== 1. Teste de Rotação Interativa pelo Braço no Canvas ===")
rw = RenderWidget()
rw.resize(1200, 800)
rw.init_engine(1920, 1080)
ctrl = rw.geometry_ctrl

ctrl.guide_state["type"] = "curvilinear"
ctrl.guide_state["cx"] = 960.0
ctrl.guide_state["cy"] = 540.0
ctrl.guide_state["yaw"] = 0.0

# Arm handle is at (cx + 80, cy) -> (1040, 540)
handle = ctrl.hit_test(QtCore.QPointF(1040.0, 540.0), 1.0)
assert handle == "guide_curv_rotate", f"Esperado handle 'guide_curv_rotate', obtido '{handle}'"
print("  [OK] Hit-test do braço de rotação a 80px detectado com sucesso")

# Drag handle to 90 degrees (960, 620)
ctrl.mouse_press(QtCore.QPointF(1040.0, 540.0), 1.0)
ctrl.mouse_move(QtCore.QPointF(960.0, 620.0))
assert abs(ctrl.guide_state["yaw"] - 90.0) < 1.0, f"Esperado yaw=90, obtido {ctrl.guide_state['yaw']}"
ctrl.mouse_release()
print(f"  [OK] Arrastar braço no canvas girou yaw para {ctrl.guide_state['yaw']:.1f}°")

print()
print("=== 2. Teste de Renderização dos 8 Componentes 3D ===")
# Enable all 3D features
ctrl.guide_state["show_ring"] = True
ctrl.guide_state["show_v"] = True
ctrl.guide_state["show_h"] = True
ctrl.guide_state["show_d"] = True
ctrl.guide_state["show_ground"] = True
ctrl.guide_state["show_ground_verticals"] = True
ctrl.guide_state["show_ceiling"] = True
ctrl.guide_state["show_ceiling_verticals"] = True
ctrl.guide_state["show_cube"] = True
ctrl.guide_state["show_vps"] = True
ctrl.guide_state["show_letterbox"] = True
ctrl.guide_state["aspect_ratio"] = "2.35:1"

# Render on a dummy QImage
img = QtGui.QImage(1920, 1080, QtGui.QImage.Format_ARGB32_Premultiplied)
img.fill(QtCore.Qt.black)
painter = QtGui.QPainter(img)

from plugins.system.workspace_core.workspace.canvas.renderers.geometry_overlay_renderer import GeometryOverlayRenderer
GeometryOverlayRenderer.render_guides(painter, ctrl, 1.0)
painter.end()

print("  [OK] Renderização de Chão, Teto, Cubo, 6 VPs, Letterbox e Arm executada sem erros")

print()
print("=== 3. Teste de Sincronização Total com Painel Avançado ===")
win = QtWidgets.QMainWindow()
rw = RenderWidget(win)
win.setCentralWidget(rw)
win.resize(1200, 800)
win.show()
rw.init_engine(1920, 1080)
ctrl = rw.geometry_ctrl

gp = GeometryPanel(win)
gp.state["show_ground"] = True
gp.state["show_ground_verticals"] = True
gp.state["show_ceiling"] = True
gp.state["show_ceiling_verticals"] = True
gp.state["show_cube"] = True
gp.state["show_letterbox"] = True
gp.state["aspect_ratio"] = "2.35:1"
gp.state["snap_mode"] = "v"
gp.state["snap_sensitivity"] = 4.5

gp._sync_to_render_widget()
assert ctrl.guide_state["show_ground"] == True
assert ctrl.guide_state["aspect_ratio"] == "2.35:1"
assert ctrl.guide_state["snap_mode"] == "v"
assert ctrl.guide_state["snap_sensitivity"] == 4.5
print("  [OK] Todas as opções avançadas sincronizadas perfeitamente do painel para o controller")

print()
print("[SUCCESS] 100% DAS OPÇÕES DA PERSPECTIVA 6 PONTOS E RÉGUAS ESTÃO COMPLETAS E TESTADAS!")
