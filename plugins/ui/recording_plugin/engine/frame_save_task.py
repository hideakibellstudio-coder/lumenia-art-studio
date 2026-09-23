"""
FrameSaveTask — Tarefa Assíncrona de Salvamento de Frames de Gravação (ARCcC).
=============================================================================
Processa a conversão de buffers, aplicação de overlays de guias, redimensionamento
e marca d'água em thread secundária (QRunnable) para garantir zero interrupção
no traçado em tempo real da caneta / pincel.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

from PySide6 import QtCore, QtGui

logger = logging.getLogger(__name__)


class FrameSaveTask(QtCore.QRunnable):
    """Tarefa assíncrona de escrita de imagem para não engasgar o traçado da caneta."""

    def __init__(
        self,
        raw_bytes: bytes,
        width: int,
        height: int,
        target_w: int,
        target_h: int,
        output_path: str,
        watermark: bool = False,
        guides_data: Optional[Dict[str, Any]] = None,
        guides_renderer: Optional[Callable[..., Any]] = None,
        watermark_renderer: Optional[Callable[[QtGui.QImage], Any]] = None,
    ):
        super().__init__()
        self.raw_bytes = raw_bytes
        self.width, self.height = width, height
        self.target_w, self.target_h = target_w, target_h
        self.output_path = output_path
        self.watermark = watermark
        self.guides_data = guides_data
        self.guides_renderer = guides_renderer
        self.watermark_renderer = watermark_renderer

    def run(self) -> None:
        try:
            img = QtGui.QImage(
                self.raw_bytes,
                self.width,
                self.height,
                self.width * 4,
                QtGui.QImage.Format.Format_RGBA8888,
            )
            if img.isNull():
                return

            # 1. Renderiza as guias ativas via callback injetado (sem cross-plugin import)
            if self.guides_data and self.guides_renderer is not None:
                try:
                    p_guides = QtGui.QPainter(img)
                    p_guides.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
                    sym = self.guides_data.get("sym")
                    guide = self.guides_data.get("guide")
                    self.guides_renderer(p_guides, sym, guide, 1.0)
                    p_guides.end()
                except Exception as e:
                    logger.debug("[TimelapseEngine] Falha ao renderizar guias no frame: %s", e)

            # 2. Redimensiona se resolução alvo for diferente e válida
            if self.target_w > 0 and self.target_h > 0 and (self.target_w != self.width or self.target_h != self.height):
                img = img.scaled(
                    self.target_w,
                    self.target_h,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )

            # 3. Aplica marca d'água no canto inferior direito se solicitado
            if self.watermark:
                if self.watermark_renderer is not None:
                    self.watermark_renderer(img)
                else:
                    from .recording_engine import TimelapseRecordingEngine
                    TimelapseRecordingEngine.apply_watermark(img)

            # 4. Salva JPEG com compressão otimizada
            img.save(self.output_path, "JPEG", 90)
        except Exception as e:
            logger.error("[TimelapseEngine] Falha ao salvar frame %s: %s", self.output_path, e)
