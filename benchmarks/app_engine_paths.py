"""Scenario "engine": the paths the application takes through the backend.

Display acquisition: the whole-canvas copy (`get_qimage`, what the viewport made on
every repaint at zoom >= 100% until S1.1, and what recording and export still ask
for), the region the viewport asks for today (a 1600x900 window and a 128x128
stroke rectangle), the zoomed-out view (the pyramid, whole and after a change), a 120-sample
stroke, the same stroke over 20 layers, an opacity change and an undo/redo
pair. Everything goes through the public backend contract, as the UI does.
"""

from __future__ import annotations

import argparse
import os

from benchmarks.app_common import emit, parse_sizes, repeat_ms, summary

DEFAULT_SIZES = "1920x1080,3840x2160,6000x4000"
STROKE_SAMPLES = 120
EXTRA_LAYERS = 19


def _stroke(backend, origin_x: float = 100.0, origin_y: float = 100.0) -> None:
    backend.start_stroke(origin_x, origin_y, 0.8, 0.0)
    for i in range(1, STROKE_SAMPLES + 1):
        backend.paint_stroke(origin_x + i * 8, origin_y + (i % 20) * 6, 0.8, i * 0.004)
    backend.end_stroke()


def _add_dense_layers(backend) -> None:
    for i in range(EXTRA_LAYERS):
        backend.add_layer(f"bench-{i}", -1)
        backend.select_layer(backend.get_drawing_layer_count() - 1)
        backend.start_stroke(50 + i * 30, 50, 0.8, 0.0)
        for j in range(30):
            backend.paint_stroke(50 + i * 30 + j * 20, 50 + j * 25, 0.8, j * 0.004)
        backend.end_stroke()


def _toggle_opacity(backend, layer_index: int) -> None:
    current = backend.get_layer_info(layer_index)["opacity"]
    backend.set_layer_opacity(layer_index, 0.5 if current == 1.0 else 1.0)


def _zoomed_out(backend, width: int, height: int, tag: str, repeats: int) -> dict:
    """The fit view of a large document: what a repaint costs zoomed out (D18).

    `display_lod_fit_clean`: nothing changed since the last read. `display_lod_after_change`:
    a 32x32 patch is pasted and the repaint asks for the 128x128 rectangle around it, as a
    pen stroke does. `lod_whole_rebuild_reference`: what every repaint cost before D18 (the
    whole pyramid rebuilt and the whole level copied), measured on the engine directly.
    `display_lod_after_change_with_profile`: the same change with a colour profile active.
    """
    import aladyn_engine_native as native
    from PySide6.QtCore import QRect

    zoom = 0.4
    whole, patch_area, patch = QRect(0, 0, width, height), QRect(100, 100, 128, 128), bytes([10, 20, 30, 255]) * 1024
    backend.get_display_image(zoom, whole)  # builds the pyramid

    def after_change():
        backend.paste_rgba_buffer_on_active_layer(100, 100, 32, 32, patch)
        backend.get_display_image(zoom, patch_area)

    reference = native.PaintEngineFacade(width, height)
    reference.get_display_pixel_buffer_lod(1)
    metrics = {
        f"display_lod_fit_clean.{tag}": summary(repeat_ms(lambda: backend.get_display_image(zoom, whole), repeats)),
        f"display_lod_after_change.{tag}": summary(repeat_ms(after_change, repeats)),
        f"lod_whole_rebuild_reference.{tag}": summary(
            repeat_ms(lambda: (reference.mark_lod_dirty(), reference.get_display_pixel_buffer_lod(1)), repeats)
        ),
    }
    # A colour profile other than sRGB: the pyramid reads a converted copy of the canvas, converted
    # only where it rebuilds (the whole canvas on every read cost 390 ms at 4K).
    backend.set_color_profile(3)
    backend.get_display_image(zoom, whole)
    metrics[f"display_lod_after_change_with_profile.{tag}"] = summary(repeat_ms(after_change, repeats))
    backend.set_color_profile(0)
    return metrics


def measure(sizes: list[tuple[int, int]], repeats: int) -> dict:
    from PySide6.QtCore import QRect

    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    metrics: dict[str, dict] = {}
    for width, height in sizes:
        tag = f"{width}x{height}"
        uid = f"bench-{tag}"
        backend = AladynBackend()
        backend.set_active_document_context(uid, width, height)
        metrics[f"get_qimage.{tag}"] = summary(repeat_ms(backend.get_qimage, repeats))
        for label, region in (("viewport", QRect(0, 0, 1600, 900)), ("stroke", QRect(100, 100, 128, 128))):
            metrics[f"display_region_{label}.{tag}"] = summary(
                repeat_ms(lambda region=region: backend.get_display_image(1.0, region), repeats)
            )
        metrics.update(_zoomed_out(backend, width, height, tag, repeats))
        backend.set_brush_size(40.0)
        metrics[f"stroke120.{tag}"] = summary(repeat_ms(lambda: _stroke(backend), max(3, repeats // 2)))
        _add_dense_layers(backend)
        metrics[f"stroke120_20layers.{tag}"] = summary(
            repeat_ms(lambda: _stroke(backend), max(3, repeats // 2))
        )
        metrics[f"opacity_change_20layers.{tag}"] = summary(
            repeat_ms(lambda: _toggle_opacity(backend, 5), max(3, repeats // 2))
        )
        metrics[f"undo_redo_pair.{tag}"] = summary(
            repeat_ms(lambda: (backend.undo(), backend.redo()), max(3, repeats // 2))
        )
        backend.close_document_context(uid)
    return metrics


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default=DEFAULT_SIZES)
    parser.add_argument("--repeats", type=int, default=10)
    args = parser.parse_args()
    from PySide6 import QtWidgets

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    emit(measure(parse_sizes(args.sizes), args.repeats))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
