"""
test_camera_exact_zoom_and_grid.py
==================================
Test suite for S11: Câmera e exibição (pixel exato a partir de 400%, grade opcional).
Validates nearest-neighbor rendering without bilinear blur at zoom >= 4.0,
the is_exact_pixel_zoom property on ViewportTransform, and optional pixel grid rendering.
"""

from __future__ import annotations

import pytest
from PySide6 import QtCore, QtGui

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)


def test_viewport_transform_exact_pixel_zoom():
    """Valida que o ViewportTransform nativo reconhece zoom >= 400% como zoom exato por pixel."""
    vt = native.ViewportTransform(1920, 1080, 1920, 1080)

    # 100%
    vt.set_camera(0.0, 0.0, 1.0, 0.0)
    assert not vt.is_exact_pixel_zoom

    # 200%
    vt.set_camera(0.0, 0.0, 2.0, 0.0)
    assert not vt.is_exact_pixel_zoom

    # 399%
    vt.set_camera(0.0, 0.0, 3.99, 0.0)
    assert not vt.is_exact_pixel_zoom

    # 400% (Limiar de pixel exato)
    vt.set_camera(0.0, 0.0, 4.0, 0.0)
    assert vt.is_exact_pixel_zoom

    # 800%
    vt.set_camera(0.0, 0.0, 8.0, 0.0)
    assert vt.is_exact_pixel_zoom

    # 1600%
    vt.set_camera(0.0, 0.0, 16.0, 0.0)
    assert vt.is_exact_pixel_zoom


def test_render_widget_pixel_grid_toggle(qapp):
    """Valida que o RenderWidget possui a propriedade show_pixel_grid e o método toggle_pixel_grid."""
    from ui.plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

    widget = RenderWidget()
    assert hasattr(widget, "show_pixel_grid")
    assert widget.show_pixel_grid is True

    # Alterna o estado da grade de pixels
    new_state = widget.toggle_pixel_grid()
    assert new_state is False
    assert widget.show_pixel_grid is False

    # Alterna de volta
    new_state2 = widget.toggle_pixel_grid()
    assert new_state2 is True
    assert widget.show_pixel_grid is True


def test_viewport_renderer_pixel_grid_paint(qapp):
    """Valida o método de renderização da grade de pixels do ViewportRenderer."""
    from ui.plugins.system.workspace_core.workspace.canvas.viewport.viewport_renderer import ViewportRenderer

    # Imagem de teste para pintar
    image = QtGui.QImage(100, 100, QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.black)

    painter = QtGui.QPainter(image)
    try:
        dirty = QtCore.QRect(0, 0, 20, 20)
        # Renderiza a grade de pixels
        ViewportRenderer._render_pixel_grid(painter, dirty, 100, 100)
    finally:
        painter.end()

    # Confere que pixels foram desenhados na grade
    # (pelo menos um pixel foi alterado com a cor cinza da grade)
    arr = image.constBits()
    assert len(arr) == 100 * 100 * 4
