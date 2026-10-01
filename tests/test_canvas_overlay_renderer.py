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
    # O teste cria o contexto que usa: depender do que sobrou de outro teste
    # quebrava quando um teste anterior fechava todos os documentos.
    backend = EngineRegistry.instance().get_backend()
    backend.set_active_document_context("overlay-renderer-test", SIZE, SIZE)
    widget = RenderWidget()
    widget.resize(SIZE, SIZE)
    yield widget
    if widget.transform_ctrl.active:
        widget.transform_ctrl.cancel()
    backend.clear_selection()
    backend.close_document_context("overlay-renderer-test")
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


# -- the loupe shows the canvas under the cursor, asking the engine for that patch only --------

def _paint_block(backend, x, y, size, color):
    assert backend.paste_rgba_buffer_on_active_layer(x, y, size, size, bytes(color + (255,)) * (size * size))


class _CountingBackend:
    """The real backend, with the reads of the canvas counted."""

    def __init__(self, backend):
        self._backend = backend
        self.whole_canvas_reads = 0
        self.regions = []

    def get_qimage(self):
        self.whole_canvas_reads += 1
        return self._backend.get_qimage()

    def get_display_image(self, zoom, region):
        self.regions.append(QtCore.QRect(region))
        return self._backend.get_display_image(zoom, region)


def _screen_of(canvas, world_x, world_y):
    """The screen position that `to_canvas` maps to (world_x, world_y): the widget has the one direction only."""
    origin = canvas.to_canvas(0.0, 0.0, 1.0, 0.0)
    step = canvas.to_canvas(100.0, 100.0, 1.0, 0.0)
    scale_x, scale_y = (step.x - origin.x) / 100.0, (step.y - origin.y) / 100.0
    return QtCore.QPointF((world_x - origin.x) / scale_x, (world_y - origin.y) / scale_y)


def test_the_loupe_magnifies_the_pixels_under_the_cursor(canvas):
    backend = EngineRegistry.instance().get_backend()
    _paint_block(backend, 100, 100, 40, (30, 200, 60))
    image = draw(OverlayRenderer.render_color_loupe, _screen_of(canvas, 120.0, 120.0), canvas, backend,
                 QtGui.QColor(255, 0, 0), QtGui.QColor(0, 0, 255))
    # The loupe shades its content (a vignette), so look for "clearly green", not the exact colour.
    greens = sum(1 for y in range(0, SIZE, 2) for x in range(0, SIZE, 2)
                 if (c := image.pixelColor(x, y)).green() > 60 and c.green() > 2 * c.red() and c.green() > 2 * c.blue())
    assert greens > 100, "the magnified patch should be the green block under the cursor"


def test_the_loupe_reads_the_patch_and_not_the_whole_canvas(canvas):
    backend = _CountingBackend(EngineRegistry.instance().get_backend())
    draw(OverlayRenderer.render_color_loupe, _screen_of(canvas, 120.0, 120.0), canvas, backend,
         QtGui.QColor(255, 0, 0), QtGui.QColor(0, 0, 255))
    assert backend.whole_canvas_reads == 0, "the loupe copied the whole canvas to crop 18 pixels"
    assert len(backend.regions) == 1 and backend.regions[0].width() <= 18 and backend.regions[0].height() <= 18


def test_the_loupe_at_the_canvas_edge_asks_only_for_what_is_inside(canvas):
    backend = _CountingBackend(EngineRegistry.instance().get_backend())
    draw(OverlayRenderer.render_color_loupe, _screen_of(canvas, 2.0, 2.0), canvas, backend,
         QtGui.QColor(255, 0, 0), QtGui.QColor(0, 0, 255))
    assert backend.regions, "a corner of the canvas is still inside it"
    assert all(QtCore.QRect(0, 0, SIZE, SIZE).contains(region) for region in backend.regions)
    assert backend.regions[0].width() < 18 or backend.regions[0].height() < 18, "the patch was clipped to the canvas"


def test_the_loupe_far_outside_the_canvas_asks_for_nothing(canvas):
    backend = _CountingBackend(EngineRegistry.instance().get_backend())
    draw(OverlayRenderer.render_color_loupe, _screen_of(canvas, -500.0, -500.0), canvas, backend,
         QtGui.QColor(255, 0, 0), QtGui.QColor(0, 0, 255))
    assert backend.regions == [] and backend.whole_canvas_reads == 0
