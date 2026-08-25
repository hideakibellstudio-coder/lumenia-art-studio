"""Comprehensive verification tests for the clean GeometryToolController architecture."""
import sys, os, math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6 import QtWidgets, QtCore, QtGui
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from ui.core.engine.registry import EngineRegistry
from ui.engine_backends.aladyn import AladynBackend
from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

backend = AladynBackend()
backend.init_renderer(0, 1000, 1000, 1000, 1000)
EngineRegistry.instance().setup([backend])

rw = RenderWidget()
rw.resize(1280, 720)

print("=== 1. TESTE: Preservação do Pivô após Movimentação do Usuário ===")
rw.geometry_ctrl.sym_state["cx"] = 400.0
rw.geometry_ctrl.sym_state["cy"] = 300.0
rw.init_engine(2000, 1000)
assert rw.geometry_ctrl.sym_state["cx"] == 1000.0
assert rw.geometry_ctrl.sym_state["cy"] == 500.0
print("  [OK] Primeira inicialização reseta pivô do default (400,300) -> (1000,500)")

rw.geometry_ctrl.sym_state["cx"] = 300.0
rw.geometry_ctrl.sym_state["cy"] = 200.0
rw.geometry_ctrl.center_on_document(3840, 2160)
assert rw.geometry_ctrl.sym_state["cx"] == 300.0
print("  [OK] Pivô movido pelo usuário (300,200) preservado após center_on_document")

print()
print("=== 2. TESTE: Snap da Régua Reta com Offset Paralelo (Infinite Painter) ===")
rw.geometry_ctrl.guide_state["type"] = "straight"
rw.geometry_ctrl.guide_state["p0"] = QtCore.QPointF(0, 500)
rw.geometry_ctrl.guide_state["p1"] = QtCore.QPointF(2000, 500)

rw.geometry_ctrl.start_stroke_snap((600.0, 520.0))
# Drawing horizontally with vertical hand jitter to (800, 535)
snapped_x, snapped_y = rw.geometry_ctrl.snap_point(800.0, 535.0)
assert abs(snapped_y - 520.0) < 1e-4, f"Esperado Y=520 na linha paralela de contato, obtido {snapped_y}"
assert abs(snapped_x - 800.0) < 1e-4
rw.geometry_ctrl.mouse_release()
print("  [OK] Régua reta: traço inicia exatamente no toque e desliza em linha paralela sem pular")

print()
print("=== 3. TESTE: Curvilínea 6P - Geração de 3 Curvas Dinâmicas e Hover ===")
rw.geometry_ctrl.guide_state["type"] = "curvilinear"
rw.geometry_ctrl.guide_state["cx"] = 1000.0
rw.geometry_ctrl.guide_state["cy"] = 500.0
rw.geometry_ctrl.guide_state["fov"] = 130.0
rw.geometry_ctrl.guide_state["show_v"] = True
rw.geometry_ctrl.guide_state["show_h"] = True
rw.geometry_ctrl.guide_state["show_d"] = True

# Hover test (point offset from center so all 3 orthogonal 3D planes V, H, D are non-degenerate)
rw.geometry_ctrl.handle_hover(QtCore.QPointF(1050.0, 520.0))
assert len(rw.geometry_ctrl.dynamic_hover_curves) == 3, f"Esperado 3 curvas dinâmicas, obtido {len(rw.geometry_ctrl.dynamic_hover_curves)}"
print(f"  [OK] Hover gerou {len(rw.geometry_ctrl.dynamic_hover_curves)} curvas dinâmicas no ponto (1050, 520)")

# Stroke test with intent locking
rw.geometry_ctrl.start_stroke_snap((1000.0, 500.0))
# Drag 20px vertically
snapped = rw.geometry_ctrl.snap_point(1000.0, 520.0)
assert rw.geometry_ctrl.locked_curve is not None, "Esperado curva travada após arrasto de 20px"
assert rw.geometry_ctrl.locked_curve["family"] == "v", f"Esperado família 'v', obtido {rw.geometry_ctrl.locked_curve['family']}"
rw.geometry_ctrl.mouse_release()
print(f"  [OK] Traço travou automaticamente na curva correta ({rw.geometry_ctrl.locked_curve['family'] if rw.geometry_ctrl.locked_curve else 'v'})")

print()
print("=== 4. TESTE: Perspectiva 2P com Vertical Perpendicular ao Horizonte ===")
rw.geometry_ctrl.guide_state["type"] = "two_point"
rw.geometry_ctrl.guide_state["vpA"] = QtCore.QPointF(200, 500)
rw.geometry_ctrl.guide_state["vpB"] = QtCore.QPointF(1800, 500)

rw.geometry_ctrl.start_stroke_snap((1000.0, 500.0))
# Drag downward (vertical)
snapped = rw.geometry_ctrl.snap_point(1000.0, 560.0)
assert rw.geometry_ctrl.locked_dir is not None
assert abs(rw.geometry_ctrl.locked_dir[0]) < 1e-4 and abs(rw.geometry_ctrl.locked_dir[1]) > 0.9, f"Esperado direção vertical (0, 1), obtido {rw.geometry_ctrl.locked_dir}"
rw.geometry_ctrl.mouse_release()
print("  [OK] Perspectiva 2P travou na direção vertical perpendicular ao horizonte")

print()
print("[SUCCESS] TODOS OS TESTES DE GEOMETRIA, SIMETRIA E SNAPPING PASSARAM 100%!")
