"""
Cursor Settings Dialog — Diálogo de Personalização e Preferências de Cursores.
=============================================================================
Padronizado no Design System do Lumenia V2 com seleção de formato de cursor,
comportamento durante a pintura e persistência via QSettings.
"""

from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon


class CursorSettingsDialog(QtWidgets.QDialog):
    """Diálogo para configuração do cursor de pincel e ferramentas."""

    cursorSettingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.FramelessWindowHint | QtCore.Qt.Window)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(440, 480)
        self.resize(480, 520)
        self._drag_pos = None

        self._load_settings()
        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _load_settings(self):
        settings = QtCore.QSettings("Aladyn", "Lumenia")
        self.mode = settings.value("cursor/mode", "ring_and_dot")
        self.hide_on_stroke = settings.value("cursor/hide_on_stroke", "false").lower() in ("true", "1")
        self.show_crosshair = settings.value("cursor/show_crosshair", "false").lower() in ("true", "1")
        self.ring_opacity = int(float(settings.value("cursor/ring_opacity", 0.9)) * 100)

    def _build_ui(self):
        main_lay = QtWidgets.QVBoxLayout(self)
        main_lay.setContentsMargins(10, 10, 10, 10)

        self.card = QtWidgets.QFrame(self)
        self.card.setObjectName("CursorCard")
        card_lay = QtWidgets.QVBoxLayout(self.card)
        card_lay.setContentsMargins(16, 14, 16, 16)
        card_lay.setSpacing(12)

        # ── Cabeçalho
        hdr = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel()
        icon_lbl.setPixmap(get_icon("cursor", "ACCENT", QtCore.QSize(18, 18)).pixmap(18, 18))
        hdr.addWidget(icon_lbl)

        title = QtWidgets.QLabel("CONFIGURAÇÕES DE CURSOR E PONTEIRO")
        title.setStyleSheet("font-weight: 700; font-size: 12px; letter-spacing: 0.5px;")
        hdr.addWidget(title)
        hdr.addStretch()

        btn_close = QtWidgets.QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        hdr.addWidget(btn_close)
        card_lay.addLayout(hdr)

        # ── Seção 1: Formato do Cursor do Pincel
        grp_box = QtWidgets.QGroupBox("Formato do Cursor de Pintura")
        grp_lay = QtWidgets.QVBoxLayout(grp_box)
        grp_lay.setSpacing(8)

        self.rb_ring_dot = QtWidgets.QRadioButton("◎  Anel de Contorno com Ponto Central (Padrão)")
        self.rb_ring_only = QtWidgets.QRadioButton("◯  Apenas Anel de Contorno (Círculo de Raio)")
        self.rb_dot_only = QtWidgets.QRadioButton("•   Apenas Ponto Central de Precisão")
        self.rb_crosshair = QtWidgets.QRadioButton("✛  Mira de Precisão (Crosshair)")
        self.rb_system = QtWidgets.QRadioButton("↖  Cursor Padrão do Sistema Operacional")

        self.btn_group = QtWidgets.QButtonGroup(self)
        self.btn_group.addButton(self.rb_ring_dot, 0)
        self.btn_group.addButton(self.rb_ring_only, 1)
        self.btn_group.addButton(self.rb_dot_only, 2)
        self.btn_group.addButton(self.rb_crosshair, 3)
        self.btn_group.addButton(self.rb_system, 4)

        if self.mode == "ring_only":
            self.rb_ring_only.setChecked(True)
        elif self.mode == "dot_only":
            self.rb_dot_only.setChecked(True)
        elif self.mode == "crosshair":
            self.rb_crosshair.setChecked(True)
        elif self.mode == "system":
            self.rb_system.setChecked(True)
        else:
            self.rb_ring_dot.setChecked(True)

        for rb in (self.rb_ring_dot, self.rb_ring_only, self.rb_dot_only, self.rb_crosshair, self.rb_system):
            rb.setCursor(QtCore.Qt.PointingHandCursor)
            grp_lay.addWidget(rb)

        card_lay.addWidget(grp_box)

        # ── Seção 2: Comportamento
        grp_beh = QtWidgets.QGroupBox("Comportamento e Dinâmica")
        beh_lay = QtWidgets.QVBoxLayout(grp_beh)
        beh_lay.setSpacing(8)

        self.chk_hide = QtWidgets.QCheckBox("Ocultar anel de contorno durante o traço de pintura")
        self.chk_hide.setChecked(self.hide_on_stroke)
        self.chk_hide.setCursor(QtCore.Qt.PointingHandCursor)
        beh_lay.addWidget(self.chk_hide)

        self.chk_ch = QtWidgets.QCheckBox("Exibir mira de precisão em réguas e guias de perspectiva")
        self.chk_ch.setChecked(self.show_crosshair)
        self.chk_ch.setCursor(QtCore.Qt.PointingHandCursor)
        beh_lay.addWidget(self.chk_ch)

        # Opacidade do anel
        op_row = QtWidgets.QHBoxLayout()
        self.lbl_op = QtWidgets.QLabel(f"Opacidade do Anel: {self.ring_opacity}%")
        self.slider_op = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_op.setRange(30, 100)
        self.slider_op.setValue(self.ring_opacity)
        self.slider_op.valueChanged.connect(lambda v: self.lbl_op.setText(f"Opacidade do Anel: {v}%"))
        op_row.addWidget(self.lbl_op)
        op_row.addWidget(self.slider_op, 1)
        beh_lay.addLayout(op_row)

        card_lay.addWidget(grp_beh)
        card_lay.addStretch()

        # ── Rodapé
        footer = QtWidgets.QHBoxLayout()
        btn_restore = QtWidgets.QPushButton("Restaurar Padrões")
        btn_restore.setCursor(QtCore.Qt.PointingHandCursor)
        btn_restore.clicked.connect(self._on_restore)
        footer.addWidget(btn_restore)
        footer.addStretch()

        btn_cancel = QtWidgets.QPushButton("Cancelar")
        btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        footer.addWidget(btn_cancel)

        btn_save = QtWidgets.QPushButton("Salvar e Aplicar")
        btn_save.setCursor(QtCore.Qt.PointingHandCursor)
        btn_save.clicked.connect(self._on_save)
        footer.addWidget(btn_save)

        card_lay.addLayout(footer)
        main_lay.addWidget(self.card)

    def _on_restore(self):
        self.rb_ring_dot.setChecked(True)
        self.chk_hide.setChecked(False)
        self.chk_ch.setChecked(False)
        self.slider_op.setValue(90)

    def _on_save(self):
        settings = QtCore.QSettings("Aladyn", "Lumenia")
        if self.rb_ring_only.isChecked():
            mode = "ring_only"
        elif self.rb_dot_only.isChecked():
            mode = "dot_only"
        elif self.rb_crosshair.isChecked():
            mode = "crosshair"
        elif self.rb_system.isChecked():
            mode = "system"
        else:
            mode = "ring_and_dot"

        settings.setValue("cursor/mode", mode)
        settings.setValue("cursor/hide_on_stroke", "true" if self.chk_hide.isChecked() else "false")
        settings.setValue("cursor/show_crosshair", "true" if self.chk_ch.isChecked() else "false")
        settings.setValue("cursor/ring_opacity", self.slider_op.value() / 100.0)

        cfg = {
            "mode": mode,
            "hide_on_stroke": self.chk_hide.isChecked(),
            "show_crosshair": self.chk_ch.isChecked(),
            "ring_opacity": self.slider_op.value() / 100.0
        }
        self.cursorSettingsChanged.emit(cfg)
        self.accept()

    def _apply_theme(self, *args):
        tm = ThemeManager.instance()
        bg_card = tm.get_color("bg_card", "#181825")
        bg_panel = tm.get_color("bg_panel", "#1e1e24")
        border = tm.get_color("border", "#313244")
        accent = tm.get_color("accent", "#6366f1")
        text_main = tm.get_color("text_main", "#f3f4f6")
        text_sec = tm.get_color("text_sec", "#9ca3af")

        self.card.setStyleSheet(f"""
            QFrame#CursorCard {{
                background-color: {bg_card}; border: 1px solid {border}; border-radius: 10px;
            }}
            QGroupBox {{
                font-weight: bold; font-size: 11px; color: {accent};
                border: 1px solid {border}; border-radius: 6px; margin-top: 10px; padding-top: 10px;
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; }}
            QLabel, QRadioButton, QCheckBox {{ color: {text_main}; font-size: 11px; }}
            QPushButton {{
                background-color: {bg_panel}; color: {text_main}; border: 1px solid {border};
                border-radius: 6px; padding: 6px 14px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {accent}; color: #ffffff; border-color: {accent}; }}
        """)

    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & QtCore.Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
