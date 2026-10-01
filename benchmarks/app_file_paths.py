"""Scenario "files": saving and opening a .lmn document with many layers.

Save and open run on the calling thread today, so these times are the time the
interface is frozen. The peak-memory growth is the working set the operation
adds on top of what was already resident.
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


def measure(sizes: list[tuple[int, int]], layers: int) -> dict:
    from PySide6 import QtWidgets

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from ui.core.document.manager import DocumentManager
    from ui.core.document.restore import restore_document
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
            _fill_layers(backend, layers)

            path = os.path.join(folder, f"bench-{tag}.lmn")
            before = peak_memory_mb()
            started = time.perf_counter()
            DocumentSerializer.save(doc, backend, path)
            metrics[f"save_s.{tag}"] = round(time.perf_counter() - started, 2)
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
    args = parser.parse_args()
    emit(measure(parse_sizes(args.sizes), args.layers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
