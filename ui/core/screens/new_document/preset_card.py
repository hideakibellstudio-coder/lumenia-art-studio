"""PresetCard — Interactive visual card representing a canvas dimension preset."""

from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.icons import get_icon


class PresetCard(QtWidgets.QFrame):
    clicked = QtCore.Signal(str, int, int, int)  # id, width, height, dpi

    def __init__(
        self,
        preset_id: str,
        name: str,
        width: int,
        height: int,
        dpi: int,
        icon_name: str = "file",
        description: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.preset_id = preset_id
        self.p_name = name
        self.p_width = width
        self.p_height = height
        self.p_dpi = dpi
        self.icon_name = icon_name
        self.description = description
        self._is_selected = False

        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(58)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_style)
        self.update_style()

    def _build_ui(self):
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        # Ícone do Preset
        self.lbl_icon = QtWidgets.QLabel()
        self.lbl_icon.setFixedSize(30, 30)
        self.lbl_icon.setAlignment(QtCore.Qt.AlignCenter)
        lay.addWidget(self.lbl_icon)

        # Textos
        v_box = QtWidgets.QVBoxLayout()
        v_box.setContentsMargins(0, 0, 0, 0)
        v_box.setSpacing(2)

        # Linha Superior: Nome + Badge DPI
        row_top = QtWidgets.QHBoxLayout()
        row_top.setSpacing(6)
        self.lbl_title = QtWidgets.QLabel(self.p_name)
        self.lbl_title.setStyleSheet("font-size: 11px; font-weight: bold;")
        row_top.addWidget(self.lbl_title)

        self.lbl_dpi_badge = QtWidgets.QLabel(f"{self.p_dpi} DPI")
        row_top.addWidget(self.lbl_dpi_badge)
        row_top.addStretch()
        v_box.addLayout(row_top)

        # Linha Inferior: Dimensões e Descrição
        dim_text = f"{self.p_width} × {self.p_height} px"
        if self.description:
            dim_text += f"  •  {self.description}"
        self.lbl_desc = QtWidgets.QLabel(dim_text)
        v_box.addWidget(self.lbl_desc)

        lay.addLayout(v_box, 1)

    @property
    def is_selected(self) -> bool:
        return self._is_selected

    def set_selected(self, selected: bool):
        if self._is_selected != selected:
            self._is_selected = selected
            self.update_style()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.preset_id, self.p_width, self.p_height, self.p_dpi)
        super().mousePressEvent(event)

    def update_style(self, *_):
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_card_hover") if self._is_selected else tm.get_color("bg_card")
        border = tm.get_color("accent") if self._is_selected else tm.get_color("border")
        border_w = "2px" if self._is_selected else "1px"
        text = tm.get_color("text_main")
        muted = tm.get_color("text_muted")
        accent = tm.get_color("accent")
        accent_bg = tm.get_color("accent_bg")

        self.setStyleSheet(f"""
            PresetCard {{
                background-color: {bg};
                border: {border_w} solid {border};
                border-radius: 6px;
            }}
            PresetCard:hover {{
                border-color: {accent};
            }}
        """)
        self.lbl_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text};")
        self.lbl_desc.setStyleSheet(f"font-size: 10px; color: {muted};")
        self.lbl_dpi_badge.setStyleSheet(f"font-size: 9px; font-weight: 600; color: {accent}; background: {accent_bg}; padding: 1px 4px; border-radius: 3px;")
        self.lbl_icon.setStyleSheet(f"background: {accent_bg}; border-radius: 6px;")

        icon = get_icon(self.icon_name, color=accent if self._is_selected else text)
        if icon and not icon.isNull():
            self.lbl_icon.setPixmap(icon.pixmap(16, 16))
