"""TestRunnerThread — roda `tests/run_all_tests.py` sem travar a interface.

O log sai linha a linha (`log_received`); no fim, `tests_finished(código,
caminho do JUnit XML)`. O XML vai para a pasta temporária do sistema, nunca
para o repositório.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6 import QtCore

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TEST_SCRIPT = REPO_ROOT / "tests" / "run_all_tests.py"


class TestRunnerThread(QtCore.QThread):
    __test__ = False  # não é um teste (o pytest coletaria pelo nome)

    log_received = QtCore.Signal(str)
    tests_finished = QtCore.Signal(int, str)  # código de saída, JUnit XML ("" se não houver)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        handle, self.junit_path = tempfile.mkstemp(prefix="lumenia_tests_", suffix=".xml")
        os.close(handle)

    def run(self) -> None:
        if not TEST_SCRIPT.exists():
            self.log_received.emit(f"Erro: Script não encontrado em {TEST_SCRIPT}\n")
            self.tests_finished.emit(1, "")
            return
        cmd = [sys.executable, str(TEST_SCRIPT), "--junit", self.junit_path]
        try:
            process = subprocess.Popen(
                cmd, cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
            for line in iter(process.stdout.readline, ""):
                if line:
                    self.log_received.emit(line)
            process.stdout.close()
            self.tests_finished.emit(process.wait(), self.junit_path)
        except OSError as exc:
            self.log_received.emit(f"Falha na execução: {exc}\n")
            self.tests_finished.emit(1, "")
