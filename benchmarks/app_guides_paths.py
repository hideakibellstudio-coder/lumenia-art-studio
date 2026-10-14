"""Scenario "guides": the pen and the repaint with every guide and symmetry mode on.

Drawing with a guide on costs the snap of every pen sample (`pen_move`, `hover_move`) and the
guide overlay of every repaint (`repaint_hover`, `repaint_stroke`, `repaint_idle`). `overlay_render` is the overlay
alone, drawn from scratch onto an image the size of the viewport: what a repaint costs when
nothing of it can be reused (a pan or a zoom changes where every line falls, `repaint_zoom`).
`none` is the control: the same strokes and repaints without any guide, so a guide's price is the
difference. Everything goes through the real input router and the canvas widget, as the app does.
"""

from __future__ import annotations

import argparse
import os
import time

from benchmarks.app_common import emit, fit_window, parse_sizes, repeat_ms, summary
from benchmarks.app_ui_paths import pen_strokes

DEFAULT_SIZES = "1920x1080"
WINDOW = (1920, 1080)
HOVER_SAMPLES = 120
ZOOM_REPAINTS = 10
OVERLAY_RUNS = 5

_CURVILINEAR_ALL = {
    "show_vps": True, "show_cube": True, "show_ground": True, "show_ground_verticals": True,
    "show_ceiling": True, "show_ceiling_verticals": True, "show_letterbox": True,
}
# name -> (guide type, extra guide fields, symmetry mode)
CONFIGS = {
    "none": ("none", {}, "none"),
    "straight": ("straight", {}, "none"),
    "curve_ruler": ("curve_ruler", {}, "none"),
    "one_point": ("one_point", {}, "none"),
    "two_point": ("two_point", {}, "none"),
    "three_point": ("three_point", {}, "none"),
    "isometric": ("isometric", {}, "none"),
    "curvilinear": ("curvilinear", {}, "none"),
    "curvilinear_all": ("curvilinear", _CURVILINEAR_ALL, "none"),
    "mirror": ("none", {}, "mirror"),
    "radial": ("none", {}, "radial"),
    "kaleidoscope": ("none", {}, "kaleidoscope"),
    "everything": ("curvilinear", _CURVILINEAR_ALL, "kaleidoscope"),
}


def _apply(canvas, guide_type: str, extra: dict, symmetry: str) -> None:
    """Put the canvas in one configuration through the shared geometry state, as the panel does."""
    state = canvas.geometry_ctrl.state
    state.guide.reset({**state.guide, "type": guide_type, **{key: False for key in _CURVILINEAR_ALL}, **extra}, sync=False)
    state.set_symmetry_mode(symmetry)
    state.guideChanged.emit()


def _overlay_render_ms(canvas) -> list[float]:
    """The overlay drawn from scratch onto a transparent image the size of the viewport."""
    from PySide6 import QtCore, QtGui
    from ui.plugins.system.workspace_core.workspace.canvas.renderers.geometry_overlay_renderer import (
        GeometryOverlayRenderer,
    )

    geometry = canvas.geometry_ctrl
    transform = canvas.canvas_transform()

    def draw() -> None:
        image = QtGui.QImage(canvas.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
        image.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setTransform(transform)
        GeometryOverlayRenderer.render_symmetry(painter, geometry.sym_state, canvas.zoom)
        GeometryOverlayRenderer.render_guides(painter, geometry, canvas.zoom)
        painter.end()

    return repeat_ms(draw, OVERLAY_RUNS)


def _hover_ms(canvas) -> tuple[list[float], list[float]]:
    """The pointer moving over the canvas with no button down: the router's work, then the repaint it asks for.

    With a guide on, every move repaints the whole canvas (the rays that follow the pointer cross it),
    so `repaint_hover` is what the user waits for between one cursor position and the next.
    """
    from PySide6 import QtCore

    router = canvas.input_router
    no_modifier = QtCore.Qt.KeyboardModifier.NoModifier
    moves, repaints = [], []
    for i in range(HOVER_SAMPLES):
        point = QtCore.QPointF(300 + i * 7, 250 + (i % 40) * 6)
        started = time.perf_counter()
        router.handle_pointer_move(point, 0.0, no_modifier)
        moves.append((time.perf_counter() - started) * 1000.0)
        started = time.perf_counter()
        canvas.repaint()
        repaints.append((time.perf_counter() - started) * 1000.0)
    return moves, repaints


def _zoom_repaint_ms(canvas) -> list[float]:
    """A repaint after each zoom step: the overlay cannot be reused, every line moves."""
    steps = iter(range(ZOOM_REPAINTS))

    def zoom_and_repaint() -> None:
        canvas.zoom = 0.8 + 0.03 * next(steps)
        canvas.publish_view(zoom_changed=True)
        canvas.repaint()

    return repeat_ms(zoom_and_repaint, ZOOM_REPAINTS)


def _measure_config(app, canvas, name: str, config: tuple, strokes: int) -> dict:
    guide_type, extra, symmetry = config
    canvas.zoom = 1.0
    canvas.publish_view(zoom_changed=True)
    _apply(canvas, guide_type, extra, symmetry)
    app.processEvents()
    canvas.repaint()  # first paint of this configuration: caches (if any) are built here, not measured

    metrics: dict[str, object] = {f"overlay_render.{name}": summary(_overlay_render_ms(canvas))}
    hover_moves, hover_repaints = _hover_ms(canvas)
    metrics[f"hover_move.{name}"] = summary(hover_moves)
    metrics[f"repaint_hover.{name}"] = summary(hover_repaints)
    moves, repaints = pen_strokes(canvas, strokes)
    metrics[f"pen_move.{name}"] = summary(moves)
    metrics[f"repaint_stroke.{name}"] = summary(repaints)
    app.processEvents()
    metrics[f"repaint_idle.{name}"] = summary(repeat_ms(canvas.repaint, 10))
    metrics[f"repaint_zoom.{name}"] = summary(_zoom_repaint_ms(canvas))
    return metrics


def measure(sizes: list[tuple[int, int]], strokes: int, configs: list[str] | None) -> dict:
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from ui.boundary.orchestrator.main_window import MainWindow

    window = MainWindow()
    window.show()
    app.processEvents()
    metrics: dict[str, object] = {}
    for width, height in sizes:
        window.dm.new_document(width, height, f"bench-guides-{width}x{height}")
        app.processEvents()
        canvas = window.workspace.canvas_widget
        metrics[f"viewport.{width}x{height}"] = "x".join(str(side) for side in fit_window(app, window, WINDOW))
        canvas.active_tool = "brush"
        for name, config in CONFIGS.items():
            if configs and name not in configs:
                continue
            metrics.update(_measure_config(app, canvas, name, config, strokes))
        _apply(canvas, "none", {}, "none")
    return metrics


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    # Offscreen has no OpenGL: with the GL canvas widget every paint is a no-op (see app_ui_paths).
    os.environ.setdefault("LUMENIA_DISABLE_OPENGL", "1")
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default=DEFAULT_SIZES)
    parser.add_argument("--strokes", type=int, default=2)
    parser.add_argument("--configs", default="", help="comma list of: " + ", ".join(CONFIGS) + " (default: all)")
    parser.add_argument("--native-snap", action="store_true", help="snap in the C++ engine instead of Python")
    args = parser.parse_args()
    if args.native_snap:
        os.environ["LUMENIA_SNAP_NATIVE_PERSPECTIVE"] = "1"
        os.environ["LUMENIA_SNAP_NATIVE_CURVILINEAR"] = "1"
    configs = [item.strip() for item in args.configs.split(",") if item.strip()] or None
    emit(measure(parse_sizes(args.sizes), args.strokes, configs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
