"""BackgroundQueue — uma fila de trabalhos numa thread só, com o resultado de volta na thread do dono.

A base do `DocumentSaver` (gravar) e do `DocumentLoader` (abrir): cada um precisa de uma thread de
fundo que faça um trabalho de cada vez, na ordem pedida, e devolva o resultado ou o erro por
callback na thread da interface. Antes de 2026-10-01 isto era o corpo do `DocumentSaver`; abrir
sem travar pediu a mesma coisa, e duas cópias teriam divergido.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from PySide6 import QtCore

logger = logging.getLogger(__name__)


@dataclass
class _Job:
    work: Callable[[], Any]
    on_done: Optional[Callable[[Any], None]]
    on_error: Optional[Callable[[Exception], None]]
    tag: Optional[str]
    label: str


class _Run(QtCore.QRunnable):
    def __init__(self, job: _Job, finished: QtCore.SignalInstance) -> None:
        super().__init__()
        self.setAutoDelete(False)  # a fila guarda a referência até o resultado chegar
        self._job, self._finished = job, finished

    def run(self) -> None:
        result, error = None, None
        try:
            result = self._job.work()
        except Exception as exc:  # noqa: BLE001 -- vai ao `on_error` na thread da interface
            error = exc
        self._finished.emit(self._job, result, error)


class BackgroundQueue(QtCore.QObject):
    idle = QtCore.Signal()  # a fila esvaziou
    _finished = QtCore.Signal(object, object, object)  # emitido na thread de fundo; entregue na do dono

    def __init__(self, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._pool = QtCore.QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._running: dict[int, tuple[_Job, _Run]] = {}
        self._finished.connect(self._on_finished)

    def submit(
        self,
        work: Callable[[], Any],
        on_done: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        tag: Optional[str] = None,
        label: str = "trabalho",
    ) -> None:
        """Enfileira `work` (roda na thread de fundo). Os callbacks voltam na thread de quem chamou."""
        job = _Job(work, on_done, on_error, tag, label)
        run = _Run(job, self._finished)
        self._running[id(job)] = (job, run)
        self._pool.start(run)

    def is_busy(self) -> bool:
        return bool(self._running)

    def has_tag(self, tag: str) -> bool:
        return any(job.tag == tag for job, _run in self._running.values())

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

    @QtCore.Slot(object, object, object)
    def _on_finished(self, job: _Job, result: Any, error: Optional[Exception]) -> None:
        self._running.pop(id(job), None)
        try:
            if error is None:
                if job.on_done is not None:
                    job.on_done(result)
            elif job.on_error is not None:
                job.on_error(error)
            else:
                logger.error("%s falhou sem quem a tratasse: %s", job.label, error)
        except Exception:  # noqa: BLE001 -- um callback com defeito não derruba a fila
            logger.exception("Falha no tratamento do resultado de: %s", job.label)
        if not self._running:
            self.idle.emit()
