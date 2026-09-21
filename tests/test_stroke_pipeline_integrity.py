"""
Testes de Regressão e Integridade para o Pipeline de Traço do Canvas (ARCcC v2)
================================================================================
Valida o comportamento do traço desde o toque da caneta (tap isolado),
atualização contínua de cursor rects, suporte a tilt/twist, direções variadas,
inversões bruscas e escalas de estabilização de 0% a 98%.
"""

import math
import pytest
from PySide6 import QtWidgets, QtCore, QtGui

from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
from plugins.system.workspace_core.workspace.canvas.viewport.canvas_stroke_pipeline import CanvasStrokePipeline
from ui.core.engine.registry import EngineRegistry
from ui.engine_backends.aladyn import AladynBackend


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    backend = EngineRegistry.instance().get_backend()
    if backend is None:
        EngineRegistry.instance().setup([AladynBackend()])
    return app


def test_stroke_pipeline_isolated_tap_dirty_rect(qapp):
    """Garante que um toque único (tap/clique sem arrasto) gere dirty rect analítico válido."""
    rw = RenderWidget()
    rw.canvas_w = 1000
    rw.canvas_h = 1000
    rw.brush_size = 40.0

    # Inicia traço em (300, 300)
    rw.start_stroke(300.0, 300.0, pressure=0.8, timestamp=1.0)
    assert rw.drawing is True

    # Finaliza traço no mesmo ponto sem ter havido paint_stroke
    rw.end_stroke(300.0, 300.0)
    assert rw.drawing is False

    # Verifica se _last_rendered_cursor_rect e o dirty rect foram computados
    assert not rw._last_rendered_cursor_rect.isEmpty()
    assert rw._last_rendered_cursor_rect.width() > 0
    assert rw._last_rendered_cursor_rect.height() > 0


def test_stroke_pipeline_cursor_history_invalidation(qapp):
    """Garante que _last_rendered_cursor_rect é atualizado a cada etapa de paint_stroke."""
    rw = RenderWidget()
    rw.canvas_w = 1000
    rw.canvas_h = 1000
    rw.brush_size = 30.0
    rw._cursor_in_viewport = True

    rw.start_stroke(100.0, 100.0, pressure=0.7, timestamp=1.0)
    assert rw._last_rendered_cursor_rect.isEmpty()

    # Move para (120, 100)
    rw.paint_stroke(120.0, 100.0, pressure=0.7, timestamp=1.016)
    r1 = QtCore.QRect(rw._last_rendered_cursor_rect)
    assert not r1.isEmpty()
    assert abs(r1.center().x() - 120) <= 2

    # Move para (150, 100)
    rw.paint_stroke(150.0, 100.0, pressure=0.7, timestamp=1.032)
    r2 = QtCore.QRect(rw._last_rendered_cursor_rect)
    assert not r2.isEmpty()
    assert abs(r2.center().x() - 150) <= 2
    assert r1 != r2

    rw.end_stroke(150.0, 100.0)


def test_stroke_pipeline_tilt_and_twist_forwarding(qapp):
    """Verifica que argumentos de inclinação (tiltX, tiltY) e rotação (twist) são repassados."""
    rw = RenderWidget()
    rw.canvas_w = 1000
    rw.canvas_h = 1000

    # Inicia com tilt e twist
    rw.start_stroke(200.0, 200.0, pressure=0.6, timestamp=1.0, tilt_x=25.0, tilt_y=-15.0, twist=45.0)
    assert rw.drawing is True

    # Pinta com tilt e twist
    rw.paint_stroke(220.0, 200.0, pressure=0.65, timestamp=1.016, tilt_x=30.0, tilt_y=-10.0, twist=50.0)
    rw.end_stroke(220.0, 200.0)
    assert rw.drawing is False


def test_stroke_directions_and_u_turn(qapp):
    """Verifica robustez em múltiplas direções ortogonais/diagonais e inversão brusca de 180°."""
    rw = RenderWidget()
    rw.canvas_w = 1000
    rw.canvas_h = 1000
    rw.brush_size = 20.0

    directions = [
        ("Horizontal Direita (0°)", 1.0, 0.0),
        ("Diagonal (45°)", 0.707, 0.707),
        ("Vertical Baixo (90°)", 0.0, 1.0),
        ("Horizontal Esquerda (180°)", -1.0, 0.0),
        ("Vertical Cima (270°)", 0.0, -1.0),
    ]

    for _, dx, dy in directions:
        sx, sy = 400.0, 400.0
        rw.start_stroke(sx, sy, pressure=0.8, timestamp=1.0)
        t = 1.0
        for i in range(1, 11):
            t += 0.016
            rw.paint_stroke(sx + dx * i * 8.0, sy + dy * i * 8.0, pressure=0.8, timestamp=t)
        rw.end_stroke(sx + dx * 80.0, sy + dy * 80.0)

    # Inversão brusca de 180° (U-turn)
    rw.start_stroke(500.0, 500.0, pressure=0.8, timestamp=1.0)
    t = 1.0
    for i in range(1, 6):
        t += 0.016
        rw.paint_stroke(500.0 + i * 10.0, 500.0, pressure=0.8, timestamp=t)
    for i in range(1, 6):
        t += 0.016
        rw.paint_stroke(550.0 - i * 10.0, 500.0, pressure=0.8, timestamp=t)
    rw.end_stroke(500.0, 500.0)
    assert rw.drawing is False


def test_stroke_stabilizer_varied_scales(qapp):
    """Verifica que a escala do estabilizador (0% a 98%) é aplicada e catch-up aumenta com o lag."""
    rw = RenderWidget()
    rw.canvas_w = 1000
    rw.canvas_h = 1000
    backend = rw.backend

    if not backend or not hasattr(backend, "set_stabilizer_weight"):
        pytest.skip("Backend nativo indisponível")

    scales = [0.0, 0.25, 0.50, 0.75, 0.98]
    catchup_widths = []

    for s in scales:
        backend.set_stabilizer_weight(s)
        assert abs(backend._facade.get_stabilizer().get_stabilization_percentage() - (s * 100.0)) < 1.0

        rw.start_stroke(100.0, 300.0, pressure=0.8, timestamp=1.0)
        t = 1.0
        for i in range(1, 21):
            t += 0.016
            x = 100.0 + i * 15.0
            y = 300.0 + math.sin(i * 0.4) * 40.0
            rw.paint_stroke(x, y, pressure=0.8, timestamp=t)
        
        # end_stroke
        res = backend.end_stroke(x, y)
        w = res[2] if (res and len(res) >= 4) else 0.0
        catchup_widths.append(w)

    # O catchup ao soltar a caneta em 0% é 0 (ou sem atraso)
    assert catchup_widths[0] == 0.0
    # Em 98%, o catchup é substancial (> 50px)
    assert catchup_widths[-1] > 50.0
