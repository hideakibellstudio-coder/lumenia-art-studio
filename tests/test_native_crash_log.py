"""Queda nativa deixa rastro: `ui/infrastructure/logging/crash_log.py`.

Até 2026-09-25 um acesso inválido no motor C++ fechava o app sem uma linha no
log (o `sys.excepthook` só vê exceção Python). Cada cenário roda num processo
filho: a queda é de verdade e o faulthandler do pytest não é tocado.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CRASH = """
import sys
from pathlib import Path
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0002)  # sem a caixa de erro do Windows
import faulthandler
from ui.infrastructure.logging.crash_log import enable_native_crash_log
enable_native_crash_log(Path(sys.argv[1]))
faulthandler._sigsegv()
"""

REOPEN = """
import sys
from pathlib import Path
from ui.infrastructure.logging.crash_log import enable_native_crash_log
print(enable_native_crash_log(Path(sys.argv[1])))
"""


def _run(script: str, logs_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", script, str(logs_dir)], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=120)


def test_native_crash_writes_the_stack_and_next_session_reports_it(tmp_path):
    crashed = _run(CRASH, tmp_path)
    assert crashed.returncode != 0
    stack = (tmp_path / "native_crash.log").read_text(encoding="utf-8", errors="replace")
    assert "most recent call first" in stack, stack

    reopened = _run(REOPEN, tmp_path)
    assert reopened.returncode == 0, reopened.stderr
    archived = Path(reopened.stdout.strip())
    assert archived.parent == tmp_path and archived.name.startswith("native_crash-")
    assert "most recent call first" in archived.read_text(encoding="utf-8", errors="replace")
    assert (tmp_path / "native_crash.log").read_text(encoding="utf-8") == ""


def test_clean_session_reports_nothing_and_keeps_few_archives(tmp_path):
    for index in range(7):
        (tmp_path / f"native_crash-2026010{index}-000000.log").write_text("antigo", encoding="utf-8")
    (tmp_path / "native_crash.log").write_text("", encoding="utf-8")
    reopened = _run(REOPEN, tmp_path)
    assert reopened.stdout.strip() == "None", reopened.stderr
    assert len(list(tmp_path.glob("native_crash-*.log"))) == 7  # nada arquivado, nada apagado

    (tmp_path / "native_crash.log").write_text("queda", encoding="utf-8")
    _run(REOPEN, tmp_path)
    assert len(list(tmp_path.glob("native_crash-*.log"))) == 5
