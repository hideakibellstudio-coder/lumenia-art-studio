from benchmarks.run_engine_benchmarks import run


def test_engine_benchmark_exports_machine_readable_baseline():
    result = run(iterations=1, canvas_size=64, points=4)
    assert result["schema_version"] == 1
    assert result["environment"]["canvas_size_px"] == 64
    metrics = result["metrics"]
    assert metrics["startup_import"]["samples"] == 1
    assert metrics["facade_create"]["samples"] == 1
    assert metrics["stroke"]["p95_ms"] >= 0
    assert metrics["compose_display"]["mean_ms"] >= 0
    assert metrics["lod_build"]["samples"] == 1
    assert metrics["native_tile_memory_mb"]["max"] >= 0
    assert metrics["native_pixel_bytes"] == 64 * 64 * 4
