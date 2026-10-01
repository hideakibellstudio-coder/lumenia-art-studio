"""Measure the application paths (display, pen input, files) and compare runs.

Each scenario runs in its own process: the peak-memory readings do not mix and
a crash in one scenario does not take the others with it. Results are plain
JSON, so the same command before and after a change is the evidence the ARCcC
build cycle asks for (4.4.8: hypothesis, benchmark, evidence, change, new
benchmark).

    python benchmarks/run_app_benchmarks.py                      # everything
    python benchmarks/run_app_benchmarks.py --only ui --output before.json
    python benchmarks/run_app_benchmarks.py --compare before.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import os
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.compare_runs import compare, format_report  # noqa: E402

SCENARIOS = {
    "engine": "benchmarks.app_engine_paths",
    "ui": "benchmarks.app_ui_paths",
    "files": "benchmarks.app_file_paths",
}
# Scenario-specific knobs, as command-line arguments of the scenario module.
SIZE_FLAG = "--sizes"
QUICK_ARGS = {
    "engine": ["--sizes", "256x256", "--repeats", "2"],
    "ui": ["--sizes", "256x256", "--strokes", "1"],
    "files": ["--sizes", "256x256", "--layers", "3"],
}


def run_scenario(name: str, extra_args: list[str], config_dir: str) -> dict:
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env["LUMENIA_CONFIG_PATH"] = os.path.join(config_dir, f"{name}.json")
    completed = subprocess.run(
        [sys.executable, "-m", SCENARIOS[name], *extra_args],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    if completed.returncode:
        detail = (completed.stderr or completed.stdout).strip()[-1500:]
        raise RuntimeError(f"scenario '{name}' failed: {detail}")
    return json.loads(completed.stdout.strip().splitlines()[-1])


def run(only: list[str], sizes: str | None, quick: bool) -> dict:
    results = {}
    with tempfile.TemporaryDirectory(prefix="lumenia-bench-config-") as config_dir:
        for name in only:
            args = list(QUICK_ARGS[name]) if quick else []
            if sizes and not quick:
                args += [SIZE_FLAG, sizes]
            results[name] = run_scenario(name, args, config_dir)
    return {
        "schema_version": 1,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "qt_platform": os.environ.get("QT_QPA_PLATFORM", "offscreen"),
            "quick": quick,
        },
        "scenarios": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure application paths and write JSON.")
    parser.add_argument("--only", default=",".join(SCENARIOS), help="comma list of: " + ", ".join(SCENARIOS))
    parser.add_argument("--sizes", default=None, help="canvas sizes, e.g. 1920x1080,3840x2160")
    parser.add_argument("--quick", action="store_true", help="tiny canvases, for checking the runner itself")
    parser.add_argument("--output", type=Path, default=ROOT / "build" / "benchmarks" / "app.json")
    parser.add_argument("--compare", type=Path, default=None, help="baseline JSON from an earlier run")
    parser.add_argument("--tolerance", type=float, default=0.25, help="allowed relative regression (default 25%%)")
    args = parser.parse_args()

    names = [item.strip() for item in args.only.split(",") if item.strip()]
    unknown = [item for item in names if item not in SCENARIOS]
    if unknown:
        parser.error(f"unknown scenario(s): {', '.join(unknown)}")
    result = run(names, args.sizes, args.quick)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

    if args.compare is not None:
        baseline = json.loads(args.compare.read_text(encoding="utf-8"))
        rows = compare(baseline, result, args.tolerance)
        print(format_report(rows))
        return 1 if any(row["regressed"] for row in rows) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
