"""SidebarButton component for Workspace Dock System."""

from __future__ import annotations
import time
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.icons import get_icon, SVG_ICONS, ALIASES

# Mapeamento inteligente de fallback para IDs e títulos de painéis
PANEL_ICON_MAP = {
    # Cores
    "color": "palette",
    "colors": "palette",
    "color_wheel": "palette",
    "color_plugin": "palette",
    "palette": "palette",
    "cores": "palette",
    "roda_de_cores": "palette",

    # Pincéis & Ferramentas
    "brush": "brush",
    "brushes": "brush",
    "brush_settings": "brush",
    "brush_plugin": "brush",
    "pincel": "brush",
    "pincéis": "brush",
    "ferramentas": "brush",
    "tools": "tools",

    # Camadas
    "layer": "layers",
    "layers": "layers",
    "layers_plugin": "layers",
    "camadas": "layers",

    # Navegador
    "navigator": "compass",
    "navigator_plugin": "compass",
    "navegador": "compass",
    "nav": "compass",
    "compass": "compass",

    # Geometria, Guias & Simetria
    "geometry": "shapes",
    "geometry_plugin": "shapes",
    "shapes": "shapes",
    "guias": "ruler",
    "simetria": "shapes",
    "ruler": "ruler",

    # Telemetria & Diagnósticos
    "telemetry": "chart",
    "telemetry_plugin": "chart",
    "telemetria": "chart",
    "diagnostics": "chart",
    "chart": "chart",

    # Histórico & Ações
    "history": "undo",
    "historico": "undo",
    "histórico": "undo",

    # Plugins & Configurações
    "plugins": "plugin",
    "plugin": "plugin",
    "settings": "settings",
    "configuracoes": "settings",
    "configurações": "settings",
    "filters": "filter",
    "filtros": "filter",
}


class SidebarButton(QtWidgets.QToolButton):
    """Botão de ícone da sidebar com suporte a SVG dinâmico e drag & drop de reordenação."""

    def __init__(
        self,
        panel_id: str,
        title: str,
        icon_path: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.panel_id = panel_id
        self.title = title or panel_id
        self._raw_icon = icon_path

        self._icon_key: Optional[str] = None
        self._disk_icon_path: Optional[str] = None

        self._resolve_icon()

        self.setCheckable(True)
        self.setFixedSize(44, 44)
        self.setToolTip(self.title)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._drag_start_pos: QtCore.QPoint | None = None
        self._last_tablet_time: float = 0.0

        self.toggled.connect(self._apply_style)
        ThemeManager.instance().themeChanged.connect(self._apply_style)
        self._apply_style()

    def _resolve_icon(self) -> None:
        """Determina o identificador SVG ou arquivo em disco para o painel."""
        # 1. Se passou um identificador SVG direto ou alias
        if self._raw_icon:
            raw_clean = str(self._raw_icon).lower().strip()
            if raw_clean in SVG_ICONS or raw_clean in ALIASES:
                self._icon_key = raw_clean
                return
            if QtCore.QFile.exists(self._raw_icon):
                self._disk_icon_path = self._raw_icon
                return

        # 2. Busca pelo ID do painel
        pid_clean = str(self.panel_id).lower().strip()
        if pid_clean in PANEL_ICON_MAP:
            self._icon_key = PANEL_ICON_MAP[pid_clean]
            return

        for k, v in PANEL_ICON_MAP.items():
            if k in pid_clean:
                self._icon_key = v
                return

        # 3. Busca por palavras no título
        title_clean = str(self.title).lower().strip()
        for word in title_clean.split():
            if word in PANEL_ICON_MAP:
                self._icon_key = PANEL_ICON_MAP[word]
                return

        for k, v in PANEL_ICON_MAP.items():
            if k in title_clean:
                self._icon_key = v
                return

        # 4. Fallback padrão: ícone genérico de ferramentas
        self._icon_key = "tools"

    def _apply_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_normal = theme.get_color("bg_panel", "#1e1e24")
        bg_hover  = theme.get_color("accent_muted", "#4f46e5")
        bg_active = theme.get_color("accent", "#6366f1")
        text_main = theme.get_color("text_main", "#f3f4f6")
        border    = theme.get_color("border", "#2e2e38")

        is_active = self.isChecked()
        fg_on_accent = theme.get_color("FG_PRIMARY", "#ffffff")
        icon_color = fg_on_accent if is_active else text_main

        # Renderiza o ícone SVG com a cor reativa ao tema e ao estado ativo
        if self._icon_key:
            icon = get_icon(self._icon_key, color=icon_color, size=QtCore.QSize(22, 22))
            if icon and not icon.isNull():
                self.setIcon(icon)
                self.setIconSize(QtCore.QSize(22, 22))
                self.setText("")
        elif self._disk_icon_path:
            self.setIcon(QtGui.QIcon(self._disk_icon_path))
            self.setIconSize(QtCore.QSize(22, 22))
            self.setText("")
        else:
            self.setText(self.title[0].upper() if self.title else "?")

        self.setStyleSheet(f"""
            QToolButton {{
                background-color: {bg_normal};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
                padding: 4px;
            }}
            QToolButton:hover {{
                background-color: {bg_hover};
                border-color: {bg_active};
            }}
            QToolButton:checked {{
                background-color: {bg_active};
                color: {fg_on_accent};
                border: 1px solid {bg_active};
            }}
        """)

    def _is_synthesized_or_recent_tablet(self, event: QtGui.QMouseEvent) -> bool:
        if event.source() == QtCore.Qt.MouseEventSource.MouseEventSynthesizedBySystem:
            return True
        return (time.monotonic() - self._last_tablet_time) < 0.25

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._is_synthesized_or_recent_tablet(event):
            event.accept()
            return
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._is_synthesized_or_recent_tablet(event):
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._is_synthesized_or_recent_tablet(event):
            event.accept()
            return
        if (
            event.buttons() & QtCore.Qt.LeftButton
            and self._drag_start_pos is not None
        ):
            delta = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if delta >= QtWidgets.QApplication.startDragDistance():
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def tabletEvent(self, event: QtGui.QTabletEvent) -> None:
        self._last_tablet_time = time.monotonic()
        et = event.type()
        if et == QtCore.QEvent.TabletPress:
            self._drag_start_pos = event.position().toPoint()
            self.setDown(True)
            event.accept()
        elif et == QtCore.QEvent.TabletMove:
            if self._drag_start_pos is not None:
                delta = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
                if delta >= QtWidgets.QApplication.startDragDistance():
                    self._start_drag()
                    event.accept()
                    return
            event.accept()
        elif et == QtCore.QEvent.TabletRelease:
            if self.isDown():
                self.setDown(False)
                self.click()
            self._drag_start_pos = None
            event.accept()
        else:
            super().tabletEvent(event)

    def _start_drag(self) -> None:
        self._drag_start_pos = None
        drag = QtGui.QDrag(self)
        mime = QtCore.QMimeData()
        mime.setData("application/x-lumenia-panel", self.panel_id.encode("utf-8"))
        drag.setMimeData(mime)

        pix = self.grab()
        drag.setPixmap(pix)
        drag.setHotSpot(pix.rect().center())
        drag.exec(QtCore.Qt.MoveAction)
