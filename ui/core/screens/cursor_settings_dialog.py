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

from PySide6 import QtCore, QtGui, QtWidgets
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.infrastructure.i18n import tr


def _make_cursor_preview_icon(kind: str, color: str = "#ffffff") -> QtGui.QIcon:
    size = 22
    pix = QtGui.QPixmap(size, size)
    pix.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pix)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    center = QtCore.QPointF(size / 2.0, size / 2.0)
    pen = QtGui.QPen(QtGui.QColor(color), 1.5)
    pen_dark = QtGui.QPen(QtGui.QColor(0, 0, 0, 220), 0.8)

    if kind == "ring_and_dot":
        p.setPen(pen_dark)
        p.drawEllipse(center, 7.5, 7.5)
        p.setPen(pen)
        p.drawEllipse(center, 7.0, 7.0)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(color))
        p.drawEllipse(center, 1.8, 1.8)
    elif kind == "ring_only":
        p.setPen(pen_dark)
        p.drawEllipse(center, 7.5, 7.5)
        p.setPen(pen)
        p.drawEllipse(center, 7.0, 7.0)
    elif kind == "dot_only":
        p.setPen(pen_dark)
        p.setBrush(QtGui.QColor(color))
        p.drawEllipse(center, 3.0, 3.0)
    elif kind == "crosshair":
        p.setPen(pen)
        p.drawLine(center.x() - 7.0, center.y(), center.x() + 7.0, center.y())
        p.drawLine(center.x(), center.y() - 7.0, center.x(), center.y() + 7.0)
    elif kind == "chevron":
        path = QtGui.QPainterPath()
        path.moveTo(4.0, 4.0)
        path.lineTo(16.0, 8.5)
        path.lineTo(11.0, 11.0)
        path.lineTo(8.5, 16.0)
        path.closeSubpath()
        p.setBrush(QtGui.QColor(color))
        p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 220), 1.0))
        p.drawPath(path)
    elif kind == "system":
        path = QtGui.QPainterPath()
        path.moveTo(5.0, 4.0)
        path.lineTo(5.0, 17.0)
        path.lineTo(8.5, 13.5)
        path.lineTo(13.0, 17.0)
        path.lineTo(14.5, 15.0)
        path.lineTo(10.0, 11.5)
        path.lineTo(14.0, 11.5)
        path.closeSubpath()
        p.setBrush(QtGui.QColor(color))
        p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 220), 1.0))
        p.drawPath(path)
    p.end()
    return QtGui.QIcon(pix)


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
        self.setMinimumSize(460, 520)
        self.resize(500, 560)
        self.lbl_title = self.title_bar.lbl_title

        self._load_settings()
        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        from ui.infrastructure.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def _load_settings(self):
        from ui.infrastructure.config import ConfigManager
        sec = ConfigManager.instance().get_section("cursor")
        self.mode = sec.get("mode", "ring_and_dot")
        self.orientation = sec.get("orientation", "right")
        self.show_chevron = sec.get("show_chevron", True)
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

        self.rb_ring_dot = QtWidgets.QRadioButton()
        self.rb_ring_only = QtWidgets.QRadioButton()
        self.rb_dot_only = QtWidgets.QRadioButton()
        self.rb_crosshair = QtWidgets.QRadioButton()
        self.rb_chevron = QtWidgets.QRadioButton()
        self.rb_system = QtWidgets.QRadioButton()

        self.btn_group = QtWidgets.QButtonGroup(self)
        self.btn_group.addButton(self.rb_ring_dot, 0)
        self.btn_group.addButton(self.rb_ring_only, 1)
        self.btn_group.addButton(self.rb_dot_only, 2)
        self.btn_group.addButton(self.rb_crosshair, 3)
        self.btn_group.addButton(self.rb_chevron, 4)
        self.btn_group.addButton(self.rb_system, 5)

        self._update_radio_icons()

        if self.mode == "ring_only":
            self.rb_ring_only.setChecked(True)
        elif self.mode == "dot_only":
            self.rb_dot_only.setChecked(True)
        elif self.mode == "crosshair":
            self.rb_crosshair.setChecked(True)
        elif self.mode == "chevron":
            self.rb_chevron.setChecked(True)
        elif self.mode == "system":
            self.rb_system.setChecked(True)
        else:
            self.rb_ring_dot.setChecked(True)

        for rb in (self.rb_ring_dot, self.rb_ring_only, self.rb_dot_only, self.rb_crosshair, self.rb_chevron, self.rb_system):
            rb.setCursor(QtCore.Qt.PointingHandCursor)
            rb.setIconSize(QtCore.QSize(20, 20))
            grp_lay.addWidget(rb)

        content_lay.addWidget(self.grp_box)

        # ── Seção 2: Comportamento e Dinâmica
        self.grp_beh = QtWidgets.QGroupBox(tr("dialogs.cursor_behavior_title", "Comportamento e Dinâmica"))
        beh_lay = QtWidgets.QVBoxLayout(self.grp_beh)
        beh_lay.setSpacing(8)

        self.chk_invert_orientation = QtWidgets.QCheckBox(tr("dialogs.cursor_invert_orientation", "Inverter ponta do cursor para Diagonal Esquerda (Visão Desobstruída / Canhoto)"))
        self.chk_invert_orientation.setChecked(self.orientation == "left")
        self.chk_invert_orientation.setCursor(QtCore.Qt.PointingHandCursor)
        self.chk_invert_orientation.setToolTip(tr("dialogs.cursor_invert_tooltip", "Inclina o corpo da seta para a esquerda, liberando o campo de visão da mão de desenhistas destros."))
        beh_lay.addWidget(self.chk_invert_orientation)

        self.chk_show_chevron = QtWidgets.QCheckBox(tr("dialogs.cursor_show_chevron", "Exibir ponta de precisão junto ao anel de contorno"))
        self.chk_show_chevron.setChecked(self.show_chevron)
        self.chk_show_chevron.setCursor(QtCore.Qt.PointingHandCursor)
        self.chk_show_chevron.setToolTip(tr("dialogs.cursor_show_chevron_tooltip", "Mantém a ponta chevron visível no centro do anel."))
        beh_lay.addWidget(self.chk_show_chevron)

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
        self.retranslate_ui()

    def _update_radio_icons(self) -> None:
        c = ThemeManager.instance().get_color("text_main", "#ffffff")
        self.rb_ring_dot.setIcon(_make_cursor_preview_icon("ring_and_dot", c))
        self.rb_ring_only.setIcon(_make_cursor_preview_icon("ring_only", c))
        self.rb_dot_only.setIcon(_make_cursor_preview_icon("dot_only", c))
        self.rb_crosshair.setIcon(_make_cursor_preview_icon("crosshair", c))
        self.rb_chevron.setIcon(_make_cursor_preview_icon("chevron", c))
        self.rb_system.setIcon(_make_cursor_preview_icon("system", c))

    def retranslate_ui(self) -> None:
        """Atualiza dinamicamente os textos da tela de configurações de cursor."""
        from ui.infrastructure.i18n import tr
        self.set_dialog_title(tr("dialogs.cursor_title", "Configurações de Cursor"))
        self.grp_box.setTitle(tr("dialogs.cursor_shape_title", "Formato do Cursor de Pintura"))
        self.rb_ring_dot.setText(tr("dialogs.cursor_ring_dot", "Anel de Contorno com Ponto Central (Padrão)"))
        self.rb_ring_only.setText(tr("dialogs.cursor_ring_only", "Apenas Anel de Contorno (Círculo de Raio)"))
        self.rb_dot_only.setText(tr("dialogs.cursor_dot_only", "Apenas Ponto Central de Precisão"))
        self.rb_crosshair.setText(tr("dialogs.cursor_crosshair", "Mira de Precisão (Crosshair)"))
        self.rb_chevron.setText(tr("dialogs.cursor_chevron", "Ponta Chevron de Precisão"))
        self.rb_system.setText(tr("dialogs.cursor_system", "Cursor Padrão do Sistema Operacional"))
        self.grp_beh.setTitle(tr("dialogs.cursor_behavior_title", "Comportamento e Dinâmica"))
        self.chk_invert_orientation.setText(tr("dialogs.cursor_invert_orientation", "Inverter ponta do cursor para Diagonal Esquerda (Visão Desobstruída / Canhoto)"))
        self.chk_invert_orientation.setToolTip(tr("dialogs.cursor_invert_tooltip", "Inclina o corpo da seta para a esquerda, liberando o campo de visão da mão de desenhistas destros."))
        self.chk_show_chevron.setText(tr("dialogs.cursor_show_chevron", "Exibir ponta de precisão junto ao anel de contorno"))
        self.chk_show_chevron.setToolTip(tr("dialogs.cursor_show_chevron_tooltip", "Mantém a ponta chevron visível no centro do anel."))
        self.chk_hide.setText(tr("dialogs.cursor_hide_on_stroke", "Ocultar anel de contorno durante o traço de pintura"))
        self.chk_ch.setText(tr("dialogs.cursor_show_guides_crosshair", "Exibir mira de precisão em réguas e guias de perspectiva"))
        self.lbl_op.setText(f"{tr('dialogs.cursor_ring_opacity', 'Opacidade do Anel')}: {self.slider_op.value()}%")
        self.btn_restore.setText(tr("dialogs.reset_defaults", "Restaurar Padrões"))
        self.btn_cancel.setText(tr("dialogs.cancel", "Cancelar"))
        self.btn_save.setText(tr("dialogs.save_apply", "Salvar e Aplicar"))
        self._update_radio_icons()

    def _on_restore(self):
        self.rb_ring_dot.setChecked(True)
        self.chk_invert_orientation.setChecked(False)
        self.chk_show_chevron.setChecked(True)
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
        elif self.rb_chevron.isChecked():
            mode = "chevron"
        elif self.rb_system.isChecked():
            mode = "system"
        else:
            mode = "ring_and_dot"

        cfg = {
            "mode": mode,
            "orientation": "left" if self.chk_invert_orientation.isChecked() else "right",
            "show_chevron": self.chk_show_chevron.isChecked(),
            "hide_on_stroke": self.chk_hide.isChecked(),
            "show_crosshair": self.chk_ch.isChecked(),
            "ring_opacity": self.slider_op.value() / 100.0,
        }
        from ui.infrastructure.config import ConfigManager
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
