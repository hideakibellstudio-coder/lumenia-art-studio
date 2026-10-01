"""The undo history pages to disk when the temporary folder has a name outside the ANSI code page.

On Windows `std::filesystem::path::string()` converts to the ANSI code page: a temporary folder under a user called
"田中" or "Łukasz" became "?" and the scratch file could not be opened. The disk then looked disabled, and an undo
history over its memory limit was pruned instead of paged (the artist lost undo depth with no message). Every
operation on the scratch file now goes through the `path` object. This test runs the engine with `TMPDIR` pointing at
a folder with such a name and checks that the history pages and the file is removed on exit. Linux never needed the
fix, so the test cannot fail here; it records what the Windows build must keep doing (the MinGW build check compiles
the path overloads).
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHILD = textwrap.dedent("""
    import glob, os, sys
    sys.path.insert(0, {root!r})
    import aladyn_engine_native as n
    f = n.PaintEngineFacade(600, 400)
    f.set_undo_memory_limit_mb(0)          # every finished step goes to the scratch disk
    f.get_brush_profile().brush_size = 90.0
    for s in range(6):
        f.begin_stroke_raw(60 + s * 20, 120, 0.9, 0.0)
        for j in range(1, 25): f.update_stroke_raw(60 + s * 20 + j * 10, 120 + (j % 7) * 20, 0.9, j * 0.01)
        f.end_stroke_raw()
    during = glob.glob(os.path.join(sys.argv[1], "lumenia_scratch_*"))
    print(len(during), f.get_scratch_disk_usage_mb() > 0)
""")


def test_the_undo_history_pages_to_a_folder_whose_name_is_not_ansi(tmp_path):
    folder = tmp_path / "Łukasz_田中_João"
    folder.mkdir()
    result = subprocess.run([sys.executable, "-c", CHILD.format(root=str(ROOT)), str(folder)],
                            capture_output=True, text=True, timeout=120, env={"TMPDIR": str(folder), "TEMP": str(folder), "TMP": str(folder)})
    assert result.returncode == 0, result.stderr[-300:]
    files, paged = result.stdout.split()
    assert files == "1", "one scratch file must exist while the history is paged"
    assert paged == "True", "the history must page to disk, not be pruned"
    assert list(folder.glob("lumenia_scratch_*")) == [], "the scratch file is removed on a normal exit"
