"""Scenario "ui": the application window, the pen input and the repaint.

Boot to the main window, a new document, the cost of one pen sample through the
real input router, and the repaint of the canvas widget at "fit" and at 100%
zoom (the case where the viewport copies the whole canvas on every paint).
"""

from __future__ import annotations

import argparse
import os
import time

from benchmarks.app_common import emit, parse_sizes, peak_memory_mb, repeat_ms, summary

DEFAULT_SIZES = "1920x1080,3840x2160"
STROKE_SAMPLES = 120
REPAINT_EVERY = 4


def _pen_strokes(canvas, strokes: int):
    """Pen samples through the input router; returns (move_ms, repaint_ms) lists."""
    from PySide6 import QtCore

    no_modifier = QtCore.Qt.KeyboardModifier.NoModifier
    left = QtCore.Qt.MouseButton.LeftButton
    router = canvas.input_router
    moves, repaints = [], []
    for _ in range(strokes):
        router.handle_pointer_press(QtCore.QPointF(200, 200), left, 0.8, no_modifier)
        for i in range(1, STROKE_SAMPLES + 1):
            point = QtCore.QPointF(200 + i * 6, 200 + (i % 30) * 5)
            started = time.perf_counter()
            router.handle_pointer_move(point, 0.8, no_modifier)
            moves.append((time.perf_counter() - started) * 1000.0)
            if i % REPAINT_EVERY == 0:
                started = time.perf_counter()
                canvas.repaint()
                repaints.append((time.perf_counter() - started) * 1000.0)
        router.handle_pointer_release(QtCore.QPointF(920, 300), left, no_modifier)
    return moves, repaints


def measure(sizes: list[tuple[int, int]], strokes: int) -> dict:
    started = time.perf_counter()
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from ui.boundary.orchestrator.main_window import MainWindow

    window = MainWindow()
    window.show()
    app.processEvents()
    metrics: dict[str, object] = {
        "boot_to_window_s": round(time.perf_counter() - started, 2),
        "memory_after_window_mb": peak_memory_mb(),
    }
    for width, height in sizes:
        tag = f"{width}x{height}"
        opened = time.perf_counter()
        window.dm.new_document(width, height, f"bench-{tag}")
        app.processEvents()
        metrics[f"new_document_s.{tag}"] = round(time.perf_counter() - opened, 3)

        canvas = window.workspace.canvas_widget
        canvas.resize(1600, 900)
        canvas.active_tool = "brush"
        moves, repaints = _pen_strokes(canvas, strokes)
        app.processEvents()
        metrics[f"pen_move.{tag}"] = summary(moves)
        metrics[f"repaint_during_stroke.{tag}"] = summary(repaints)

        canvas.zoom = 1.0
        canvas.publish_view(zoom_changed=True)
        metrics[f"repaint_zoom100.{tag}"] = summary(repeat_ms(canvas.repaint, 10))
    return metrics


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default=DEFAULT_SIZES)
    parser.add_argument("--strokes", type=int, default=3)
    args = parser.parse_args()
    emit(measure(parse_sizes(args.sizes), args.strokes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
