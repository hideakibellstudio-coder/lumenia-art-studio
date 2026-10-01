"""The application benchmark exports a comparable result (S0.8).

The runner measures the paths S1 will change (whole-canvas display copy, pen
input, save and open). These tests check the format and the comparison, not
the speed: thresholds that depend on the hardware do not belong in a test.
"""

from __future__ import annotations

import pytest

from benchmarks.compare_runs import compare, flatten, format_report


def _run(**metrics):
    return {"scenarios": {"ui": metrics}}


def test_a_slowdown_beyond_the_tolerance_is_a_regression():
    rows = compare(_run(repaint={"p50_ms": 10.0}), _run(repaint={"p50_ms": 14.0}), tolerance=0.25)
    assert [row["regressed"] for row in rows] == [True]


def test_a_slowdown_inside_the_tolerance_is_not():
    rows = compare(_run(repaint={"p50_ms": 10.0}), _run(repaint={"p50_ms": 11.0}), tolerance=0.25)
    assert [row["regressed"] for row in rows] == [False]


def test_noise_below_the_floor_is_never_a_regression():
    """A 0.05 ms metric doubling is not news."""
    rows = compare(_run(move={"p50_ms": 0.05}), _run(move={"p50_ms": 0.1}), tolerance=0.25)
    assert [row["regressed"] for row in rows] == [False]


def test_totals_in_seconds_and_megabytes_are_compared_too():
    before = _run(save_s=1.0, save_peak_memory_growth_mb=100.0)
    after = _run(save_s=2.0, save_peak_memory_growth_mb=300.0)
    rows = {row["metric"]: row["regressed"] for row in compare(before, after, tolerance=0.25)}
    assert rows == {"ui.save_s": True, "ui.save_peak_memory_growth_mb": True}


def test_only_stable_statistics_are_flattened():
    flat = flatten(_run(move={"samples": 9, "p50_ms": 1.0, "p95_ms": 5.0, "max_ms": 9.0}, boot_s=0.5))
    assert flat == {"ui.move.p50_ms": 1.0, "ui.boot_s": 0.5}


def test_a_metric_missing_on_one_side_is_skipped():
    assert compare(_run(a={"p50_ms": 1.0}), _run(b={"p50_ms": 1.0}), tolerance=0.25) == []


def test_the_report_counts_regressions():
    rows = compare(_run(repaint={"p50_ms": 10.0}), _run(repaint={"p50_ms": 20.0}), tolerance=0.25)
    assert "1 metrics compared, 1 regressed" in format_report(rows)


def test_a_quick_run_exports_every_scenario():
    pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")
    from benchmarks.run_app_benchmarks import run

    result = run(["engine", "ui", "files"], sizes=None, quick=True)
    assert result["schema_version"] == 1
    scenarios = result["scenarios"]
    assert scenarios["engine"]["get_qimage.256x256"]["p50_ms"] >= 0
    assert scenarios["engine"]["stroke120_20layers.256x256"]["samples"] >= 3
    assert scenarios["ui"]["boot_to_window_s"] > 0
    assert scenarios["ui"]["pen_move.256x256"]["samples"] == 120
    assert scenarios["files"]["file_size_mb.256x256"] >= 0
    assert scenarios["files"]["open_restore_s.256x256"] >= 0
