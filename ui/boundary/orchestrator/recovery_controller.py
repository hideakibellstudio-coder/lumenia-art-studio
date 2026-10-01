"""RecoveryController — cópias periódicas de recuperação e a oferta de reabri-las.

Colaborador da `MainWindow` (ver `shell_actions.py`). Dono do
`RecoveryStore` e do timer. Reabrir uma cópia usa o mesmo caminho de "Abrir"
(`DocumentActions.open_native_document`).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.infrastructure.i18n import tr
from ui.infrastructure.config.manager import ConfigManager
from ui.core.document.document import Document
from ui.core.document.document_saver import DocumentSaver
from ui.core.document.save_capture import CaptureEngine, SaveCapture
from ui.core.document.manager import DocumentManager
from ui.core.document.recovery import RecoveryStore
from ui.core.engine.backend_protocols import RoleProvider

from .document_actions import DocumentActions
from .shell_actions import ShellActions
from .workspace_port import ShellCanvas

_INTERVAL_MS = 60000


class RecoveryController(ShellActions):
    def __init__(
        self,
        window: QtWidgets.QWidget,
        dm: DocumentManager,
        backend: RoleProvider[CaptureEngine],
        canvas: Optional[ShellCanvas],
        documents: DocumentActions,
        saver: DocumentSaver,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._dm = dm
        self._backend = backend
        self._canvas = canvas
        self._documents = documents
        self._saver = saver
        config = ConfigManager.instance()
        self.store = RecoveryStore(Path(config.config_path).parent / "recovery")
        dm.documentClosed.connect(self.discard)
        documents.documentSaved.connect(self.discard)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(_INTERVAL_MS)
        self.timer.timeout.connect(self.capture)
        if not config.is_test_mode:
            self.timer.start()
            QtCore.QTimer.singleShot(0, self, self.offer)

    def close(self) -> None:
        self.timer.stop()
        self.store.close()

    def discard(self, uid: str) -> None:
        try:
            self.store.discard(uid)
        except OSError as exc:
            self._say(tr("status.recovery_clear_failed", "Falha ao limpar recuperação: {error}", error=exc), 5000)

    def capture(self) -> None:
        if self._canvas is not None and self._canvas.is_busy:
            return
        active = self._dm.active_document()
        backend = self._backend()
        if not active or not backend or not backend.available:
            return
        # A captura de cada documento leva poucos ms e a gravação roda na thread do `DocumentSaver`:
        # a interface não trava (eram ~4 s por documento grande, a cada minuto).
        try:
            document: Document
            for document in self._dm.documents():
                if document.is_dirty:
                    backend.set_active_document_context(document.uid, document.width, document.height)
                    capture = self.store.prepare(document, backend)
                    if capture is not None:
                        self._saver.submit(capture, on_done=self._written, on_error=self._failed)
        except Exception as exc:
            self._say(tr("status.recovery_create_failed", "Falha ao criar recuperação: {error}", error=exc), 10000)
        finally:
            backend.set_active_document_context(active.uid, active.width, active.height)

    def _written(self, capture: SaveCapture) -> None:
        self.store.finish(capture, written=True)

    def _failed(self, capture: SaveCapture, error: Exception) -> None:
        self.store.finish(capture, written=False)
        self._say(tr("status.recovery_create_failed", "Falha ao criar recuperação: {error}", error=error), 10000)

    def offer(self) -> None:
        candidates = self.store.candidates()
        if not candidates:
            return
        answer = QtWidgets.QMessageBox.question(
            self._window, tr("messages.recovery_title", "Recuperação de documentos"),
            tr("messages.recovery_question", "Encontradas {count} cópias de recuperação. Deseja abri-las?",
               count=len(candidates)),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if answer != QtWidgets.QMessageBox.Yes:
            return
        for path in candidates:
            self._documents.open_native_document(str(path), then=lambda document, source=path: self.adopt_recovered(document, source))

    def adopt_recovered(self, document: Document, source: Path) -> None:
        """Uma cópia reaberta é um documento novo e sujo, sem arquivo: o artista decide onde salvar."""
        document.file_path = None
        document.mark_dirty("recovery")
        # Mantém a cópia original até existir um snapshot novo e durável.
        try:
            self.store.capture(document, self._backend())
            self.store.discard_candidate(source)
        except Exception as exc:
            self._say(tr("status.recovery_opened_kept", "Recuperação aberta; cópia original mantida: {error}", error=exc), 5000)
