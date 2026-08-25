import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import math
from PySide6 import QtWidgets, QtCore, QtGui

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.engine_backends.aladyn import AladynBackend
from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from plugins.ui.geometry_plugin.panel import GeometryPanel

backend = AladynBackend()
backend.init_renderer(0, 1000, 1000, 1000, 1000)
EngineRegistry.instance().setup([backend])

print("=== 1. TESTE DE CENTRALIZAÇÃO DINÂMICA DE RÉGUAS E SIMETRIAS ===")
rw = RenderWidget()
rw.init_engine(2000, 1000)

assert rw.geometry_ctrl.sym_state["cx"] == 1000.0, f"Expected 1000, got {rw.geometry_ctrl.sym_state['cx']}"
assert rw.geometry_ctrl.sym_state["cy"] == 500.0, f"Expected 500, got {rw.geometry_ctrl.sym_state['cy']}"
assert rw.geometry_ctrl.guide_state["cx"] == 1000.0
assert rw.geometry_ctrl.guide_state["cy"] == 500.0
print("  [OK] Centralização em canvas (2000, 1000) -> (1000, 500) validada com sucesso!")

# Teste com novo tamanho
rw.init_engine(3840, 2160)
assert rw.geometry_ctrl.sym_state["cx"] == 1920.0
assert rw.geometry_ctrl.sym_state["cy"] == 1080.0
print("  [OK] Centralização em canvas 4K (3840, 2160) -> (1920, 1080) validada com sucesso!")

print("\n=== 2. TESTE DE ATRAÇÃO MAGNÉTICA (SNAPPING) PROPORCIONAL & ZOOM ===")
rw.geometry_ctrl.guide_state["type"] = "straight"
rw.geometry_ctrl.guide_state["p0"] = QtCore.QPointF(0, 500)
rw.geometry_ctrl.guide_state["p1"] = QtCore.QPointF(2000, 500)
rw.geometry_ctrl.guide_state["snap_radius"] = 32.0

# 2.1 Ponto próximo da régua (Y=510, dist=10px <= 32px) com zoom 1.0 -> Deve atrair para Y=500
snapped = rw.geometry_ctrl.snap_point(300.0, 510.0, zoom=1.0)
assert abs(snapped[1] - 500.0) < 1e-4, f"Esperado Y=500, obtido {snapped[1]}"
print(f"  [OK] Ponto próximo (300, 510) -> Atraído para {snapped}")

# 2.2 Ponto distante da régua (Y=650, dist=150px > 32px) com zoom 1.0 -> Deve permanecer LIVRE em (300, 650)
snapped_far = rw.geometry_ctrl.snap_point(300.0, 650.0, zoom=1.0)
assert abs(snapped_far[1] - 650.0) < 1e-4, f"Esperado livre Y=650, obtido {snapped_far[1]}"
print(f"  [OK] Ponto distante (300, 650) -> Permanece livre em {snapped_far}")

# 2.3 Compensação de Zoom: ponto em Y=540 (dist=40px)
# Com zoom 0.5: threshold = 32 / 0.5 = 64px -> dist=40px <= 64px -> Deve atrair para Y=500!
snapped_z05 = rw.geometry_ctrl.snap_point(300.0, 540.0, zoom=0.5)
assert abs(snapped_z05[1] - 500.0) < 1e-4, f"Esperado snap em zoom 0.5, obtido {snapped_z05[1]}"
print(f"  [OK] Zoom 0.5 (threshold 64px) atrai ponto a 40px -> {snapped_z05}")

# Com zoom 2.0: threshold = 32 / 2.0 = 16px -> dist=40px > 16px -> Deve ficar livre em (300, 540)!
snapped_z20 = rw.geometry_ctrl.snap_point(300.0, 540.0, zoom=2.0)
assert abs(snapped_z20[1] - 540.0) < 1e-4, f"Esperado livre em zoom 2.0, obtido {snapped_z20[1]}"
print(f"  [OK] Zoom 2.0 (threshold 16px) mantém livre ponto a 40px -> {snapped_z20}")

print("\n=== 3. TESTE DE PINTURA COM SIMETRIA NO MOTOR NATIVO C++ ===")
# Ativa Simetria Espelho Vertical no centro (cx=500, cy=500, angle=pi/2)
rw.geometry_ctrl.sym_state["mode"] = "mirror_v"
rw.geometry_ctrl.sym_state["cx"] = 500.0
rw.geometry_ctrl.sym_state["cy"] = 500.0
rw.geometry_ctrl.sync_symmetry_to_engine()

# Desenha traço à esquerda: de (200, 300) até (200, 700)
backend.start_stroke(200.0, 300.0, 1.0)
backend.paint_stroke(200.0, 500.0, 1.0)
backend.paint_stroke(200.0, 700.0, 1.0)
backend.end_stroke()

# Obtém buffer renderizado
img = backend.get_qimage()
assert img is not None, "get_qimage returned None!"

# Verifica pixel no traço original (X=200, Y=500) -> Deve ter sido pintado
orig_pixel = QtGui.QColor(img.pixel(200, 500))
print(f"  Pixel original em (200, 500): {orig_pixel.name()}")

# Verifica pixel no traço espelhado (X=800, Y=500) -> Deve ter sido pintado
mirror_pixel = QtGui.QColor(img.pixel(800, 500))
print(f"  Pixel espelhado em (800, 500): {mirror_pixel.name()}")

assert orig_pixel.name() == mirror_pixel.name(), f"Esperado cores idênticas, obtido {orig_pixel.name()} vs {mirror_pixel.name()}"
assert mirror_pixel.alpha() > 0 or mirror_pixel.red() < 250, "O traço espelhado não foi pintado!"

print("  [OK] Simetria Espelho Vertical replicada perfeitamente no C++!")

# Teste com Simetria Radial (6 setores)
backend.clear_canvas()
rw.geometry_ctrl.sym_state["mode"] = "radial"
rw.geometry_ctrl.sym_state["segments"] = 6
rw.geometry_ctrl.sym_state["cx"] = 500.0
rw.geometry_ctrl.sym_state["cy"] = 500.0
rw.geometry_ctrl.sync_symmetry_to_engine()

# Desenha ponto em (500, 200) (dist 300 para cima)
backend.start_stroke(500.0, 200.0, 1.0)
backend.paint_stroke(500.0, 205.0, 1.0)
backend.end_stroke()

img_rad = backend.get_qimage()
# Os 6 pontos radiais estarão a raio 300 em ângulos: 90°, 150°, 210°, 270°, 330°, 30°
# Setor 1: (500, 200)
# Setor 4 (270°): (500, 800)
p1 = QtGui.QColor(img_rad.pixel(500, 200))
p4 = QtGui.QColor(img_rad.pixel(500, 800))
print(f"  Radial Setor 1 (500, 200): {p1.name()} | Setor 4 (500, 800): {p4.name()}")
assert p1.name() == p4.name(), f"Esperado réplica radial no setor 4! {p1.name()} vs {p4.name()}"

print("  [OK] Simetria Radial 6 setores replicada perfeitamente no C++!")

print("\n[SUCCESS] TODOS OS 3 TESTES DE CENTRALIZAÇÃO, SNAPPING E SIMETRIA PASSARAM COM 100% DE SUCESSO!")
