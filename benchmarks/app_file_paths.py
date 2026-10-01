"""Scenario "files": saving and opening a .lmn document with many layers.

Saving has two halves (ui/core/document/save_capture.py): `save_capture_ms` is the first,
the only part that must run on the interface thread, so it is the freeze a save causes
(the file used to be written on that thread: `save_s` is both halves, as before);
`save_write_s` is the second, which the application runs on another thread. Opening runs
on the interface thread: `open_read_s` plus `open_restore_s` is the time it is frozen.
The peak-memory growth is the working set the operation adds on top of what was already
resident (monotonic peak: it shows only when the operation raised it).

Two kinds of content: `sparse` (a few strokes per layer, as a sketch) and `dense` (every
layer fully painted: a smooth fill with grain, the case where the file really has to hold
a layer's worth of pixels).
"""

from __future__ import annotations

import argparse
import os
import tempfile
import time

from benchmarks.app_common import emit, parse_sizes, peak_memory_mb

DEFAULT_SIZES = "1920x1080,3840x2160"
LAYERS = 10
STROKE_SAMPLES = 40


def _fill_layers(backend, layers: int) -> None:
    for i in range(layers):
        backend.select_layer(i)
        backend.begin_stroke_raw(100 + i * 50, 100, 0.8, 0.0)
        for j in range(STROKE_SAMPLES):
            backend.update_stroke_raw(100 + i * 50 + j * 30, 100 + j * 20, 0.8, j * 0.004)
        backend.end_stroke()


def _paint_dense(backend, layers: int, width: int, height: int) -> None:
    """Every layer fully painted: a smooth gradient with a little grain (the grain keeps LZ4 honest)."""
    import numpy as np

    rng = np.random.default_rng(1)
    ramp = (np.add.outer(np.arange(height), np.arange(width)) % 256).astype(np.uint8)
    for i in range(layers):
        backend.select_layer(i)
        pixels = np.empty((height, width, 4), dtype=np.uint8)
        pixels[:, :, 0] = ramp
        pixels[:, :, 1] = np.roll(ramp, 40 * i, axis=1)
        pixels[:, :, 2] = 255 - ramp
        pixels[:, :, 3] = 255
        pixels[:, :, :3] += rng.integers(0, 6, size=(height, width, 3), dtype=np.uint8)
        backend.paste_rgba_buffer_on_active_layer(0, 0, width, height, pixels.tobytes())


def measure(sizes: list[tuple[int, int]], layers: int, content: str = "sparse") -> dict:
    from PySide6 import QtWidgets

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from ui.core.document.manager import DocumentManager
    from ui.core.document.restore import restore_document
    from ui.core.document.save_capture import capture_document
    from ui.core.document.serializer import DocumentSerializer
    from ui.core.engine.registry import EngineRegistry
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    EngineRegistry.instance().setup([AladynBackend()])
    backend = EngineRegistry.instance().get_backend()
    manager = DocumentManager.instance()
    metrics: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="lumenia-bench-") as folder:
        for width, height in sizes:
            tag = f"{width}x{height}"
            doc = manager.new_document(width, height, f"bench-{tag}")
            backend.set_active_document_context(doc.uid, width, height)
            for i in range(layers - 1):
                doc.layer_manager.add_layer(f"L{i}")
            if content == "dense":
                _paint_dense(backend, layers, width, height)
            else:
                _fill_layers(backend, layers)

            path = os.path.join(folder, f"bench-{tag}.lmn")
            before = peak_memory_mb()
            started = time.perf_counter()
            capture = capture_document(doc, backend, path)
            captured = time.perf_counter()
            DocumentSerializer.write(capture)
            finished = time.perf_counter()
            metrics[f"save_capture_ms.{tag}"] = round((captured - started) * 1000.0, 1)
            metrics[f"save_write_s.{tag}"] = round(finished - captured, 2)
            metrics[f"save_s.{tag}"] = round(finished - started, 2)
            after = peak_memory_mb()
            metrics[f"save_peak_memory_growth_mb.{tag}"] = (
                round(after - before, 1) if before is not None and after is not None else None
            )
            metrics[f"file_size_mb.{tag}"] = round(os.path.getsize(path) / 1048576, 1)

            started = time.perf_counter()
            manifest, payloads = DocumentSerializer.read(path)
            metrics[f"open_read_s.{tag}"] = round(time.perf_counter() - started, 2)
            reopened = manager.new_document(width, height, f"bench-{tag}-reopened")
            backend.set_active_document_context(reopened.uid, width, height)
            started = time.perf_counter()
            restore_document(reopened, backend, manifest, payloads)
            metrics[f"open_restore_s.{tag}"] = round(time.perf_counter() - started, 2)
    return metrics


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default=DEFAULT_SIZES)
    parser.add_argument("--layers", type=int, default=LAYERS)
    parser.add_argument("--content", choices=("sparse", "dense"), default="sparse")
    args = parser.parse_args()
    emit(measure(parse_sizes(args.sizes), args.layers, args.content))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
