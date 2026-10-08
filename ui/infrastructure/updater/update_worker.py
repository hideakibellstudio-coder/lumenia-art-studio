"""Looks for and downloads an update on a thread of its own, so the window never waits on the network."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6 import QtCore

from ui.infrastructure.updater.velopack_updater import FoundUpdate, VelopackUpdater

logger = logging.getLogger(__name__)


class UpdateWorker(QtCore.QObject):
    found = QtCore.Signal(object)         # FoundUpdate, or None when up to date
    progress = QtCore.Signal(int)         # 0..100 while downloading
    downloaded = QtCore.Signal(object)    # FoundUpdate, ready to apply
    failed = QtCore.Signal(str)

    def __init__(self, updater: VelopackUpdater) -> None:
        super().__init__()
        self._updater = updater

    @QtCore.Slot()
    def check(self) -> None:
        try:
            self.found.emit(self._updater.check())
        except Exception as exc:  # network, feed or Velopack: never takes the program down
            logger.warning("Busca de atualização falhou: %s", exc)
            self.failed.emit(str(exc))

    @QtCore.Slot(object)
    def download(self, update: FoundUpdate) -> None:
        try:
            self._updater.download(update, self.progress.emit)
            self.downloaded.emit(update)
        except Exception as exc:
            logger.warning("Download da atualização %s falhou: %s", update.version, exc)
            self.failed.emit(str(exc))


class UpdateThread(QtCore.QObject):
    """Owns the worker's thread. `check()` and `download()` return at once; the answers arrive as signals."""

    checkRequested = QtCore.Signal()
    downloadRequested = QtCore.Signal(object)

    def __init__(self, updater: VelopackUpdater, parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self.updater = updater
        self.worker = UpdateWorker(updater)
        self._thread: Optional[QtCore.QThread] = None  # started on the first request, not at construction
        self.checkRequested.connect(self.worker.check)
        self.downloadRequested.connect(self.worker.download)

    def _ensure_thread(self) -> None:
        if self._thread is None:
            self._thread = QtCore.QThread()
            self._thread.setObjectName("lumenia-updates")
            self.worker.moveToThread(self._thread)
            self._thread.start()

    def check(self) -> None:
        self._ensure_thread()
        self.checkRequested.emit()

    def download(self, update: FoundUpdate) -> None:
        self._ensure_thread()
        self.downloadRequested.emit(update)

    def stop(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(5000)
            self._thread = None
