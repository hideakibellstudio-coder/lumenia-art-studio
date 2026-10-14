"""`GuideLayerCache`: a camada estática das guias é pintada uma vez e reaproveitada.

Medido em 2026-10-12: com uma guia ligada cada movimento do mouse repintava o canvas inteiro e
retraçava todas as linhas da guia (69 ms na curvilinear completa, 29 ms na isométrica; 5 ms sem guia).
O cache só vale se (1) reaproveitar a imagem quando nada mudou, (2) nunca mostrar uma camada
velha quando algo mudou, e (3) desenhar os mesmos pixels que a pintura direta.
"""
from __future__ import annotations

import numpy as np
import pytest
from PySide6 import QtCore, QtGui

from ui.core.state.geometry_state import default_guide, default_symmetry
from ui.plugins.system.workspace_core.workspace.canvas.renderers.geometry_overlay_renderer import (
    GeometryOverlayRenderer,
)
from ui.plugins.system.workspace_core.workspace.canvas.viewport.guide_layer_cache import (
    GuideLayerCache,
    GuideLayerView,
)

SIZE = QtCore.QSize(320, 240)
BACKGROUND = QtGui.QColor(200, 190, 180)


def make_view(guide=None, symmetry=None, transform=None, size=SIZE, ratio=1.0, zoom=1.0, theme="dark_default"):
    return GuideLayerView(
        size=size, pixel_ratio=ratio, transform=transform or QtGui.QTransform(), zoom=zoom, theme=theme,
        guide=guide if guide is not None else default_guide(),
        symmetry=symmetry if symmetry is not None else default_symmetry(),
    )


def isometric():
    return {**default_guide(), "type": "isometric"}


def mirror():
    return {**default_symmetry(), "mode": "mirror"}


def draw(cache, view, dirty=None):
    """Desenha a camada sobre um fundo liso e devolve os pixels RGBA (alto × largo × 4)."""
    ratio = view.pixel_ratio
    image = QtGui.QImage(
        round(view.size.width() * ratio), round(view.size.height() * ratio), QtGui.QImage.Format_ARGB32_Premultiplied
    )
    image.setDevicePixelRatio(ratio)
    image.fill(BACKGROUND)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setTransform(view.transform)
    cache.draw(painter, view, dirty or QtCore.QRect(QtCore.QPoint(0, 0), view.size))
    painter.end()
    return to_array(image)


def draw_direct(view):
    """A pintura de antes do cache: as mesmas funções, direto no widget."""
    image = QtGui.QImage(view.size, QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(BACKGROUND)
    painter = QtGui.QPainter(image)
    painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
    painter.setTransform(view.transform)
    GeometryOverlayRenderer.render_symmetry(painter, view.symmetry, view.zoom)
    GeometryOverlayRenderer.render_guides_static(painter, view.guide, view.zoom)
    painter.end()
    return to_array(image)


def to_array(image):
    rgba = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
    return np.frombuffer(rgba.constBits(), np.uint8).reshape(rgba.height(), rgba.width(), 4).astype(int)


def painted(pixels):
    """Quantos pixels diferem do fundo."""
    background = (BACKGROUND.red(), BACKGROUND.green(), BACKGROUND.blue(), 255)
    return int((pixels != np.array(background)).any(axis=2).sum())


@pytest.fixture
def cache(qapp):
    return GuideLayerCache()


def test_unchanged_view_is_painted_once_and_drawn_twice(cache):
    view = make_view(guide=isometric())
    first = draw(cache, view)
    second = draw(cache, view)
    assert cache.paints == 1
    assert painted(first) > 0
    assert (first == second).all()


def test_without_guide_or_symmetry_nothing_is_painted_or_kept(cache):
    pixels = draw(cache, make_view())
    assert cache.paints == 0
    assert painted(pixels) == 0


def test_turning_the_guide_off_releases_the_image(cache):
    draw(cache, make_view(guide=isometric()))
    assert cache.paints == 1
    assert painted(draw(cache, make_view())) == 0
    draw(cache, make_view(guide=isometric()))
    assert cache.paints == 2  # voltou a pintar: a imagem tinha sido solta


def test_changing_the_guide_repaints(cache):
    straight = {**default_guide(), "type": "straight"}
    moved = {**straight, "p0": QtCore.QPointF(10, 10)}
    before = draw(cache, make_view(guide=straight))
    after = draw(cache, make_view(guide=moved))
    assert cache.paints == 2
    assert (before != after).any()


def test_editing_a_point_in_place_repaints(cache):
    """A alça arrastada pode mudar o QPointF do dicionário sem trocar a chave: a impressão pega."""
    guide = {**default_guide(), "type": "straight", "p0": QtCore.QPointF(20, 20), "p1": QtCore.QPointF(300, 200)}
    before = draw(cache, make_view(guide=guide))
    guide["p0"].setX(120.0)
    after = draw(cache, make_view(guide=guide))
    assert cache.paints == 2
    assert (before != after).any()


def test_changing_the_symmetry_repaints(cache):
    draw(cache, make_view(symmetry=mirror()))
    draw(cache, make_view(symmetry={**mirror(), "cx": 90.0}))
    assert cache.paints == 2


@pytest.mark.parametrize(
    "change",
    [
        {"transform": QtGui.QTransform.fromTranslate(15.0, -8.0)},
        {"zoom": 1.5},
        {"size": QtCore.QSize(400, 300)},
        {"theme": "light_default"},
    ],
    ids=["pan", "zoom", "resize", "theme"],
)
def test_camera_size_and_theme_changes_repaint(cache, change):
    draw(cache, make_view(guide=isometric()))
    draw(cache, make_view(guide=isometric(), **change))
    assert cache.paints == 2


def test_cached_layer_matches_the_direct_painting(cache):
    transform = QtGui.QTransform().translate(30, 10).scale(0.8, 0.8)
    for guide, symmetry in ((isometric(), None), (None, mirror()), ({**default_guide(), "type": "curvilinear"}, None)):
        view = make_view(guide=guide, symmetry=symmetry, transform=transform, zoom=0.8)
        # Camada intermediária de 8 bits: sobreposição de traços translúcidos pode diferir poucos níveis.
        assert np.abs(draw(cache, view) - draw_direct(view)).max() <= 12


def test_only_the_dirty_region_is_drawn(cache):
    view = make_view(guide=isometric())
    dirty = QtCore.QRect(40, 30, 60, 50)
    pixels = draw(cache, view, dirty)
    outside = pixels.copy()
    outside[dirty.top():dirty.bottom() + 1, dirty.left():dirty.right() + 1] = (BACKGROUND.red(), BACKGROUND.green(), BACKGROUND.blue(), 255)
    assert painted(outside) == 0
    assert painted(pixels) > 0


def test_a_dirty_region_outside_the_widget_draws_nothing(cache):
    pixels = draw(cache, make_view(guide=isometric()), QtCore.QRect(1000, 1000, 50, 50))
    assert painted(pixels) == 0


def test_high_dpi_layer_covers_the_device_pixels(cache):
    view = make_view(guide=isometric(), ratio=2.0)
    pixels = draw(cache, view)
    assert pixels.shape[:2] == (SIZE.height() * 2, SIZE.width() * 2)
    assert painted(pixels) > 0
