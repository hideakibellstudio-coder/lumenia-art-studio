"""DocumentSaver — grava documentos numa thread própria, sem travar a interface (S1.2).

Salvar tem duas metades (`save_capture.py`). A primeira, `capture_document`, roda na thread da
interface e leva poucos milissegundos. A segunda, `DocumentSerializer.write`, comprime e grava
o arquivo (segundos num documento grande) e roda aqui, numa thread só: uma gravação por vez,
na ordem em que chegaram, para que duas gravações do mesmo arquivo nunca se atropelem e a
última capturada seja a última gravada.

O resultado volta pela thread de quem criou o `DocumentSaver` (sinal enfileirado do Qt): os
callbacks `on_done` e `on_error` rodam na thread da interface e podem tocar nela.

Quem fecha o programa espera por `wait_idle`: uma gravação em andamento não se perde.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6 import QtCore

from .save_capture import SaveCapture
from .serializer import DocumentSerializer

logger = logging.getLogger(__name__)

Writer = Callable[[SaveCapture], str]


@dataclass
class _Job:
    capture: SaveCapture
    on_done: Optional[Callable[[SaveCapture], None]]
    on_error: Optional[Callable[[SaveCapture, Exception], None]]


class _Run(QtCore.QRunnable):
    def __init__(self, job: _Job, writer: Writer, finished: QtCore.SignalInstance) -> None:
        super().__init__()
        self.setAutoDelete(False)  # o DocumentSaver guarda a referência até o resultado chegar
        self._job, self._writer, self._finished = job, writer, finished

    def run(self) -> None:
        error: Optional[Exception] = None
        try:
            self._writer(self._job.capture)
        except Exception as exc:  # noqa: BLE001 -- vai ao `on_error` na thread da interface
            error = exc
        self._finished.emit(self._job, error)


class DocumentSaver(QtCore.QObject):
    idle = QtCore.Signal()  # a fila esvaziou
    _finished = QtCore.Signal(object, object)  # emitido na thread de gravação; entregue na do dono

    def __init__(self, parent: Optional[QtCore.QObject] = None, writer: Writer = DocumentSerializer.write) -> None:
        super().__init__(parent)
        self._writer = writer
        self._pool = QtCore.QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._running: dict[int, tuple[_Job, _Run]] = {}
        self._finished.connect(self._on_finished)

    def submit(
        self,
        capture: SaveCapture,
        on_done: Optional[Callable[[SaveCapture], None]] = None,
        on_error: Optional[Callable[[SaveCapture, Exception], None]] = None,
    ) -> None:
        """Enfileira a gravação de `capture`. Os callbacks voltam na thread de quem chamou."""
        job = _Job(capture, on_done, on_error)
        run = _Run(job, self._writer, self._finished)
        self._running[id(job)] = (job, run)
        self._pool.start(run)

    def is_busy(self) -> bool:
        return bool(self._running)

    def is_saving(self, uid: str) -> bool:
        return any(job.capture.uid == uid for job, _run in self._running.values())

    def wait_idle(self, timeout_ms: int = 120_000) -> bool:
        """Espera a fila esvaziar, desenhando a interface mas ignorando o que o usuário digita."""
        if not self._running:
            return True
        loop = QtCore.QEventLoop()
        timer = QtCore.QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)
        self.idle.connect(loop.quit)
        timer.start(timeout_ms)
        loop.exec(QtCore.QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
        timer.stop()
        self.idle.disconnect(loop.quit)
        return not self._running

    @QtCore.Slot(object, object)
    def _on_finished(self, job: _Job, error: Optional[Exception]) -> None:
        self._running.pop(id(job), None)
        try:
            if error is None:
                if job.on_done is not None:
                    job.on_done(job.capture)
            elif job.on_error is not None:
                job.on_error(job.capture, error)
            else:
                logger.error("Gravação de '%s' falhou sem quem a tratasse: %s", job.capture.target, error)
        except Exception:  # noqa: BLE001 -- um callback com defeito não derruba a fila
            logger.exception("Falha no tratamento do resultado da gravação de '%s'", job.capture.target)
        if not self._running:
            self.idle.emit()
