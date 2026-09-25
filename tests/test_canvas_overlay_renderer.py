"""Desenho das sobreposições do canvas: `OverlayRenderer`.

Tinha 7% de cobertura em 2026-09-25. Cada função desenha num QImage
transparente com o canvas e o motor reais, e o teste confere que a marca
apareceu onde devia (e que, sem estado, nada é desenhado): formigas da
seleção, prévia do retângulo/elipse e do laço, alças da transformação livre e
do modo Distorcer, prévia de forma e a lupa do conta-gotas.
"""
from __future__ import annotations

import pytest
from PySide6 import QtCore, QtGui

pytest.importorskip("aladyn_engine_native")

from ui.core.engine.registry import EngineRegistry  # noqa: E402
from ui.infrastructure.bridge_client.aladyn import AladynBackend  # noqa: E402
from ui.plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget  # noqa: E402
from ui.plugins.system.workspace_core.workspace.canvas.renderers.overlay_renderer import OverlayRenderer  # noqa: E402
from ui.plugins.system.workspace_core.workspace.canvas.tools import transform_distort  # noqa: E402

SIZE = 300


@pytest.fixture
def canvas(qapp):
    if EngineRegistry.instance().get_backend() is None:
        EngineRegistry.instance().setup([AladynBackend()])
    widget = RenderWidget()
    widget.resize(SIZE, SIZE)
    yield widget
    backend = EngineRegistry.instance().get_backend()
    if widget.transform_ctrl.active:
        widget.transform_ctrl.cancel()
    backend.clear_selection()
    widget.close()
    widget.deleteLater()


def draw(fn, *args) -> QtGui.QImage:
    image = QtGui.QImage(SIZE, SIZE, QtGui.QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(image)
    try:
        fn(painter, *args)
    finally:
        painter.end()
    return image


def painted(image: QtGui.QImage, rect: QtCore.QRect | None = None) -> int:
    area = rect or image.rect()
    return sum(1 for y in range(area.top(), area.bottom() + 1, 2) for x in range(area.left(), area.right() + 1, 2)
               if image.pixelColor(x, y).alpha() > 0)


def test_selection_marching_ants_follow_the_selection(canvas):
    backend = EngineRegistry.instance().get_backend()
    backend.select_rect(40, 40, 100, 60)
    image = draw(OverlayRenderer.render_selection_overlay, backend, 1.0, 0.0, SIZE, SIZE)
    assert painted(image, QtCore.QRect(36, 36, 108, 8)) > 0, "borda de cima"
    assert painted(image, QtCore.QRect(60, 60, 60, 20)) == 0, "o miolo não é pintado"


def test_no_selection_draws_nothing(canvas):
    backend = EngineRegistry.instance().get_backend()
    backend.clear_selection()
    assert painted(draw(OverlayRenderer.render_selection_overlay, backend, 1.0, 0.0, SIZE, SIZE)) == 0


@pytest.mark.parametrize("tool", ["rect_select", "ellipse_select"])
def test_rect_and_ellipse_drag_preview(canvas, tool):
    canvas.active_tool = tool
    ctrl = canvas.selection_ctrl
    ctrl.drag_active = True
    ctrl.drag_start, ctrl.drag_current = QtCore.QPointF(50, 50), QtCore.QPointF(200, 150)
    image = draw(OverlayRenderer.render_selection_drag_preview, canvas, 1.0)
    assert painted(image) > 20
    assert painted(image, QtCore.QRect(0, 0, 40, 40)) == 0


@pytest.mark.parametrize("lasso_type", ["freehand", "polygonal"])
def test_lasso_preview_draws_the_path(canvas, lasso_type):
    canvas.active_tool = "lasso"
    ctrl = canvas.selection_ctrl
    ctrl.lasso_settings["lasso_type"] = lasso_type
    ctrl.lasso_is_drawing = lasso_type == "freehand"
    ctrl.lasso_points = [QtCore.QPointF(60, 60), QtCore.QPointF(220, 60), QtCore.QPointF(220, 200)]
    ctrl.lasso_hover_pt = QtCore.QPointF(100, 200) if lasso_type == "polygonal" else None
    image = draw(OverlayRenderer.render_selection_drag_preview, canvas, 1.0)
    assert painted(image, QtCore.QRect(80, 54, 120, 12)) > 0, "trecho entre os dois primeiros pontos"


def _start_transform(canvas):
    backend = EngineRegistry.instance().get_backend()
    assert backend.paste_rgba_buffer_on_active_layer(100, 100, 40, 40, bytes([200, 30, 30, 255]) * 1600)
    assert canvas.transform_ctrl.start_mode()


def test_free_transform_draws_the_source_and_the_handles(canvas):
    _start_transform(canvas)
    image = draw(OverlayRenderer.render_transform_overlay, canvas.transform_ctrl, 1.0)
    assert painted(image, QtCore.QRect(110, 110, 20, 20)) > 0, "a imagem de origem"
    assert painted(image, QtCore.QRect(94, 94, 12, 12)) > 0, "alça do canto superior esquerdo"


def test_distort_mode_draws_the_quad(canvas):
    _start_transform(canvas)
    ctrl = canvas.transform_ctrl
    ctrl.quad = transform_distort.rect_corners(ctrl.source_rect)
    image = draw(OverlayRenderer.render_transform_overlay, ctrl, 1.0)
    assert painted(image, QtCore.QRect(94, 94, 12, 12)) > 0


def test_inactive_transform_draws_nothing(canvas):
    assert painted(draw(OverlayRenderer.render_transform_overlay, canvas.transform_ctrl, 1.0)) == 0


@pytest.mark.parametrize("shape", ["shape_line", "shape_rect", "shape_ellipse", "shape_polygon", "shape_star"])
def test_shape_preview(canvas, shape):
    ctrl = canvas.shape_ctrl
    ctrl.settings["shape_type"] = shape
    ctrl.drag_active = True
    ctrl.drag_start, ctrl.drag_current = QtCore.QPointF(60, 60), QtCore.QPointF(240, 220)
    assert painted(draw(OverlayRenderer.render_shape_drag_preview, ctrl)) > 10


def test_eyedrop_loupe_shows_both_colors(canvas):
    backend = EngineRegistry.instance().get_backend()
    image = draw(OverlayRenderer.render_color_loupe, QtCore.QPointF(150, 200), canvas, backend,
                 QtGui.QColor(255, 0, 0), QtGui.QColor(0, 0, 255))
    pixels = [image.pixelColor(x, y) for y in range(0, SIZE, 2) for x in range(0, SIZE, 2)]
    reds = sum(1 for c in pixels if c.red() > 150 and c.green() < 30 and c.blue() < 30)
    blues = sum(1 for c in pixels if c.blue() > 150 and c.red() < 30 and c.green() < 30)
    assert reds > 50 and blues > 50, "meio anel com a cor nova, meio com a antiga"
