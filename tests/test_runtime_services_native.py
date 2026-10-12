"""The engine writes crash dumps (white box of bind_runtime.cpp)."""
from __future__ import annotations

import sys

import pytest

native = pytest.importorskip("aladyn_engine_native", reason="native module not built here")

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="minidumps are a Windows service")


@windows_only
def test_the_crash_handler_takes_a_folder_and_a_manual_dump_is_written(tmp_path):
    assert native.install_crash_handler(str(tmp_path))
    assert not native.install_crash_handler(str(tmp_path / "missing"))
    dump = tmp_path / "manual.dmp"
    assert native.write_diagnostic_dump(str(dump))
    assert dump.read_bytes()[:4] == b"MDMP"
