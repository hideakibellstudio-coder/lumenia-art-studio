"""Real C++ I/O, codec and multi-tile history failure scenarios (no Python mocks)."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_history_error_status_message_is_not_empty_stack_message():
    from ui.plugins.system.workspace_core.workspace.workspace_container import history_failure_message

    message = history_failure_message("desfazer", "scratch_read_failed")
    assert message == "Falha ao desfazer: scratch disk do histórico indisponível. Documento preservado."
    assert "Nada a desfazer" not in message


@pytest.fixture(scope="module")
def fault_harness():
    result = subprocess.run([sys.executable, str(ROOT / "tests/native/build_history_faults.py")],
                            cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    from tests.native.build_history_faults import BINARY
    return BINARY


@pytest.mark.parametrize("scenario", [
    "undo_read", "redo_read", "undo_corrupt", "redo_corrupt", "write_first", "write_partial",
    "disable", "corrupt", "truncate", "purge",
])
def test_history_fault_scenario(fault_harness, scenario):
    result = subprocess.run([str(fault_harness), scenario], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
