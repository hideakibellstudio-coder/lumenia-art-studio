"""
TextToolController — Controlador de Edição e Inserção de Texto no Canvas.
==========================================================================
Encapsula o ciclo de vida do TextOverlayEditor, criação da imagem raster de texto,
composição na camada ativa via backend nativo C++ e renderização do texto em andamento.
"""

from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING
from PySide6 import QtCore, QtGui
from ui.core.tool_settings import default_tool_settings, normalize_tool_settings

if TYPE_CHECKING:
    from ..render_widget import RenderWidget

from ..text_overlay_editor import TextOverlayEditor

logger = logging.getLogger("Workspace.TextTool")


class TextToolController:
    """Controlador atômico responsável pela ferramenta de texto."""

    def __init__(self, widget: RenderWidget) -> None:
        self.widget = widget
        self.settings = default_tool_settings("text")
        self.active_editor: Optional[TextOverlayEditor] = None

    def set_settings(self, new_settings: dict) -> None:
        self.settings = normalize_tool_settings("text", new_settings, self.settings)
        if self.active_editor:
            self.active_editor.apply_typography(self.settings)

    def open_editor(self, canvas_x: float, canvas_y: float) -> None:
        if self.active_editor:
            self.commit()
        self.active_editor = TextOverlayEditor(self.widget, canvas_x, canvas_y, self.settings)
        if hasattr(self.widget, "strokeStarted"):
            self.widget.strokeStarted.emit()
        self.widget.update()

    def commit(self) -> None:
        ed = self.active_editor
        if not ed:
            return

        try:
            text = ed.get_text().strip()
            if text:
                cfg = ed.settings
                w = self.widget.canvas_w
                h = self.widget.canvas_h
                text_img = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32_Premultiplied)
                text_img.fill(QtCore.Qt.transparent)

                p = QtGui.QPainter(text_img)
                p.setRenderHints(QtGui.QPainter.Antialiasing | QtGui.QPainter.TextAntialiasing, True)
                qf = QtGui.QFont(cfg.get("font_family", "Segoe UI"), max(6, int(cfg.get("font_size", 36))))
                qf.setBold(bool(cfg.get("bold", False)))
                qf.setItalic(bool(cfg.get("italic", False)))
                qf.setUnderline(bool(cfg.get("underline", False)))
                p.setFont(qf)
                p.setPen(QtGui.QPen(QtGui.QColor(cfg.get("color", QtGui.QColor(0, 0, 0, 255)))))

                al = cfg.get("align", "left")
                align_f = QtCore.Qt.TextWordWrap | (
                    QtCore.Qt.AlignHCenter if al == "center" else (
                        QtCore.Qt.AlignRight if al == "right" else QtCore.Qt.AlignLeft
                    )
                )
                max_w = max(200.0, float(w) - ed.canvas_pos.x())
                max_h = max(200.0, float(h) - ed.canvas_pos.y())
                p.drawText(QtCore.QRectF(ed.canvas_pos.x(), ed.canvas_pos.y(), max_w, max_h), align_f, text)
                p.end()
                text_rgba = text_img.convertToFormat(QtGui.QImage.Format_RGBA8888)
                px_bytes = text_rgba.constBits().tobytes()
                from ui.core.engine.registry import EngineRegistry
                b = EngineRegistry.instance().get_backend()
                if b and hasattr(b, "paste_rgba_buffer_on_active_layer") and getattr(b, "available", False):
                    b.paste_rgba_buffer_on_active_layer(0, 0, w, h, px_bytes)
                else:
                    logger.warning(
                        "Texto descartado: motor nativo indisponivel (paste_rgba_buffer_on_active_layer). "
                        "Nenhum pixel foi persistido no TileGrid; nada sera salvo no .lmn."
                    )

            ed.hide()
            ed.deleteLater()
            self.active_editor = None
            self.widget.update()
        finally:
            if hasattr(self.widget, "strokeFinished"):
                self.widget.strokeFinished.emit()

    def cancel(self) -> None:
        if self.active_editor:
            self.active_editor.hide()
            self.active_editor.deleteLater()
            self.active_editor = None
            self.widget.update()
            if hasattr(self.widget, "strokeFinished"):
                self.widget.strokeFinished.emit()
