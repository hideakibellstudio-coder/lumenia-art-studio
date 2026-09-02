"""Components for RenderSettingsDialog (ProofingPreviewBar, ProfileCard)."""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class ProofingPreviewBar(QtWidgets.QWidget):
    """Renderiza uma barra de degradê espectral comparativa simulando o perfil ativo em tempo real."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self._profile_id = 0

    def set_profile(self, profile_id: int):
        self._profile_id = profile_id
        self.update()

    def paintEvent(self, event):
        from ui.core.engine.color_profile import ColorProfileEngine

        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        w, h = rect.width(), rect.height()

        if w <= 0 or h <= 0:
            return

        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        p.setClipPath(path)

        grad = QtGui.QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.00, QtGui.QColor("#ff0000"))
        grad.setColorAt(0.17, QtGui.QColor("#ffff00"))
        grad.setColorAt(0.33, QtGui.QColor("#00ff00"))
        grad.setColorAt(0.50, QtGui.QColor("#00ffff"))
        grad.setColorAt(0.67, QtGui.QColor("#0000ff"))
        grad.setColorAt(0.83, QtGui.QColor("#ff00ff"))
        grad.setColorAt(1.00, QtGui.QColor("#ffffff"))

        img = QtGui.QImage(w, h, QtGui.QImage.Format_RGBA8888)
        img_painter = QtGui.QPainter(img)
        img_painter.fillRect(0, 0, w, h, QtGui.QBrush(grad))
        img_painter.end()

        if self._profile_id != 0:
            img = ColorProfileEngine.transform_qimage(img, self._profile_id)

        p.drawImage(0, 0, img)
        p.setClipping(False)

        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 30), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect, 6, 6)
        p.end()


class ProfileCard(QtWidgets.QFrame):
    """Cartão individual representando um perfil de cor na lista."""

    selected = QtCore.Signal(dict)

    def __init__(self, profile_data: dict, is_selected: bool = False, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.profile_data = profile_data
        self.is_selected = is_selected
        self.is_active = is_active
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_style)
        self.update_style()

    def _get_category_icon_name(self, cat: str) -> str:
        if "Digital" in cat:
            return "display"
        elif "Impressão" in cat:
            return "printer"
        elif "Acessibilidade" in cat:
            return "eye"
        return "color_wheel"

    def _build_ui(self):
        self.setFixedHeight(64)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        cat = self.profile_data.get("category", "")
        self.icon_btn = QtWidgets.QToolButton()
        self.icon_btn.setFixedSize(32, 32)
        self.icon_btn.setIconSize(QtCore.QSize(18, 18))
        self.icon_btn.setIcon(get_icon(self._get_category_icon_name(cat)))
        self.icon_btn.setStyleSheet("border: none; background-color: rgba(255,255,255,0.06); border-radius: 6px;")
        layout.addWidget(self.icon_btn)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setAlignment(QtCore.Qt.AlignVCenter)

        self.name_label = QtWidgets.QLabel(self.profile_data.get("name", "Perfil"))
        self.name_label.setProperty("heading", "true")

        self.cat_label = QtWidgets.QLabel(f"{cat}")
        self.cat_label.setProperty("muted", "true")

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.cat_label)
        layout.addLayout(text_layout)
        layout.addStretch()

        from ui.core.i18n import tr, I18nManager
        badge_text = tr("render.badge_active", "ATIVO") if self.is_active else ""
        self.badge_label = QtWidgets.QLabel(badge_text)
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 2px 6px; border-radius: 4px;" if self.is_active else "color: transparent;"
        )
        layout.addWidget(self.badge_label)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def set_active_state(self, is_active: bool):
        from ui.core.i18n import tr
        self.is_active = is_active
        badge_text = tr("render.badge_active", "ATIVO") if is_active else ""
        self.badge_label.setText(badge_text)
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 2px 6px; border-radius: 4px;" if is_active else "color: transparent;"
        )

    def retranslate_ui(self):
        from ui.core.i18n import tr
        if hasattr(self, "badge_label") and self.is_active:
            self.badge_label.setText(tr("render.badge_active", "ATIVO"))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.profile_data)

    def update_style(self, *args):
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_card_hover") if self.is_selected else tm.get_color("bg_card")
        border = tm.get_color("accent") if self.is_selected else tm.get_color("border")
        text_color = tm.get_color("text_main")
        text_sec = tm.get_color("text_sec")

        self.setStyleSheet(f"""
            ProfileCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
        if hasattr(self, "cat_label"):
            self.cat_label.setStyleSheet(f"color: {text_sec}; font-size: 11px;")
