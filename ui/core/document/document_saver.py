"""DocumentSaver — grava documentos numa thread própria, sem travar a interface (S1.2).

Salvar tem duas metades (`save_capture.py`). A primeira, `capture_document`, roda na thread da
interface e leva poucos milissegundos. A segunda, `DocumentSerializer.write`, comprime e grava
o arquivo (segundos num documento grande) e roda aqui, na thread de uma `BackgroundQueue`: uma
gravação por vez, na ordem em que chegaram, para que duas gravações do mesmo arquivo nunca se
atropelem e a última capturada seja a última gravada.

O resultado volta pela thread de quem criou o `DocumentSaver`: os callbacks `on_done` e `on_error`
rodam na thread da interface e podem tocar nela. Quem fecha o programa espera por `wait_idle`:
uma gravação em andamento não se perde.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtCore

from .background_queue import BackgroundQueue
from .save_capture import SaveCapture
from .serializer import DocumentSerializer

Writer = Callable[[SaveCapture], str]


class DocumentSaver(QtCore.QObject):
    idle = QtCore.Signal()  # a fila esvaziou

    def __init__(self, parent: Optional[QtCore.QObject] = None, writer: Writer = DocumentSerializer.write) -> None:
        super().__init__(parent)
        self._writer = writer
        self._queue = BackgroundQueue(self)
        self._queue.idle.connect(self.idle)

    def submit(
        self,
        capture: SaveCapture,
        on_done: Optional[Callable[[SaveCapture], None]] = None,
        on_error: Optional[Callable[[SaveCapture, Exception], None]] = None,
    ) -> None:
        """Enfileira a gravação de `capture`. Os callbacks voltam na thread de quem chamou."""
        self._queue.submit(
            lambda: self._writer(capture),
            on_done=(lambda _path: on_done(capture)) if on_done is not None else None,
            on_error=(lambda exc: on_error(capture, exc)) if on_error is not None else None,
            tag=capture.uid,
            label=f"gravação de '{capture.target}'",
        )

    def is_busy(self) -> bool:
        return self._queue.is_busy()

    def is_saving(self, uid: str) -> bool:
        return self._queue.has_tag(uid)

    def wait_idle(self, timeout_ms: int = 120_000) -> bool:
        return self._queue.wait_idle(timeout_ms)
