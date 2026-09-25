"""Texto tipográfico: fonte, tamanho, estilo, alinhamento, cor; Inserir e Cancelar.

As opções chegam ao controlador de texto do canvas pelo `CanvasToolBinding`.
Até 2026-09-24 esta barra também as mandava direto ao canvas
(`parent().canvas_widget.set_text_settings`), um segundo caminho.
"""
from __future__ import annotations

from PySide6 import QtGui, QtWidgets

from ui.infrastructure.i18n import tr
from ui.infrastructure.icons import get_icon
from ui.core.tools import ToolCommand

from .base import (
    OrientedOptionsView, Text, color_button, header_row, icon_label, paint_swatch, set_checked, set_value,
)

_ALIGNS = ("left", "center", "right")
_SIZE = Text("tool_options.size", "Tam:")
_COLOR = Text("tool_options.color", "Cor:")


def _style_button(text: str, css: str, width: int) -> QtWidgets.QToolButton:
    button = QtWidgets.QToolButton()
    button.setText(text)
    button.setStyleSheet(css)
    button.setCheckable(True)
    button.setFixedSize(width, 24)
    return button


class TextOptionsView(OrientedOptionsView):
    def __init__(self, tool_state, orientation, parent=None):
        super().__init__(tool_state, "text", orientation, parent)

    def build(self, layout):
        v = self.vertical
        self.cbo_font = QtWidgets.QFontComboBox()
        self.cbo_font.setFixedHeight(24)
        self.spin_size = QtWidgets.QSpinBox()
        self.spin_size.setRange(8, 288)
        self.spin_size.setSuffix(" pt")
        self.spin_size.setFixedSize(75, 24)
        style_w = 28 if v else 24
        self.btn_bold = _style_button("B", "font-weight: bold;", style_w)
        self.btn_italic = _style_button("I", "font-style: italic; font-weight: bold;", style_w)
        self.btn_underline = _style_button("U", "text-decoration: underline; font-weight: bold;", style_w)
        self.align_buttons = {}
        self.align_group = QtWidgets.QButtonGroup(self)  # exclusivo: um alinhamento sempre marcado
        for align in _ALIGNS:
            button = QtWidgets.QToolButton()
            button.setCheckable(True)
            button.setFixedHeight(24)
            self.align_group.addButton(button)
            self.align_buttons[align] = button
        self.btn_color = color_button(20)
        self.btn_commit = QtWidgets.QPushButton()
        self.btn_commit.setFixedHeight(24)
        self.translate(self.btn_commit.setText, Text("secondary_bar.insert_text", "Inserir Texto") if v
                       else Text("tool_options.insert_text", "Inserir"))
        self.btn_cancel = QtWidgets.QPushButton()
        if v:
            self.translate(self.btn_cancel.setText, Text("common.cancel", "Cancelar"))
            self.btn_cancel.setFixedHeight(24)
        else:
            self.btn_cancel.setIcon(get_icon("close"))
            self.btn_cancel.setFixedSize(24, 24)
            self.cbo_font.setFixedWidth(130)

        styles = (self.btn_bold, self.btn_italic, self.btn_underline)
        aligns = tuple(self.align_buttons.values())
        if v:
            layout.addLayout(header_row(self, "text", Text("secondary_bar.text_title", "TEXTO TIPOGRÁFICO"))[0])
            layout.addWidget(self.cbo_font)
            for caption, widgets in ((_SIZE, (self.spin_size,)),
                                     (Text("secondary_bar.style", "Estilo:"), styles),
                                     (Text("secondary_bar.align", "Alinhar:"), aligns),
                                     (_COLOR, (self.btn_color,))):
                row = QtWidgets.QHBoxLayout()
                row.addWidget(self.label(caption))
                row.addStretch()
                for w in widgets:
                    row.addWidget(w)
                layout.addLayout(row)
            actions = QtWidgets.QHBoxLayout()
            actions.addWidget(self.btn_cancel)
            actions.addWidget(self.btn_commit)
            layout.addLayout(actions)
        else:
            layout.addWidget(icon_label("text"))
            layout.addWidget(self.cbo_font)
            layout.addWidget(self.label(_SIZE))
            for w in (self.spin_size, *styles, *aligns, self.label(_COLOR), self.btn_color,
                      self.btn_commit, self.btn_cancel):
                layout.addWidget(w)

        self.cbo_font.currentFontChanged.connect(lambda f: self.publish(font_family=f.family()))
        self.spin_size.valueChanged.connect(lambda x: self.publish(font_size=x))
        self.btn_bold.toggled.connect(lambda x: self.publish(bold=x))
        self.btn_italic.toggled.connect(lambda x: self.publish(italic=x))
        self.btn_underline.toggled.connect(lambda x: self.publish(underline=x))
        for align, button in self.align_buttons.items():
            button.clicked.connect(lambda _=False, a=align: self.publish(align=a))
        self.btn_color.clicked.connect(self._pick_color)
        self.btn_commit.clicked.connect(lambda: self.commandRequested.emit(ToolCommand.TEXT_COMMIT.value))
        self.btn_cancel.clicked.connect(lambda: self.commandRequested.emit(ToolCommand.TEXT_CANCEL.value))

    def _pick_color(self) -> None:
        color = QtWidgets.QColorDialog.getColor(
            self.options()["color"], self, tr("secondary_bar.text_color", "Cor do Texto"),
            QtWidgets.QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self.publish(color=color)

    def show_options(self, o):
        if self.cbo_font.currentFont().family() != o["font_family"]:
            self.cbo_font.setCurrentFont(QtGui.QFont(o["font_family"]))
        set_value(self.spin_size, o["font_size"])
        set_checked(self.btn_bold, o["bold"])
        set_checked(self.btn_italic, o["italic"])
        set_checked(self.btn_underline, o["underline"])
        set_checked(self.align_buttons[o["align"]], True)
        paint_swatch(self.btn_color, o["color"])

    def retranslate_ui(self):
        self.align_buttons["left"].setText(tr("tool_options.align_left", "Esq"))
        self.align_buttons["center"].setText(tr("tool_options.align_center", "Cen"))
        self.align_buttons["right"].setText(tr("tool_options.align_right", "Dir"))
