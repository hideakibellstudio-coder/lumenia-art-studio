"""
DocumentFrameSource — de onde vem cada quadro do timelapse.
===========================================================
Pixels compostos pelo motor (`EngineBackend`) e tamanho, papel e guias do
documento ativo (`Document`, a fonte única). Até 2026-09-24 o motor de
gravação guardava o canvas e lia dele tudo isso com `getattr`
(`canvas.backend`, `canvas.canvas_w`, `canvas.paper_color`,
`canvas.geometry_ctrl.guide_state`...).

Testes (e outros motores) entregam qualquer função `grab(include_guides)`
que devolva um `Frame` ou None.
"""
from __future__ import annotations

import copy
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from PySide6 import QtCore, QtGui

from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Frame:
    pixels: bytes          # RGBA8888, width × height
    width: int
    height: int
    guides: Optional[dict]  # {"sym": ..., "guide": ...} ou None


def active_guides(sym_state: Optional[dict], guide_state: Optional[dict]) -> Optional[dict]:
    """Guias e simetria visíveis agora (cópias), ou None se não houver nenhuma."""
    has_sym = bool(sym_state) and sym_state.get("mode", "none") != "none"
    has_guide = (bool(guide_state) and guide_state.get("type", "none") != "none"
                 and not guide_state.get("hidden", False))
    if not (has_sym or has_guide):
        return None
    return {
        "sym": copy.deepcopy(sym_state) if has_sym else None,
        "guide": copy.deepcopy(guide_state) if has_guide else None,
    }


class DocumentFrameSource:
    def __init__(
        self,
        backend: Optional[Callable[[], Any]] = None,
        document: Optional[Callable[[], Any]] = None,
    ) -> None:
        self._backend = backend or (lambda: EngineRegistry.instance().get_backend())
        self._document = document or (lambda: DocumentManager.instance().active_document())

    def __call__(self, include_guides: bool) -> Optional[Frame]:
        return self.grab(include_guides)

    def grab(self, include_guides: bool) -> Optional[Frame]:
        doc = self._document()
        backend = self._backend()
        if doc is None or backend is None:
            return None
        width, height = int(doc.width), int(doc.height)
        pixels = self._pixels(backend, doc, width, height)
        if not pixels:
            logger.warning("[Timelapse] Nenhum pixel obtido da composição do documento.")
            return None
        guides = active_guides(doc.sym_state, doc.guide_state) if include_guides else None
        return Frame(pixels, width, height, guides)

    @staticmethod
    def _pixels(backend, doc, width: int, height: int) -> Optional[bytes]:
        raw = backend.get_display_pixel_buffer()
        if raw:
            return bytes(raw)
        # Backend sem buffer de exibição: compõe a imagem do motor sobre o papel.
        image = backend.get_qimage()
        if image is None or image.isNull():
            return None
        frame = QtGui.QImage(width, height, QtGui.QImage.Format.Format_RGBA8888)
        frame.fill(doc.paper_color if doc.paper_visible else QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(frame)
        painter.drawImage(0, 0, image)
        painter.end()
        return bytes(frame.constBits())
