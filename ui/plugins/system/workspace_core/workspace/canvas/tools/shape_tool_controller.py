"""Vector and Geometric Shape Tool Controller."""

import logging
from typing import Any, Optional, Protocol, runtime_checkable
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.backend_protocols import CoreLifecycleProtocol, SelectionTransformProtocol
from ui.core.tool_settings import default_tool_settings

from .shape_paths import build_shape_path

logger = logging.getLogger("Workspace.ShapeTool")


class ShapeEngine(CoreLifecycleProtocol, SelectionTransformProtocol, Protocol):
    """A forma entra na camada ativa colada (`SelectionTransform`) e só se o motor está disponível (`CoreLifecycle`)."""


@runtime_checkable
class ShapeCanvas(Protocol):
    """O que a ferramenta de forma usa do canvas. Membro novo usado aqui entra neste contrato;
    `tests/test_canvas_contracts.py` confere que o `RenderWidget` o cumpre."""
    canvas_w: int
    canvas_h: int
    backend: Optional[ShapeEngine]
    strokeFinished: Any

    def update(self) -> None: ...


class ShapeToolController:
    """Controlador de desenho e rasterização de formas vetoriais no ALADYN ENGINE."""

    def __init__(self, widget: ShapeCanvas):
        self.widget = widget
        self.settings = default_tool_settings("shapes")
        self.drag_active: bool = False
        self.drag_start: QtCore.QPointF = QtCore.QPointF(0, 0)
        self.drag_current: QtCore.QPointF = QtCore.QPointF(0, 0)

    def calculate_path(self):
        """Caminho da forma em arraste (geometria em `shape_paths.py`)."""
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        return build_shape_path(
            self.settings.get("shape_type", "shape_line"), self.drag_start, self.drag_current, self.settings,
            shift=bool(modifiers & QtCore.Qt.ShiftModifier), alt=bool(modifiers & QtCore.Qt.AltModifier),
        )

    def commit_to_layer(self):
        path = self.calculate_path()
        if not path:
            self.widget.update()
            self.widget.strokeFinished.emit()
            return

        shape_type = self.settings.get("shape_type", "shape_line")
        draw_mode = self.settings.get("draw_mode", "both")
        stroke_w = float(self.settings.get("stroke_width", 4))
        stroke_col = QtGui.QColor(self.settings.get("stroke_color", QtGui.QColor(0, 0, 0, 255)))
        fill_col = QtGui.QColor(self.settings.get("fill_color", QtGui.QColor(0, 0, 0, 255)))

        shape_img = QtGui.QImage(self.widget.canvas_w, self.widget.canvas_h, QtGui.QImage.Format_ARGB32_Premultiplied)
        shape_img.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(shape_img)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        pen = QtGui.QPen(stroke_col, stroke_w, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin) if draw_mode in ("both", "stroke") else QtCore.Qt.NoPen
        brush = QtGui.QBrush(fill_col) if (draw_mode in ("both", "fill") and shape_type != "shape_line") else QtCore.Qt.NoBrush

        painter.setPen(pen)
        painter.setBrush(brush)

        if isinstance(path, QtGui.QPainterPath):
            painter.drawPath(path)
        elif isinstance(path, QtCore.QLineF):
            painter.drawLine(path)
        elif isinstance(path, QtCore.QRectF):
            painter.drawRect(path)

        painter.end()

        shape_rgba = shape_img.convertToFormat(QtGui.QImage.Format_RGBA8888)
        ptr = shape_rgba.constBits()
        px_bytes = ptr.tobytes()

        backend = self.widget.backend
        if backend and backend.available:
            backend.paste_rgba_buffer_on_active_layer(0, 0, self.widget.canvas_w, self.widget.canvas_h, px_bytes)
            self.widget.update()
            self.widget.strokeFinished.emit()
        else:
            self.widget.update()
            self.widget.strokeFinished.emit()
            logger.warning(
                "Forma descartada: motor nativo indisponivel (paste_rgba_buffer_on_active_layer). "
                "Nenhum pixel foi persistido no TileGrid; nada sera salvo no .lmn."
            )

