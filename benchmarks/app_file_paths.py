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
        backend.start_stroke(100 + i * 50, 100, 0.8, 0.0)
        for j in range(STROKE_SAMPLES):
            backend.paint_stroke(100 + i * 50 + j * 30, 100 + j * 20, 0.8, j * 0.004)
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


def _event_loop_gap_during_save(doc, backend, folder: str, tag: str) -> float:
    """The longest time the interface thread went without handling an event while the application
    saved the document the way it does (capture here, writing on the DocumentSaver's thread).

    A timer ticks every 5 ms and the loop that waits for the save keeps processing events: the
    largest distance between two ticks, plus the capture itself, is how long a user would see the
    window frozen. The target of S1.2 is 50 ms.
    """
    from PySide6 import QtCore, QtWidgets

    from ui.core.document.document_saver import DocumentSaver
    from ui.core.document.save_capture import capture_document

    app = QtWidgets.QApplication.instance()
    saver = DocumentSaver()
    ticks: list[float] = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
    timer.start()
    app.processEvents()
    ticks.append(time.perf_counter())
    started = time.perf_counter()
    capture = capture_document(doc, backend, os.path.join(folder, f"async-{tag}.lmn"))
    capture_ms = (time.perf_counter() - started) * 1000.0
    saver.submit(capture)
    while saver.is_busy():
        app.processEvents()
        time.sleep(0.001)
    timer.stop()
    gaps = [(b - a) * 1000.0 for a, b in zip(ticks, ticks[1:])]
    return round(max(gaps + [capture_ms]), 1)


def _open_in_background(manager, backend, path: str, width: int, height: int, tag: str) -> dict:
    """Opening the way the application does it: the file is read and decoded on a worker thread and
    the interface thread only creates the document and adopts the decoded layers.

    `open_interface_s` is that second half, the only time the window is not handling events;
    `open_event_loop_max_gap_ms` is the longest time without an event over the whole open;
    `open_s` is from the request to the document being ready.
    """
    from PySide6 import QtCore, QtWidgets

    from ui.core.document.document_loader import DocumentLoader
    from ui.core.document.restore import restore_document

    app = QtWidgets.QApplication.instance()
    loader = DocumentLoader()
    ticks: list[float] = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
    timer.start()
    app.processEvents()
    ticks.append(time.perf_counter())
    done: dict[str, float] = {}

    def adopt(loaded) -> None:
        began = time.perf_counter()
        document = manager.new_document(width, height, f"bench-{tag}-async")
        backend.set_active_document_context(document.uid, width, height)
        restore_document(document, backend, loaded.manifest, loaded.payloads, loaded.prepared)
        done["interface"] = time.perf_counter() - began
        done["end"] = time.perf_counter()

    requested = time.perf_counter()
    loader.submit(path, backend, adopt, lambda _path, exc: done.update(error=exc))
    while loader.is_busy():
        app.processEvents()
        time.sleep(0.001)
    timer.stop()
    if "error" in done:
        raise done["error"]
    gaps = [(b - a) * 1000.0 for a, b in zip(ticks, ticks[1:])]
    # the adoption runs inside the loop, so no tick can fire during it: it counts as a gap of its own
    gaps.append(done["interface"] * 1000.0)
    return {
        f"open_interface_s.{tag}": round(done["interface"], 3),
        f"open_event_loop_max_gap_ms.{tag}": round(max(gaps), 1),
        f"open_s.{tag}": round(done["end"] - requested, 2),
    }


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
            metrics[f"save_event_loop_max_gap_ms.{tag}"] = _event_loop_gap_during_save(doc, backend, folder, tag)
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
            metrics.update(_open_in_background(manager, backend, path, width, height, tag))
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
