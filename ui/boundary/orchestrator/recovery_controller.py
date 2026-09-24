"""RecoveryController — cópias periódicas de recuperação e a oferta de reabri-las.

Colaborador da `MainWindow` (ver `shell_actions.py`). Dono do
`RecoveryStore` e do timer. Reabrir uma cópia usa o mesmo caminho de "Abrir"
(`DocumentActions.open_native_document`).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from ui.core.i18n import tr
from ui.core.config.manager import ConfigManager
from ui.core.document.document import Document
from ui.core.document.manager import DocumentManager
from ui.core.document.recovery import RecoveryStore

from .document_actions import DocumentActions
from .shell_actions import BackendProvider, ShellActions
from .workspace_port import ShellCanvas

_INTERVAL_MS = 60000


class RecoveryController(ShellActions):
    def __init__(
        self,
        window: QtWidgets.QWidget,
        dm: DocumentManager,
        backend: BackendProvider,
        canvas: Optional[ShellCanvas],
        documents: DocumentActions,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._dm = dm
        self._backend = backend
        self._canvas = canvas
        self._documents = documents
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
        try:
            document: Document
            for document in self._dm.documents():
                if document.is_dirty:
                    backend.set_active_document_context(document.uid, document.width, document.height)
                    self.store.capture(document, backend)
        except Exception as exc:
            self._say(tr("status.recovery_create_failed", "Falha ao criar recuperação: {error}", error=exc), 10000)
        finally:
            backend.set_active_document_context(active.uid, active.width, active.height)

    def offer(self) -> None:
        candidates = self.store.candidates()
        if not candidates:
            return
        answer = QtWidgets.QMessageBox.question(
            self._window, "Recuperação de documentos",
            f"Encontradas {len(candidates)} cópias de recuperação. Deseja abri-las?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if answer != QtWidgets.QMessageBox.Yes:
            return
        for path in candidates:
            if not self._documents.open_native_document(str(path)):
                continue
            document: Document = self._dm.active_document()
            document.file_path = None
            document.mark_dirty("recovery")
            # Mantém a cópia original até existir um snapshot novo e durável.
            try:
                self.store.capture(document, self._backend())
                self.store.discard_candidate(path)
            except Exception as exc:
                self._say(tr("status.recovery_opened_kept", "Recuperação aberta; cópia original mantida: {error}", error=exc), 5000)
