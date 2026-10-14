"""Scenario "brush_engines": fast pen strokes with every brush engine.

The cost of one pen sample (`paint_stroke`) and of a whole stroke for each engine
(default brush, pencil, inker, eraser, marker, blur, smudge, watercolor, oil) at
three brush sizes (8-bit documents by default, `--bits 16` for RGBA16), over a canvas that already holds paint (blur and smudge do
nothing on an empty canvas). The stroke is a fast one: 40 px between samples, 4 ms
apart (10 000 px/s), so every sample asks the engine for a whole run of dabs. The
stroke-opacity ceiling (a working copy of the layer) is measured on its own, since
it adds a merge to every sample. Everything goes through the public backend contract,
as the UI does. The engine's own stage timings (raster, undo record, composite) come
from the telemetry snapshot, summed over the last stroke, so the number says which stage the time went to.
"""

from __future__ import annotations

import argparse
import math
import os

from benchmarks.app_common import emit, parse_sizes, summary

DEFAULT_SIZES = "1920x1080"
STROKE_SAMPLES = 60
STEP_PX = 40.0
SAMPLE_INTERVAL_S = 0.004
BRUSH_DIAMETERS = (12.0, 48.0, 150.0)
CAPPED_OPACITY = 0.5
PIXEL_FORMAT_RGBA8 = 0  # mirrors engine/core/canvas/PixelFormat.hpp
PIXEL_FORMAT_RGBA16 = 1


def _engines():
    from ui.core.engine.engine_type import EngineType

    return (
        ("brush", EngineType.BRUSH), ("pencil", EngineType.PENCIL), ("inker", EngineType.INKER),
        ("eraser", EngineType.ERASER), ("marker", EngineType.MARKER), ("blur", EngineType.BLUR),
        ("smudge", EngineType.SMUDGE), ("watercolor", EngineType.WATERCOLOR),
        ("oil", EngineType.OIL_IMPASTO),
    )


def _painted_canvas_bytes(width: int, height: int) -> bytes:
    """Stripes and a gradient, fully opaque: every pixel has something to blur or drag."""
    import numpy as np

    ys, xs = np.mgrid[0:height, 0:width]
    pixels = np.empty((height, width, 4), dtype=np.uint8)
    pixels[..., 0] = (xs * 255 // max(1, width - 1)).astype(np.uint8)
    pixels[..., 1] = (ys * 255 // max(1, height - 1)).astype(np.uint8)
    pixels[..., 2] = np.where(((xs // 24) + (ys // 24)) % 2 == 0, 40, 220).astype(np.uint8)
    pixels[..., 3] = 255
    return pixels.tobytes()


def _stroke_points(width: int, height: int) -> list[tuple[float, float]]:
    """A snake across the canvas: 40 px steps along x with a vertical wave, so the path curves."""
    left, top = width * 0.1, height * 0.5
    amplitude = height * 0.25
    points = []
    for i in range(STROKE_SAMPLES + 1):
        x = left + i * STEP_PX
        if x > width * 0.9:
            x = width * 0.9 - (x - width * 0.9) % (width * 0.8)
        points.append((x, top + amplitude * math.sin(i * 0.35)))
    return points


def _run_stroke(backend, points: list[tuple[float, float]]) -> tuple[list[float], dict[str, float]]:
    """One stroke: the milliseconds each `paint_stroke` took, and the engine's own stage totals.

    The telemetry snapshot holds the figures of the last pen sample, so it is read after every
    sample (outside the timed call) and summed over the stroke.
    """
    import time

    samples = []
    stages = {"raster_ms": 0.0, "undo_ms": 0.0, "composite_ms": 0.0}
    backend.start_stroke(points[0][0], points[0][1], 0.8, 0.0)
    for i, (x, y) in enumerate(points[1:], start=1):
        started = time.perf_counter()
        backend.paint_stroke(x, y, 0.8, i * SAMPLE_INTERVAL_S)
        samples.append((time.perf_counter() - started) * 1000.0)
        snap = backend.get_telemetry_snapshot()
        stages["raster_ms"] += snap.time_raster_dab_us / 1000.0
        stages["undo_ms"] += snap.time_undo_record_us / 1000.0
        stages["composite_ms"] += snap.time_composite_us / 1000.0
    started = time.perf_counter()
    backend.end_stroke()
    samples.append((time.perf_counter() - started) * 1000.0)
    return samples, {key: round(value, 3) for key, value in stages.items()}


def _measure_case(backend, points, strokes: int) -> dict:
    per_sample: list[float] = []
    totals: list[float] = []
    _run_stroke(backend, points)  # warm-up: first touch of tiles, engine state, caches
    backend.undo()
    stages: dict[str, float] = {}
    dabs = 0
    for _ in range(strokes):
        samples, stages = _run_stroke(backend, points)
        per_sample.extend(samples[:-1])
        totals.append(sum(samples))
        dabs = backend.get_telemetry_snapshot().total_dabs_in_stroke
        backend.undo()
    return {"sample": summary(per_sample), "stroke": summary(totals), "dabs": dabs, "stages": stages}


def measure(sizes: list[tuple[int, int]], strokes: int, engines: list[str] | None, bits: int = 8) -> dict:
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    metrics: dict[str, object] = {}
    stages: dict[str, dict] = {}
    for width, height in sizes:
        tag = f"{width}x{height}" + (".rgba16" if bits == 16 else "")
        uid = f"bench-engines-{tag}"
        backend = AladynBackend()
        backend.set_active_document_context(uid, width, height, PIXEL_FORMAT_RGBA16 if bits == 16 else PIXEL_FORMAT_RGBA8)
        backend.paste_rgba_buffer_on_active_layer(0, 0, width, height, _painted_canvas_bytes(width, height))
        backend.set_telemetry_enabled(True)
        backend.set_brush_color(0.9, 0.2, 0.1)
        points = _stroke_points(width, height)
        for name, engine in _engines():
            if engines and name not in engines:
                continue
            backend.set_engine_type(int(engine))
            for diameter in BRUSH_DIAMETERS:
                backend.set_brush_size(diameter)
                cases = [("", 1.0)]
                if diameter == BRUSH_DIAMETERS[1]:
                    cases.append((".capped", CAPPED_OPACITY))
                for suffix, opacity in cases:
                    backend.set_brush_opacity(opacity)
                    result = _measure_case(backend, points, strokes)
                    key = f"{name}.d{int(diameter)}{suffix}.{tag}"
                    metrics[f"sample.{key}"] = result["sample"]
                    metrics[f"stroke.{key}"] = result["stroke"]
                    metrics[f"dabs.{key}"] = result["dabs"]
                    stages[key] = result["stages"]
            backend.set_brush_opacity(1.0)
        backend.close_document_context(uid)
    metrics["stages_last_stroke"] = stages
    return metrics


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default=DEFAULT_SIZES)
    parser.add_argument("--strokes", type=int, default=5)
    parser.add_argument("--engines", default="", help="comma list, e.g. blur,smudge (default: all)")
    parser.add_argument("--bits", type=int, choices=(8, 16), default=8, help="document pixel format: 8 (RGBA8) or 16 (RGBA16)")
    args = parser.parse_args()
    from PySide6 import QtWidgets

    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    engines = [item.strip() for item in args.engines.split(",") if item.strip()] or None
    emit(measure(parse_sizes(args.sizes), args.strokes, engines, args.bits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
