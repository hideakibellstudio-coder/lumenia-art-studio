"""Compare two application-benchmark results (the "new benchmark" of ARCcC 4.4.8)."""

from __future__ import annotations

# Absolute noise floor per unit: a change smaller than this is never a regression,
# whatever its ratio (a 0.05 ms metric doubling is not news).
NOISE_FLOOR = {"ms": 0.2, "s": 0.05, "mb": 5.0}
# Only stable statistics are compared: medians and totals, not p95 or max.
COMPARED_STATS = ("p50_ms",)


def flatten(result: dict) -> dict[str, float]:
    """Turn {"scenarios": {"ui": {"pen_move.1920x1080": {"p50_ms": 0.07}, "boot_s": 0.6}}}
    into {"ui.pen_move.1920x1080.p50_ms": 0.07, "ui.boot_s": 0.6}."""
    flat: dict[str, float] = {}
    for scenario, metrics in result.get("scenarios", {}).items():
        for name, value in metrics.items():
            if isinstance(value, dict):
                for stat in COMPARED_STATS:
                    if isinstance(value.get(stat), (int, float)):
                        flat[f"{scenario}.{name}.{stat}"] = float(value[stat])
            elif isinstance(value, (int, float)):
                flat[f"{scenario}.{name}"] = float(value)
    return flat


def _unit(key: str) -> str:
    stem = key.rsplit(".", 1)[-1]
    for unit in ("mb", "ms", "s"):
        if stem.endswith("_" + unit):
            return unit
    return ""


def compare(baseline: dict, current: dict, tolerance: float) -> list[dict]:
    """One row per metric present in both runs; `regressed` is True when the
    current value is worse than baseline * (1 + tolerance) by more than the noise floor."""
    before, after = flatten(baseline), flatten(current)
    rows = []
    for key in sorted(before.keys() & after.keys()):
        old, new = before[key], after[key]
        floor = NOISE_FLOOR.get(_unit(key), 0.0)
        regressed = new > old * (1.0 + tolerance) and (new - old) > floor
        rows.append({"metric": key, "before": old, "after": new,
                     "ratio": (new / old) if old else float("inf"), "regressed": regressed})
    return rows


def format_report(rows: list[dict]) -> str:
    lines = [f"{'metric':64s} {'before':>10s} {'after':>10s} {'ratio':>7s}"]
    for row in rows:
        mark = "  REGRESSION" if row["regressed"] else ""
        lines.append(f"{row['metric']:64s} {row['before']:10.3f} {row['after']:10.3f} {row['ratio']:7.2f}{mark}")
    regressed = sum(row["regressed"] for row in rows)
    lines.append(f"{len(rows)} metrics compared, {regressed} regressed")
    return "\n".join(lines)
