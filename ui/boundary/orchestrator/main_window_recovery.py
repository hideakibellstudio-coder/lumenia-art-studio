"""Periodic recovery and explicit recovery choice on startup."""

from pathlib import Path
from PySide6 import QtCore, QtWidgets
from ui.core.config.manager import ConfigManager
from ui.core.document.recovery import RecoveryStore
from ui.core.engine.registry import EngineRegistry
from ui.core.document.document import Document


class MainWindowRecoveryMixin:
    def setup_recovery(self):
        config = ConfigManager.instance()
        self.recovery = RecoveryStore(Path(config.config_path).parent / "recovery")
        self.dm.documentClosed.connect(self._discard_recovery)
        if self.canvas_widget is not None:
            self.canvas_widget.strokeFinished.connect(self._mark_canvas_changed)
        self.recovery_timer = QtCore.QTimer(self)
        self.recovery_timer.setInterval(60000)
        self.recovery_timer.timeout.connect(self._capture_recovery)
        if not config.is_test_mode:
            self.recovery_timer.start()
            QtCore.QTimer.singleShot(0, self, self._offer_recovery)

    def _mark_canvas_changed(self):
        document = self.dm.active_document()
        if document:
            document.mark_dirty("canvas")

    def _discard_recovery(self, uid):
        try:
            self.recovery.discard(uid)
        except OSError as exc:
            self.status_bar.showMessage(f"Falha ao limpar recuperação: {exc}", 5000)

    def _capture_recovery(self):
        if self.canvas_widget is not None and self.canvas_widget.drawing:
            return
        if self.workspace and getattr(getattr(self.canvas_widget, "transform_ctrl", None), "active", False):
            return
        active = self.dm.active_document()
        backend = EngineRegistry.instance().get_backend()
        if not active or not backend or not backend.available:
            return
        try:
            document: Document
            for document in self.dm.documents():
                if document.is_dirty:
                    backend.set_active_document_context(document.uid, document.width, document.height)
                    self.recovery.capture(document, backend)
        except Exception as exc:
            self.status_bar.showMessage(f"Falha ao criar recuperação: {exc}", 10000)
        finally:
            backend.set_active_document_context(active.uid, active.width, active.height)

    def _offer_recovery(self):
        candidates = self.recovery.candidates()
        if not candidates:
            return
        answer = QtWidgets.QMessageBox.question(
            self, "Recuperação de documentos",
            f"Encontradas {len(candidates)} cópias de recuperação. Deseja abri-las?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if answer != QtWidgets.QMessageBox.Yes:
            return
        for path in candidates:
            if self.open_native_document(str(path)):
                document: Document = self.dm.active_document()
                document.file_path = None
                document.mark_dirty("recovery")
                # Keep the recovered source until a new durable snapshot exists.
                backend = EngineRegistry.instance().get_backend()
                try:
                    self.recovery.capture(document, backend)
                    self.recovery.discard_candidate(path)
                except Exception as exc:
                    self.status_bar.showMessage(f"Recuperação aberta; cópia original mantida: {exc}", 5000)
