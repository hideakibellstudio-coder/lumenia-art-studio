"""
Tool Cursor Renderer — Renderizador de Cursores de Precisão e Anéis de Contorno.
================================================================================
Renderiza anéis de alto contraste (branco/preto) escalados em tempo real pela
câmera (zoom) e fornece cursores SVG especializados com hotspots exatos e cache.
"""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.icons import get_icon


class ToolCursorRenderer:
    """Motor de renderização de cursores na viewport do canvas."""

    _cursor_cache: dict[tuple[str, int], QtGui.QCursor] = {}
    _cached_pens: dict[float, tuple[QtGui.QPen, QtGui.QPen, QtGui.QPen]] = {}

    @classmethod
    def _get_pens(cls, opacity: float) -> tuple[QtGui.QPen, QtGui.QPen, QtGui.QPen]:
        op_key = round(max(0.0, min(1.0, opacity)), 2)
        pens = cls._cached_pens.get(op_key)
        if pens is None:
            pen_white = QtGui.QPen(QtGui.QColor(255, 255, 255, int(230 * op_key)), 1.5)
            pen_white.setCosmetic(True)
            pen_black = QtGui.QPen(QtGui.QColor(0, 0, 0, int(180 * op_key)), 0.75)
            pen_black.setCosmetic(True)
            pen_ch = QtGui.QPen(QtGui.QColor(255, 255, 255, 220), 1.0)
            pen_ch.setCosmetic(True)
            pens = (pen_white, pen_black, pen_ch)
            cls._cached_pens[op_key] = pens
        return pens

    @staticmethod
    def get_cursor_settings() -> dict:
        from ui.core.config import ConfigManager
        sec = ConfigManager.instance().get_section("cursor")
        return {
            "mode": sec.get("mode", "ring_and_dot"),
            "hide_on_stroke": sec.get("hide_on_stroke", False),
            "show_crosshair": sec.get("show_crosshair", False),
            "ring_opacity": float(sec.get("ring_opacity", 0.9)),
        }

    @staticmethod
    def get_cursor_rect(screen_x: float, screen_y: float, brush_radius: float, zoom: float, margin: int = 16) -> QtCore.QRect:
        r = max(10, int(float(brush_radius) * float(zoom)) + margin)
        return QtCore.QRect(int(screen_x - r), int(screen_y - r), r * 2 + 1, r * 2 + 1)

    @classmethod
    def render_cursor(
        cls,
        painter: QtGui.QPainter,
        screen_x: float,
        screen_y: float,
        brush_radius: float,
        zoom: float,
        is_painting: bool = False,
        settings: dict | None = None
    ) -> None:
        """Desenha o indicador geométrico de pincel com alto contraste e anti-aliasing."""
        if settings is None:
            settings = cls.get_cursor_settings()

        mode = settings.get("mode", "ring_and_dot")
        if mode == "system":
            return

        if is_painting and settings.get("hide_on_stroke", False):
            return

        screen_radius = float(brush_radius) * float(zoom)
        cx = float(screen_x)
        cy = float(screen_y)

        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)

        op = float(settings.get("ring_opacity", 0.9))
        pen_white, pen_black, pen_ch = cls._get_pens(op)

        # 1. Renderização do Anel de Contorno (Borda Dupla Branco / Preto)
        if mode in ("ring_and_dot", "ring_only") and screen_radius >= 1.0:
            # Anel Externo Branco
            painter.setPen(pen_white)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(QtCore.QPointF(cx, cy), screen_radius, screen_radius)

            # Anel Interno Preto de Contraste
            painter.setPen(pen_black)
            painter.drawEllipse(QtCore.QPointF(cx, cy), screen_radius, screen_radius)

        # 2. Ponto Central (Dot)
        if mode in ("ring_and_dot", "dot_only"):
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QColor(0, 0, 0, 200))
            painter.drawEllipse(QtCore.QPointF(cx, cy), 2.0, 2.0)
            painter.setBrush(QtGui.QColor(255, 255, 255, 255))
            painter.drawEllipse(QtCore.QPointF(cx, cy), 1.0, 1.0)

        # 3. Mira de Precisão (Crosshair)
        if mode == "crosshair" or settings.get("show_crosshair", False):
            ch_len = max(6.0, min(14.0, screen_radius + 4.0))
            painter.setPen(pen_ch)
            painter.drawLine(QtCore.QPointF(cx - ch_len, cy), QtCore.QPointF(cx + ch_len, cy))
            painter.drawLine(QtCore.QPointF(cx, cy - ch_len), QtCore.QPointF(cx, cy + ch_len))

        painter.restore()

    @classmethod
    def create_custom_cursor(cls, icon_name: str, size: int = 24) -> QtGui.QCursor:
        """Gera um cursor nativo QCursor a partir do catálogo SVG com hotspot calibrado e cache."""
        cache_key = (icon_name, size)
        if cache_key in cls._cursor_cache:
            return cls._cursor_cache[cache_key]

        hotspots = {
            "eyedropper": (2, 22),
            "bucket": (4, 20),
            "eraser": (6, 20),
            "wand": (2, 2),
            "move": (12, 12),
            "transform": (12, 12),
        }
        hot_x, hot_y = hotspots.get(icon_name, (0, 0))
        icon = get_icon(icon_name, "text_main", QtCore.QSize(size, size))
        pixmap = icon.pixmap(size, size)
        if pixmap.isNull():
            cursor = QtGui.QCursor(QtCore.Qt.ArrowCursor)
        else:
            cursor = QtGui.QCursor(pixmap, hot_x, hot_y)

        cls._cursor_cache[cache_key] = cursor
        return cursor
