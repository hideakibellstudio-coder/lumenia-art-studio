"""
ui.core.document.local_layer — Modelo de Camada Local do Lumenia
================================================================
Representa uma camada, grupo ou camada de filtro dentro do LocalLayerManager.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui

from ui.core.document.layer_blend_mode import LayerBlendMode


class LocalLayer:
    """Representação local de camada/grupo com miniatura procedural e propriedades."""

    def __init__(self, uid: int, name: str, parent_uid=None, is_group=False, is_filter=False):
        self.uid = uid
        self.id = uid  # Compatibilidade com camada.id
        self.name = name
        self.parent_uid = parent_uid
        self.is_group = is_group
        self.is_filter = is_filter

        self.visible = True
        self.locked = False
        self.opacity = 1.0
        self.blend_mode = LayerBlendMode.PASS_THROUGH if is_group else LayerBlendMode.NORMAL
        self.alpha_locked = False
        self.clipping_mask = False
        self.collapsed = False

        # Miniaturas procedurais simples
        self.thumb = QtGui.QPixmap(38, 28)

        from ui.core.theme.manager import ThemeManager
        theme = ThemeManager.instance()._themes.get(ThemeManager.instance().current_theme, {})
        colors = theme.get("colors", {})

        bg_darker = QtGui.QColor(ThemeManager.instance().resolve_color("BG_DARKER", colors))
        bg_dark = QtGui.QColor(ThemeManager.instance().resolve_color("BG_DARK", colors))
        bg_mid = QtGui.QColor(ThemeManager.instance().resolve_color("BG_MID", colors))
        border = QtGui.QColor(ThemeManager.instance().resolve_color("BORDER", colors))
        accent = QtGui.QColor(ThemeManager.instance().resolve_color("ACCENT", colors))
        accent_muted = QtGui.QColor(ThemeManager.instance().resolve_color("accent_bg", colors))
        bg_light = QtGui.QColor(ThemeManager.instance().resolve_color("BG_LIGHT", colors))

        self.thumb.fill(bg_darker if is_group else bg_dark)

        painter = QtGui.QPainter(self.thumb)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if is_group:
            painter.setPen(QtGui.QPen(border, 1))
            painter.setBrush(bg_mid)
            painter.drawRoundedRect(4, 4, 30, 20, 2, 2)
        elif is_filter:
            painter.setPen(QtGui.QPen(accent, 1))
            painter.setBrush(accent_muted)
            painter.drawRoundedRect(4, 4, 30, 20, 2, 2)
        else:
            painter.setPen(QtGui.QPen(border, 1))
            painter.setBrush(bg_light)
            painter.drawRoundedRect(4, 4, 30, 20, 1, 1)
        painter.end()
