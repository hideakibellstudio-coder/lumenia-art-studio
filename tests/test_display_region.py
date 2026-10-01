"""The screen asks the engine for the rectangle it paints, not for the whole canvas (S1.1, D4).

At zoom 100% on a 4K document every repaint copied the canvas twice (C++ to bytes,
bytes to QImage) to draw a few pixels: 40 ms (benchmarks/app_ui_paths.py,
`repaint_zoom100`, 2026-10-01). The engine now hands out a region
(`get_display_region`), the backend wraps it in a `DisplayImage`, and the viewport
paints from that. These tests pin that the region is the same pixels the whole-canvas
copy had, with and without a colour profile, at the edges and with a rotated view,
and that the paint no longer asks for the whole canvas.
"""

from __future__ import annotations

import random

import pytest
from PySide6 import QtCore, QtGui

from ui.core.document.manager import DocumentManager
from ui.core.engine.display_image import FILTER_MARGIN_PX, DisplayImage, region_to_request
from ui.core.engine.registry import EngineRegistry

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

WIDTH, HEIGHT = 211, 137  # odd on purpose: no tile or row size divides them


def _noise(width: int, height: int, seed: int = 7) -> bytes:
    """Opaque noise: any shifted row or column shows up as different bytes."""
    rng = random.Random(seed)
    return bytes(b for _ in range(width * height) for b in (rng.randrange(256), rng.randrange(256), rng.randrange(256), 255))


@pytest.fixture
def facade():
    engine = native.PaintEngineFacade(WIDTH, HEIGHT)
    engine.paste_rgba_buffer_on_active_layer(0, 0, WIDTH, HEIGHT, _noise(WIDTH, HEIGHT), 0, 1.0)
    return engine


def _slice(whole: bytes, x: int, y: int, w: int, h: int) -> bytes:
    rows = (whole[((y + r) * WIDTH + x) * 4:((y + r) * WIDTH + x + w) * 4] for r in range(h))
    return b"".join(rows)


# -- the engine ---------------------------------------------------------------

@pytest.mark.parametrize("rect", [(0, 0, 1, 1), (10, 20, 50, 40), (0, 0, WIDTH, HEIGHT),
                                  (WIDTH - 5, HEIGHT - 3, 5, 3), (100, 0, 111, 1)])
def test_the_region_is_the_same_pixels_as_that_part_of_the_whole_canvas(facade, rect):
    whole = bytes(facade.get_display_pixel_buffer())
    assert facade.get_display_region(*rect) == _slice(whole, *rect)


@pytest.mark.parametrize("profile_id", [1, 2, 8, 12])
def test_a_colour_profile_is_applied_to_the_region_as_to_the_whole_canvas(facade, profile_id):
    facade.set_color_profile(profile_id)
    whole = bytes(facade.get_display_pixel_buffer())
    rect = (17, 9, 63, 41)
    assert facade.get_display_region(*rect) == _slice(whole, *rect)
    facade.set_color_profile(0)
    assert facade.get_display_region(*rect) != _slice(whole, *rect), "the profile changed nothing: the test proves nothing"


@pytest.mark.parametrize("rect", [(-1, 0, 10, 10), (0, -1, 10, 10), (0, 0, 0, 5), (0, 0, 5, 0),
                                  (WIDTH - 4, 0, 5, 5), (0, HEIGHT - 4, 5, 5), (0, 0, WIDTH + 1, 5)])
def test_a_region_outside_the_canvas_is_refused_not_clipped(facade, rect):
    with pytest.raises(ValueError):
        facade.get_display_region(*rect)


def test_the_region_follows_the_composite_after_a_change(facade):
    facade.paste_rgba_buffer_on_active_layer(30, 30, 4, 4, bytes([255, 0, 0, 255] * 16), 0, 1.0)
    assert facade.get_display_region(30, 30, 4, 4) == bytes([255, 0, 0, 255] * 16)


# -- the backend --------------------------------------------------------------

@pytest.fixture
def backend():
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    backend = AladynBackend()
    backend.set_active_document_context("region", WIDTH, HEIGHT)
    backend._facade.paste_rgba_buffer_on_active_layer(0, 0, WIDTH, HEIGHT, _noise(WIDTH, HEIGHT), 0, 1.0)
    return backend


def _bits(image: QtGui.QImage) -> bytes:
    return bytes(image.constBits())[: image.sizeInBytes()]


def test_at_working_zoom_the_backend_returns_just_the_region_and_where_it_sits(backend):
    display = backend.get_display_image(1.0, QtCore.QRect(20, 30, 60, 40))
    assert isinstance(display, DisplayImage)
    assert (display.image.width(), display.image.height()) == (60, 40)
    assert display.scale == 1.0 and display.origin == (20, 30)
    assert _bits(display.image) == _slice(bytes(backend.get_display_pixel_buffer()), 20, 30, 60, 40)


def test_a_region_that_overhangs_the_canvas_is_cut_to_it(backend):
    display = backend.get_display_image(2.0, QtCore.QRect(-10, HEIGHT - 5, WIDTH + 30, 40))
    assert (display.image.width(), display.image.height()) == (WIDTH, 5)
    assert display.origin == (0, HEIGHT - 5)


def test_a_region_entirely_outside_the_canvas_gives_nothing(backend):
    assert backend.get_display_image(1.0, QtCore.QRect(WIDTH + 5, 0, 10, 10)) is None


def test_zoomed_out_it_is_the_prefiltered_level_cut_to_the_region(backend):
    level_bytes, level_w, level_h, scale = backend._facade.get_display_pixel_buffer_lod(2)
    display = backend.get_display_image(0.25, QtCore.QRect(40, 20, 100, 60))
    assert display.scale == scale == 0.25
    x, y = display.origin
    assert (x, y) == (10, 5)
    w, h = display.image.width(), display.image.height()
    rows = (level_bytes[((y + r) * level_w + x) * 4:((y + r) * level_w + x + w) * 4] for r in range(h))
    assert _bits(display.image) == b"".join(rows)
    assert (w, h) == (25, 15)  # the region at 1/4 scale: 100/4 x 60/4


def test_zoomed_out_a_region_that_overhangs_is_cut_to_the_level(backend):
    display = backend.get_display_image(0.25, QtCore.QRect(-50, -50, WIDTH + 100, HEIGHT + 100))
    level_w, level_h = backend._facade.get_lod_size(2)
    assert (display.image.width(), display.image.height()) == (level_w, level_h) and display.origin == (0, 0)


def test_the_image_survives_after_the_native_buffer_could_have_been_reused(backend):
    display = backend.get_display_image(1.0, QtCore.QRect(0, 0, 32, 32))
    expected = _bits(display.image)
    backend._facade.paste_rgba_buffer_on_active_layer(0, 0, 32, 32, bytes([0, 0, 0, 255] * 1024), 0, 1.0)
    backend.get_display_image(1.0, QtCore.QRect(0, 0, 64, 64))
    assert _bits(display.image) == expected


def test_source_rect_maps_canvas_pixels_into_the_image():
    image = QtGui.QImage(60, 40, QtGui.QImage.Format_RGBA8888)
    region = DisplayImage(image, 1.0, (20, 30))
    assert region.source_rect(QtCore.QRect(25, 35, 10, 10)) == QtCore.QRect(5, 5, 10, 10)
    level = DisplayImage(QtGui.QImage(100, 50, QtGui.QImage.Format_RGBA8888), 0.5, (0, 0))
    assert level.source_rect(QtCore.QRect(40, 20, 100, 40)) == QtCore.QRect(20, 10, 50, 20)
    assert region.source_rect(QtCore.QRect(500, 500, 10, 10)).isEmpty()


def test_the_request_adds_the_filter_margin_and_stays_inside_the_canvas():
    canvas = QtCore.QRect(0, 0, 100, 100)
    assert region_to_request(QtCore.QRect(40, 40, 10, 10), canvas) == QtCore.QRect(
        40 - FILTER_MARGIN_PX, 40 - FILTER_MARGIN_PX, 10 + 2 * FILTER_MARGIN_PX, 10 + 2 * FILTER_MARGIN_PX)
    assert region_to_request(QtCore.QRect(0, 0, 10, 10), canvas) == QtCore.QRect(0, 0, 10 + FILTER_MARGIN_PX, 10 + FILTER_MARGIN_PX)


# -- the viewport -------------------------------------------------------------

class _WholeCanvasBackend:
    """What the viewport used to receive: the whole canvas, always drawn from its own origin."""

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        return getattr(self._real, name)

    def get_display_image(self, zoom, region):
        facade = self._real._facade
        level = facade.get_best_lod_level(zoom)
        if level == 0:
            return DisplayImage(self._real.get_qimage(), 1.0)
        data, width, height, scale = facade.get_display_pixel_buffer_lod(level)
        return DisplayImage(QtGui.QImage(data, width, height, width * 4, QtGui.QImage.Format_RGBA8888).copy(), scale)


@pytest.fixture
def viewport(qapp, backend):
    from ui.plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

    registry = EngineRegistry.instance()
    previous = registry.get_backend()
    registry.set_backend(backend)
    document = DocumentManager.instance().new_document(WIDTH, HEIGHT, name="region", activate=True)
    widget = RenderWidget()
    widget.resize(180, 150)
    widget.show()
    qapp.processEvents()  # the first resize centres the canvas at "fit"; the tests set their own zoom after it
    try:
        yield widget, registry, backend
    finally:
        widget.close()
        widget.deleteLater()
        registry.set_backend(previous)
        DocumentManager.instance().close_document(document.uid)


def _paint(widget, region: QtCore.QRect | None) -> bytes:
    target = QtGui.QImage(widget.size(), QtGui.QImage.Format_ARGB32)
    target.fill(QtGui.QColor(1, 2, 3))
    widget.render(target, QtCore.QPoint(0, 0), QtGui.QRegion(region) if region else QtGui.QRegion(widget.rect()))
    return _bits(target)


@pytest.mark.parametrize("zoom, rotation", [(1.0, 0.0), (1.0, 30.0), (1.5, 0.0), (2.37, 0.0), (3.0, 17.0), (0.9, 0.0), (0.4, 0.0)])
@pytest.mark.parametrize("region", [None, QtCore.QRect(37, 21, 77, 59), QtCore.QRect(0, 0, 40, 30)],
                         ids=["whole_widget", "partial", "corner"])
def test_the_repaint_from_a_region_draws_the_pixels_the_whole_canvas_drew(viewport, zoom, rotation, region):
    widget, registry, backend = viewport
    widget.zoom, widget.pan_x, widget.pan_y, widget.rotation = zoom, 13.0, -9.0, rotation
    widget.publish_view(zoom_changed=True)
    assert widget.zoom == zoom, "the view was reset: the test would not run at the zoom it names"
    from_region = _paint(widget, region)
    registry.set_backend(_WholeCanvasBackend(backend))
    try:
        from_whole_canvas = _paint(widget, region)
    finally:
        registry.set_backend(backend)
    assert from_region == from_whole_canvas
    assert from_region != _paint_blank(widget), "nothing was painted: the comparison proves nothing"


def _paint_blank(widget) -> bytes:
    target = QtGui.QImage(widget.size(), QtGui.QImage.Format_ARGB32)
    target.fill(QtGui.QColor(1, 2, 3))
    return _bits(target)


def test_painting_at_working_zoom_never_copies_the_whole_canvas(viewport):
    widget, registry, backend = viewport
    widget.zoom = 1.0
    widget.publish_view(zoom_changed=True)
    assert widget.zoom == 1.0
    whole_canvas_calls = []
    for name in ("get_qimage", "get_display_pixel_buffer"):
        original = getattr(backend, name)
        setattr(backend, name, lambda *args, _n=name, _o=original, **kwargs: (whole_canvas_calls.append(_n), _o(*args, **kwargs))[1])
    _paint(widget, None)
    assert whole_canvas_calls == []
