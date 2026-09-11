"""Measure native-engine baselines without imposing hardware-specific thresholds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _summary(samples_ns: list[int]) -> dict[str, float]:
    ordered = sorted(samples_ns)
    p95_index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * 0.95)))
    return {
        "samples": len(samples_ns),
        "mean_ms": statistics.fmean(samples_ns) / 1_000_000,
        "p50_ms": statistics.median(samples_ns) / 1_000_000,
        "p95_ms": ordered[p95_index] / 1_000_000,
    }


def _event(native, event_type, x: float, y: float, timestamp: float):
    return native.PointerEvent(event_type, native.Point2D(x, y), 1.0, timestamp)


def _measure_native_import() -> int:
    """Measure a fresh interpreter loading the extension, not a cached import."""
    started = time.perf_counter_ns()
    completed = subprocess.run(
        [sys.executable, "-c", "import aladyn_engine_native"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter_ns() - started
    if completed.returncode:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"Não foi possível carregar aladyn_engine_native: {detail}")
    return elapsed


def run(iterations: int, canvas_size: int, points: int) -> dict[str, object]:
    if iterations < 1 or canvas_size < 32 or points < 2:
        raise ValueError("iterations >= 1, canvas_size >= 32 e points >= 2 são obrigatórios")

    import aladyn_engine_native as native

    startup_samples = [_measure_native_import()]
    create_samples, stroke_samples, composite_samples, lod_samples = [], [], [], []
    tile_memory_samples = []
    native_bytes = 0
    for iteration in range(iterations):
        started = time.perf_counter_ns()
        facade = native.PaintEngineFacade(canvas_size, canvas_size)
        create_samples.append(time.perf_counter_ns() - started)
        facade.add_layer(f"benchmark-{iteration}")

        started = time.perf_counter_ns()
        facade.begin_stroke(_event(native, native.PointerEventType.Press, 16, 16, 0.0))
        for point in range(1, points):
            offset = 16 + point * (canvas_size - 32) / max(1, points - 1)
            facade.update_stroke(_event(native, native.PointerEventType.Move, offset, offset, point / 120.0))
        facade.end_stroke(_event(native, native.PointerEventType.Release, canvas_size - 16, canvas_size - 16, points / 120.0))
        stroke_samples.append(time.perf_counter_ns() - started)

        started = time.perf_counter_ns()
        facade.refresh_display()
        display = facade.get_display_pixel_buffer()
        composite_samples.append(time.perf_counter_ns() - started)
        native_bytes = max(native_bytes, len(display), len(facade.get_pixel_buffer()))
        tile_memory_samples.append(float(facade.get_total_tile_memory_mb()))

        started = time.perf_counter_ns()
        facade.mark_lod_dirty()
        lod = facade.get_display_pixel_buffer_lod(1)
        lod_samples.append(time.perf_counter_ns() - started)
        if lod is not None:
            native_bytes = max(native_bytes, len(lod[0]))

    return {
        "schema_version": 1,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "canvas_size_px": canvas_size,
            "stroke_points": points,
        },
        "metrics": {
            "startup_import": _summary(startup_samples),
            "facade_create": _summary(create_samples),
            "stroke": _summary(stroke_samples),
            "compose_display": _summary(composite_samples),
            "lod_build": _summary(lod_samples),
            "native_tile_memory_mb": {
                "mean": statistics.fmean(tile_memory_samples),
                "max": max(tile_memory_samples),
            },
            "native_pixel_bytes": native_bytes,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mede baseline do Aladyn Engine e grava JSON.")
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--canvas-size", type=int, default=1024)
    parser.add_argument("--points", type=int, default=120)
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "benchmarks" / "engine.json")
    args = parser.parse_args()
    try:
        result = run(args.iterations, args.canvas_size, args.points)
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
