"""PluginCard component for PluginsWindow."""
import logging

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.widgets.toggle.toggle_switch import ToggleSwitch
from ui.core.theme.manager import ThemeManager
from ui.core.plugins.metadata import PluginMetadata


class PluginCard(QtWidgets.QFrame):
    """Cartão individual representando um plugin na lista."""

    toggled = QtCore.Signal(bool)
    selected = QtCore.Signal(object)  # plugin instance

    def __init__(self, plugin, is_active: bool, is_selected: bool = False, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.is_selected = is_selected
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._build_ui(is_active)
        ThemeManager.instance().themeChanged.connect(self.update_theme_style)
        self.update_theme_style()

    def _build_ui(self, is_active: bool) -> None:
        self.setFixedHeight(84)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        # 1. Ícone
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(40, 40)
        icon = self.plugin.get_icon() if hasattr(self.plugin, "get_icon") else None
        if icon and not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(40, 40))
        else:
            self.icon_label.setPixmap(
                QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_FileIcon).pixmap(40, 40)
            )
        layout.addWidget(self.icon_label)

        # 2. Informações do Plugin
        info_layout = QtWidgets.QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(QtCore.Qt.AlignVCenter)

        from ui.core.i18n import tr, I18nManager
        is_system = False
        try:
            is_system = self.plugin.is_system_plugin()
        except Exception:
            logging.getLogger(__name__).debug("is_system_plugin() falhou.", exc_info=True)

        try:
            metadata: PluginMetadata = self.plugin.get_metadata()
            p_name = metadata.name
            p_version = metadata.version
            p_author = metadata.author
            p_desc = metadata.description
        except Exception:
            p_name = self.plugin.__class__.__name__
            p_version = "0.0.0"
            p_author = tr("plugins.unknown", "Desconhecido")
            p_desc = tr("plugins.no_description", "Sem descrição.")

        self._p_name = p_name
        self._p_version = p_version
        self._p_author = p_author
        self._p_desc = p_desc
        self._is_system = is_system

        name_text = p_name
        if is_system:
            name_text += f" {tr('plugins.system_badge', '[Sistema]')}"

        self.name_label = QtWidgets.QLabel(name_text)
        self.name_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        self.meta_label = QtWidgets.QLabel(f"v{p_version} {tr('plugins.by', 'por')} {p_author}")
        self.meta_label.setStyleSheet("font-size: 11px;")

        short_desc = p_desc.split('\n')[0]
        if len(short_desc) > 60:
            short_desc = short_desc[:60] + "..."
        self.desc_label = QtWidgets.QLabel(short_desc)
        self.desc_label.setStyleSheet("font-size: 11px;")

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.meta_label)
        info_layout.addWidget(self.desc_label)

        layout.addLayout(info_layout, 1)

        # 3. Toggle Switch
        self.switch = ToggleSwitch(parent=self)
        self.switch.setChecked(is_active)
        if is_system:
            self.switch.setEnabled(False)
            self.switch.setToolTip(tr("plugins.system_cannot_disable", "Plugins de sistema não podem ser desativados."))
        else:
            self.switch.toggled.connect(self.toggled.emit)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

        layout.addWidget(self.switch)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.plugin)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        self.update_theme_style()

    def update_theme_style(self, *args) -> None:
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        text_main = theme.get_color("text_main", "#f3f4f6")
        text_sec = theme.get_color("text_sec", "#9ca3af")
        accent = theme.get_color("accent", "#6366f1")

        bg_color = theme.get_color("bg_hover", "#2a2a32") if self.is_selected else bg_panel
        border_color = accent if self.is_selected else border

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QFrame:hover {{
                border-color: {accent};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        self.name_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {text_main};")
        self.meta_label.setStyleSheet(f"font-size: 11px; color: {text_sec};")
        self.desc_label.setStyleSheet(f"font-size: 11px; color: {text_sec};")

    def retranslate_ui(self) -> None:
        from ui.core.i18n import tr
        if hasattr(self, "name_label"):
            name_text = self._p_name
            if self._is_system:
                name_text += f" {tr('plugins.system_badge', '[Sistema]')}"
            self.name_label.setText(name_text)
        if hasattr(self, "meta_label"):
            self.meta_label.setText(f"v{self._p_version} {tr('plugins.by', 'por')} {self._p_author}")
        if hasattr(self, "switch") and self._is_system:
            self.switch.setToolTip(tr("plugins.system_cannot_disable", "Plugins de sistema não podem ser desativados."))

