"""
Cursor Settings Dialog — Diálogo de Personalização e Preferências de Cursores.
=============================================================================
Padronizado no Design System do Lumenia V2 com seleção de formato de cursor,
comportamento durante a pintura e persistência via QSettings.

Migrado para BaseFramelessDialog em 2026-09-18 (panorama-consistencia-visual-tema,
Achado #4): antes reimplementava manualmente header/drag/botão-fechar (com um glifo
de texto "✕" em vez de ícone SVG), divergindo estruturalmente dos outros ~20 diálogos
do app que já compartilham essa base.
"""

from PySide6 import QtCore, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.i18n import tr


class CursorSettingsDialog(BaseFramelessDialog):
    """Diálogo para configuração do cursor de pincel e ferramentas."""

    cursorSettingsChanged = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(
            title=tr("dialogs.cursor_title", "Configurações de Cursor"),
            icon_name="cursor",
            parent=parent,
            modal=True,
        )
        self.setMinimumSize(440, 480)
        self.resize(480, 520)
        self.lbl_title = self.title_bar.lbl_title  # alias p/ compat. com testes (mesmo padrão de KeyboardShortcutsDialog)

        self._load_settings()
        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _load_settings(self):
        from ui.core.config import ConfigManager
        sec = ConfigManager.instance().get_section("cursor")
        self.mode = sec.get("mode", "ring_and_dot")
        self.hide_on_stroke = sec.get("hide_on_stroke", False)
        self.show_crosshair = sec.get("show_crosshair", False)
        self.ring_opacity = int(sec.get("ring_opacity", 0.9) * 100)

    def _build_ui(self):
        content_lay = self.content_layout
        content_lay.setSpacing(12)

        # ── Seção 1: Formato do Cursor do Pincel
        self.grp_box = QtWidgets.QGroupBox(tr("dialogs.cursor_shape_title", "Formato do Cursor de Pintura"))
        grp_lay = QtWidgets.QVBoxLayout(self.grp_box)
        grp_lay.setSpacing(8)

        self.rb_ring_dot = QtWidgets.QRadioButton(f"◎  {tr('dialogs.cursor_ring_dot', 'Anel de Contorno com Ponto Central (Padrão)')}")
        self.rb_ring_only = QtWidgets.QRadioButton(f"◯  {tr('dialogs.cursor_ring_only', 'Apenas Anel de Contorno (Círculo de Raio)')}")
        self.rb_dot_only = QtWidgets.QRadioButton(f"•   {tr('dialogs.cursor_dot_only', 'Apenas Ponto Central de Precisão')}")
        self.rb_crosshair = QtWidgets.QRadioButton(f"✛  {tr('dialogs.cursor_crosshair', 'Mira de Precisão (Crosshair)')}")
        self.rb_system = QtWidgets.QRadioButton(f"↖  {tr('dialogs.cursor_system', 'Cursor Padrão do Sistema Operacional')}")

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

        content_lay.addWidget(self.grp_box)

        # ── Seção 2: Comportamento
        self.grp_beh = QtWidgets.QGroupBox(tr("dialogs.cursor_behavior_title", "Comportamento e Dinâmica"))
        beh_lay = QtWidgets.QVBoxLayout(self.grp_beh)
        beh_lay.setSpacing(8)

        self.chk_hide = QtWidgets.QCheckBox(tr("dialogs.cursor_hide_on_stroke", "Ocultar anel de contorno durante o traço de pintura"))
        self.chk_hide.setChecked(self.hide_on_stroke)
        self.chk_hide.setCursor(QtCore.Qt.PointingHandCursor)
        beh_lay.addWidget(self.chk_hide)

        self.chk_ch = QtWidgets.QCheckBox(tr("dialogs.cursor_show_guides_crosshair", "Exibir mira de precisão em réguas e guias de perspectiva"))
        self.chk_ch.setChecked(self.show_crosshair)
        self.chk_ch.setCursor(QtCore.Qt.PointingHandCursor)
        beh_lay.addWidget(self.chk_ch)

        # Opacidade do anel
        op_row = QtWidgets.QHBoxLayout()
        self.lbl_op = QtWidgets.QLabel(f"{tr('dialogs.cursor_ring_opacity', 'Opacidade do Anel')}: {self.ring_opacity}%")
        self.slider_op = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_op.setRange(30, 100)
        self.slider_op.setValue(self.ring_opacity)
        self.slider_op.valueChanged.connect(lambda v: self.lbl_op.setText(f"{tr('dialogs.cursor_ring_opacity', 'Opacidade do Anel')}: {v}%"))
        op_row.addWidget(self.lbl_op)
        op_row.addWidget(self.slider_op, 1)
        beh_lay.addLayout(op_row)

        content_lay.addWidget(self.grp_beh)
        content_lay.addStretch()

        # ── Rodapé
        footer = QtWidgets.QHBoxLayout()
        self.btn_restore = QtWidgets.QPushButton(tr("dialogs.reset_defaults", "Restaurar Padrões"))
        self.btn_restore.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_restore.clicked.connect(self._on_restore)
        footer.addWidget(self.btn_restore)
        footer.addStretch()

        self.btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)
        footer.addWidget(self.btn_cancel)

        self.btn_save = QtWidgets.QPushButton(tr("dialogs.save_apply", "Salvar e Aplicar"))
        self.btn_save.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save)
        footer.addWidget(self.btn_save)

        content_lay.addLayout(footer)

    def retranslate_ui(self) -> None:
        """Atualiza dinamicamente os textos da tela de configurações de cursor."""
        from ui.core.i18n import tr
        if hasattr(self, "grp_box"):
            self.set_dialog_title(tr("dialogs.cursor_title", "Configurações de Cursor"))
            self.grp_box.setTitle(tr("dialogs.cursor_shape_title", "Formato do Cursor de Pintura"))
            self.rb_ring_dot.setText(f"◎  {tr('dialogs.cursor_ring_dot', 'Anel de Contorno com Ponto Central (Padrão)')}")
            self.rb_ring_only.setText(f"◯  {tr('dialogs.cursor_ring_only', 'Apenas Anel de Contorno (Círculo de Raio)')}")
            self.rb_dot_only.setText(f"•   {tr('dialogs.cursor_dot_only', 'Apenas Ponto Central de Precisão')}")
            self.rb_crosshair.setText(f"✛  {tr('dialogs.cursor_crosshair', 'Mira de Precisão (Crosshair)')}")
            self.rb_system.setText(f"↖  {tr('dialogs.cursor_system', 'Cursor Padrão do Sistema Operacional')}")
            self.grp_beh.setTitle(tr("dialogs.cursor_behavior_title", "Comportamento e Dinâmica"))
            self.chk_hide.setText(tr("dialogs.cursor_hide_on_stroke", "Ocultar anel de contorno durante o traço de pintura"))
            self.chk_ch.setText(tr("dialogs.cursor_show_guides_crosshair", "Exibir mira de precisão em réguas e guias de perspectiva"))
            self.lbl_op.setText(f"{tr('dialogs.cursor_ring_opacity', 'Opacidade do Anel')}: {self.slider_op.value()}%")
            self.btn_restore.setText(tr("dialogs.reset_defaults", "Restaurar Padrões"))
            self.btn_cancel.setText(tr("dialogs.cancel", "Cancelar"))
            self.btn_save.setText(tr("dialogs.save_apply", "Salvar e Aplicar"))

    def _on_restore(self):
        self.rb_ring_dot.setChecked(True)
        self.chk_hide.setChecked(False)
        self.chk_ch.setChecked(False)
        self.slider_op.setValue(90)

    def _on_save(self):
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

        cfg = {
            "mode": mode,
            "hide_on_stroke": self.chk_hide.isChecked(),
            "show_crosshair": self.chk_ch.isChecked(),
            "ring_opacity": self.slider_op.value() / 100.0
        }
        from ui.core.config import ConfigManager
        ConfigManager.instance().set_section("cursor", cfg)
        self.cursorSettingsChanged.emit(cfg)
        self.accept()

    def _apply_theme(self, *args):
        tm = ThemeManager.instance()
        bg_panel = tm.get_color("bg_panel", "#1e1e24")
        border = tm.get_color("border", "#313244")
        accent = tm.get_color("accent", "#6366f1")
        text_main = tm.get_color("text_main", "#f3f4f6")

        self.setStyleSheet(f"""
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
            QPushButton:hover {{ background-color: {accent}; color: {text_main}; border-color: {accent}; }}
        """)
