"""Canvas & Image Size Dialog — Redimensionamento de Canvas e Imagem."""

from __future__ import annotations
from PySide6 import QtWidgets
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.infrastructure.i18n import tr


class CanvasSizeDialog(BaseFramelessDialog):
    """Diálogo moderno para alterar o tamanho do Canvas ou Redimensionar a Imagem."""

    def __init__(self, current_w: int, current_h: int, is_image_resize: bool = False, parent=None):
        self.is_image_resize = is_image_resize
        self.orig_w = max(1, current_w)
        self.orig_h = max(1, current_h)
        self._aspect_ratio = self.orig_w / self.orig_h

        title = tr("menu.image.image_size", "Redimensionar Imagem") if is_image_resize else tr("menu.image.canvas_size", "Tamanho do Canvas")
        icon_name = "image" if is_image_resize else "ruler"
        super().__init__(title=title, icon_name=icon_name, parent=parent, modal=True)
        self.resize(460, 440)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        from ui.infrastructure.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _build_ui(self):
        # Informações atuais
        self.curr_lbl = QtWidgets.QLabel(f"{tr('dialogs.current_dimensions', 'Dimensões Atuais')}: {self.orig_w} × {self.orig_h} px")
        self.curr_lbl.setProperty("muted", "true")
        self.content_layout.addWidget(self.curr_lbl)

        # Formulário de Novas Dimensões
        self.form_group = QtWidgets.QGroupBox(tr("dialogs.new_dimensions", "Novas Dimensões"))
        form_layout = QtWidgets.QGridLayout(self.form_group)
        form_layout.setContentsMargins(14, 14, 14, 14)
        form_layout.setSpacing(10)

        # Largura
        self.lbl_w = QtWidgets.QLabel(f"{tr('dialogs.width', 'Largura')}:")
        form_layout.addWidget(self.lbl_w, 0, 0)
        self.width_spin = QtWidgets.QSpinBox()
        self.width_spin.setRange(1, 32000)
        self.width_spin.setValue(self.orig_w)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self._on_width_changed)
        form_layout.addWidget(self.width_spin, 0, 1)

        # Altura
        self.lbl_h = QtWidgets.QLabel(f"{tr('dialogs.height', 'Altura')}:")
        form_layout.addWidget(self.lbl_h, 1, 0)
        self.height_spin = QtWidgets.QSpinBox()
        self.height_spin.setRange(1, 32000)
        self.height_spin.setValue(self.orig_h)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self._on_height_changed)
        form_layout.addWidget(self.height_spin, 1, 1)

        # Manter Proporções
        self.ratio_check = QtWidgets.QCheckBox(tr("dialogs.keep_proportions", "Manter proporções"))
        self.ratio_check.setChecked(True)
        form_layout.addWidget(self.ratio_check, 2, 0, 1, 2)

        self.content_layout.addWidget(self.form_group)

        if not self.is_image_resize:
            # Ponto de Ancoragem para Canvas
            self.anchor_group = QtWidgets.QGroupBox(tr("dialogs.anchor", "Âncora de Expansão"))
            anchor_layout = QtWidgets.QGridLayout(self.anchor_group)
            anchor_layout.setContentsMargins(14, 14, 14, 14)
            anchor_layout.setSpacing(6)

            self.anchor_buttons = []
            self.selected_anchor = (1, 1)  # Centro

            for r in range(3):
                row_btns = []
                for c in range(3):
                    btn = QtWidgets.QPushButton()
                    btn.setFixedSize(32, 32)
                    btn.setCheckable(True)
                    if (r, c) == self.selected_anchor:
                        btn.setChecked(True)
                        btn.setText("●")
                    btn.clicked.connect(lambda ch, row=r, col=c: self._select_anchor(row, col))
                    anchor_layout.addWidget(btn, r, c)
                    row_btns.append(btn)
                self.anchor_buttons.append(row_btns)

            self.content_layout.addWidget(self.anchor_group)
        else:
            # Modo de Reamostragem para Imagem
            self.resample_group = QtWidgets.QGroupBox(tr("dialogs.interpolation", "Qualidade de Interpolação"))
            resample_layout = QtWidgets.QVBoxLayout(self.resample_group)
            resample_layout.setContentsMargins(14, 14, 14, 14)
            self.resample_combo = QtWidgets.QComboBox()
            self.resample_combo.addItems([
                tr("dialogs.resample_bilinear", "Bilinear (Padrão - Equilibrado)"),
                tr("dialogs.resample_bicubic", "Bicúbico (Suave - Alta Qualidade)"),
                tr("dialogs.resample_nearest", "Nearest Neighbor (Pixel Art / Nítido)")
            ])
            resample_layout.addWidget(self.resample_combo)
            self.content_layout.addWidget(self.resample_group)

        self.content_layout.addStretch()

        # Botões de Ação
        btn_box = QtWidgets.QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.addStretch()

        self.btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel)

        self.btn_apply = QtWidgets.QPushButton(tr("dialogs.resize_btn", "Redimensionar"))
        self.btn_apply.setObjectName("accentButton")
        self.btn_apply.setDefault(True)
        self.btn_apply.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_apply)

        self.content_layout.addLayout(btn_box)

    def retranslate_ui(self) -> None:
        title = tr("menu.image.image_size", "Redimensionar Imagem") if self.is_image_resize else tr("menu.image.canvas_size", "Tamanho do Canvas")
        self.setWindowTitle(title)
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(title)

        if hasattr(self, "curr_lbl"):
            self.curr_lbl.setText(f"{tr('dialogs.current_dimensions', 'Dimensões Atuais')}: {self.orig_w} × {self.orig_h} px")
        if hasattr(self, "form_group"):
            self.form_group.setTitle(tr("dialogs.new_dimensions", "Novas Dimensões"))
        if hasattr(self, "lbl_w"):
            self.lbl_w.setText(f"{tr('dialogs.width', 'Largura')}:")
        if hasattr(self, "lbl_h"):
            self.lbl_h.setText(f"{tr('dialogs.height', 'Altura')}:")
        if hasattr(self, "ratio_check"):
            self.ratio_check.setText(tr("dialogs.keep_proportions", "Manter proporções"))

        if hasattr(self, "anchor_group"):
            self.anchor_group.setTitle(tr("dialogs.anchor", "Âncora de Expansão"))
        if hasattr(self, "resample_group"):
            self.resample_group.setTitle(tr("dialogs.interpolation", "Qualidade de Interpolação"))
        if hasattr(self, "resample_combo"):
            idx = max(0, self.resample_combo.currentIndex())
            self.resample_combo.blockSignals(True)
            self.resample_combo.clear()
            self.resample_combo.addItems([
                tr("dialogs.resample_bilinear", "Bilinear (Padrão - Equilibrado)"),
                tr("dialogs.resample_bicubic", "Bicúbico (Suave - Alta Qualidade)"),
                tr("dialogs.resample_nearest", "Nearest Neighbor (Pixel Art / Nítido)")
            ])
            self.resample_combo.setCurrentIndex(idx)
            self.resample_combo.blockSignals(False)

        if hasattr(self, "btn_cancel"):
            self.btn_cancel.setText(tr("dialogs.cancel", "Cancelar"))
        if hasattr(self, "btn_apply"):
            self.btn_apply.setText(tr("dialogs.resize_btn", "Redimensionar"))

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
            self.height_spin.setValue(max(1, int(round(new_w / self._aspect_ratio))))
            self.height_spin.blockSignals(False)

    def _on_height_changed(self, new_h: int):
        if self.ratio_check.isChecked():
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(max(1, int(round(new_h * self._aspect_ratio))))
            self.width_spin.blockSignals(False)

    def get_results(self) -> dict:
        return {
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "is_image_resize": self.is_image_resize,
            "anchor": getattr(self, "selected_anchor", (1, 1)),
            "resample_mode": getattr(self, "resample_combo", None).currentIndex() if self.is_image_resize else 0
        }

    def _apply_theme(self, *args):
        theme = ThemeManager.instance()
        bg_card = theme.get_color("bg_panel", "#1e1e24")
        border = theme.get_color("border", "#2e2e38")
        text = theme.get_color("text_main", "#ffffff")
        self.setStyleSheet(f"""
            QGroupBox {{ font-weight: bold; border: 1px solid {border}; border-radius: 6px; margin-top: 10px; padding-top: 10px; background-color: {bg_card}; }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
            QSpinBox, QComboBox {{ background-color: {theme.get_color("bg_input", "#26262e")}; color: {text}; border: 1px solid {border}; border-radius: 4px; padding: 4px 8px; }}
        """)
