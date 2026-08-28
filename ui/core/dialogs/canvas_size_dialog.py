"""Canvas & Image Size Dialog — Redimensionamento de Canvas e Imagem."""

from __future__ import annotations
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class CanvasSizeDialog(QtWidgets.QDialog):
    """Diálogo moderno para alterar o tamanho do Canvas ou Redimensionar a Imagem."""

    def __init__(self, current_w: int, current_h: int, is_image_resize: bool = False, parent=None):
        super().__init__(parent)
        self.is_image_resize = is_image_resize
        self.orig_w = max(1, current_w)
        self.orig_h = max(1, current_h)
        self.aspect_ratio = self.orig_w / self.orig_h

        title = "Redimensionar Imagem (Reamostragem)" if is_image_resize else "Tamanho do Canvas (Área de Trabalho)"
        self.setWindowTitle(title)
        self.setFixedSize(440, 420)
        self.setModal(True)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Cabeçalho
        header_layout = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel()
        icon_name = "image" if self.is_image_resize else "ruler"
        icon_lbl.setPixmap(get_icon(icon_name).pixmap(24, 24))
        header_layout.addWidget(icon_lbl)

        title_lbl = QtWidgets.QLabel("Redimensionar Imagem" if self.is_image_resize else "Tamanho do Canvas")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Informações atuais
        curr_lbl = QtWidgets.QLabel(f"Dimensões Atuais: {self.orig_w} × {self.orig_h} pixels")
        curr_lbl.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(curr_lbl)

        # Formulário de Novas Dimensões
        form_group = QtWidgets.QGroupBox("Novas Dimensões")
        form_layout = QtWidgets.QGridLayout(form_group)
        form_layout.setContentsMargins(14, 14, 14, 14)
        form_layout.setSpacing(10)

        # Largura
        form_layout.addWidget(QtWidgets.QLabel("Largura:"), 0, 0)
        self.width_spin = QtWidgets.QSpinBox()
        self.width_spin.setRange(1, 32000)
        self.width_spin.setValue(self.orig_w)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self._on_width_changed)
        form_layout.addWidget(self.width_spin, 0, 1)

        # Altura
        form_layout.addWidget(QtWidgets.QLabel("Altura:"), 1, 0)
        self.height_spin = QtWidgets.QSpinBox()
        self.height_spin.setRange(1, 32000)
        self.height_spin.setValue(self.orig_h)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self._on_height_changed)
        form_layout.addWidget(self.height_spin, 1, 1)

        # Proporção
        self.ratio_check = QtWidgets.QCheckBox("Manter Proporção (Aspect Ratio)")
        self.ratio_check.setChecked(True)
        form_layout.addWidget(self.ratio_check, 2, 0, 1, 2)

        layout.addWidget(form_group)

        if not self.is_image_resize:
            # Âncora de expansão (9 posições)
            anchor_group = QtWidgets.QGroupBox("Âncora de Expansão")
            anchor_layout = QtWidgets.QGridLayout(anchor_group)
            self.anchor_buttons = []
            self.selected_anchor = (1, 1)  # Centro

            for r in range(3):
                row_btns = []
                for c in range(3):
                    btn = QtWidgets.QPushButton()
                    btn.setFixedSize(36, 28)
                    btn.setCheckable(True)
                    if (r, c) == (1, 1):
                        btn.setChecked(True)
                        btn.setText("●")
                    btn.clicked.connect(lambda _, row=r, col=c: self._select_anchor(row, col))
                    anchor_layout.addWidget(btn, r, c, QtCore.Qt.AlignCenter)
                    row_btns.append(btn)
                self.anchor_buttons.append(row_btns)
            layout.addWidget(anchor_group)
        else:
            # Modo de Reamostragem
            resample_group = QtWidgets.QGroupBox("Método de Reamostragem")
            resample_layout = QtWidgets.QVBoxLayout(resample_group)
            self.resample_combo = QtWidgets.QComboBox()
            self.resample_combo.addItems(["Bilinear Suave (Padrão)", "Bicúbico Alta Qualidade", "Vizinho Mais Próximo (Pixel Art)"])
            resample_layout.addWidget(self.resample_combo)
            layout.addWidget(resample_group)

        layout.addStretch()

        # Botões de Ação
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_apply = QtWidgets.QPushButton("Redimensionar")
        self.btn_apply.setDefault(True)
        self.btn_apply.setStyleSheet("background-color: #6366f1; color: #ffffff; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_apply)

        layout.addLayout(btn_box)

    def _select_anchor(self, row: int, col: int):
        self.selected_anchor = (row, col)
        for r in range(3):
            for c in range(3):
                btn = self.anchor_buttons[r][c]
                is_sel = (r == row and c == col)
                btn.setChecked(is_sel)
                btn.setText("●" if is_sel else "")

    def _on_width_changed(self, new_w: int):
        if self.ratio_check.isChecked():
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(max(1, int(round(new_w / self.aspect_ratio))))
            self.height_spin.blockSignals(False)

    def _on_height_changed(self, new_h: int):
        if self.ratio_check.isChecked():
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(max(1, int(round(new_h * self.aspect_ratio))))
            self.width_spin.blockSignals(False)

    def get_results(self) -> dict:
        return {
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "is_image_resize": self.is_image_resize,
            "anchor": getattr(self, "selected_anchor", (1, 1)),
            "resample_mode": getattr(self, "resample_combo", None).currentIndex() if self.is_image_resize else 0
        }

    def _apply_theme(self):
        theme = ThemeManager.instance()
        bg_card = theme.get_color("bg_panel", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        self.setStyleSheet(f"""
            QDialog {{ background-color: {theme.get_color("bg_canvas", "#121214")}; color: {text}; }}
            QGroupBox {{ font-weight: bold; border: 1px solid {border}; border-radius: 6px; margin-top: 10px; padding-top: 10px; background-color: {bg_card}; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
            QSpinBox, QComboBox {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
        """)
