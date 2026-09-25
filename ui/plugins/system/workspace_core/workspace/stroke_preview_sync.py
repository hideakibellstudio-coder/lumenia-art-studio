"""StrokePreviewSync — atualiza as miniaturas depois de cada traço.

Depois de um traço (ou desfazer/refazer), espera 100 ms sem novos traços e
então: emite a imagem reduzida (`navigatorArtwork`, que o workspace liga ao
painel do navegador) e avisa o gerenciador de camadas do documento ativo
para redesenhar as miniaturas.

Extraído do antigo `WorkspaceBrushMixin` em 2026-09-24. Lá o timer era
conectado duas vezes ao mesmo slot, e toda sincronização rodava em dobro.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from PySide6 import QtCore, QtGui

logger = logging.getLogger("Workspace.StrokePreviewSync")

_DEBOUNCE_MS = 100
_NAVIGATOR_THUMB = QtCore.QSize(320, 240)


class StrokePreviewSync(QtCore.QObject):
    navigatorArtwork = QtCore.Signal(QtGui.QImage)

    def __init__(
        self,
        backend_provider: Callable[[], Any],
        document_provider: Callable[[], Any],
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._backend_provider = backend_provider
        self._document_provider = document_provider
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.sync_now)

    def schedule(self) -> None:
        """Pede uma sincronização; várias chamadas seguidas viram uma só."""
        self._timer.start(_DEBOUNCE_MS)

    def sync_now(self) -> None:
        backend = self._backend_provider()
        if backend is None:
            return
        # Só reduz a imagem se houver navegador ligado ao sinal.
        if self.receivers(QtCore.SIGNAL("navigatorArtwork(QImage)")) > 0:
            image = backend.get_qimage()
            if image is not None and not image.isNull():
                self.navigatorArtwork.emit(image.scaled(
                    _NAVIGATOR_THUMB, QtCore.Qt.KeepAspectRatio, QtCore.Qt.FastTransformation
                ))
        document = self._document_provider()
        if document is not None:
            document.layer_manager.request_thumbnails()
