"""Balde de tinta e varinha mágica: tolerância e amostragem por região de cor."""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ui.core.i18n import tr
from ui.core.tools import ToolCommand

from .base import (
    OrientedOptionsView, Text, add_slider, combo, header_row, icon_label, set_checked, set_combo_items,
    set_value, slider, toggle, tool_button, value_label,
)

TOLERANCE = Text("secondary_bar.tolerance", "Tolerância:")
TOLERANCE_SHORT = Text("secondary_bar.tolerance_short", "Tol:")


def selection_modes() -> list[str]:
    return [
        tr("selection.new", "Nova Seleção"),
        tr("selection.add", "Adicionar (+)"),
        tr("selection.subtract", "Subtrair (-)"),
        tr("selection.intersect", "Interseção"),
    ]


def deselect_button(view: OrientedOptionsView) -> QtWidgets.QToolButton:
    button = tool_button(icon="deselect")
    button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
    button.clicked.connect(lambda: view.commandRequested.emit(ToolCommand.DESELECT.value))
    return button


class BucketOptionsView(OrientedOptionsView):
    def __init__(self, tool_state, orientation, parent=None):
        super().__init__(tool_state, "bucket", orientation, parent)

    def build(self, layout):
        v = self.vertical
        if v:
            layout.addLayout(header_row(self, "bucket", Text("secondary_bar.bucket_title", "BALDE DE TINTA"))[0])
        else:
            layout.addWidget(icon_label("bucket"))
        self.slider_tol = slider(0, 100, None if v else 55)
        self.lbl_tol_val = value_label("20%")
        add_slider(self, TOLERANCE if v else TOLERANCE_SHORT, self.slider_tol, self.lbl_tol_val)
        self.slider_exp = slider(-10, 10, None if v else 45)
        self.lbl_exp_val = value_label("+1px")
        expansion = (Text("secondary_bar.expansion", "Expansão:") if v
                     else Text("secondary_bar.expansion_short", "Exp:"))
        add_slider(self, expansion, self.slider_exp, self.lbl_exp_val)

        self.btn_contig, self.btn_merged = toggle(), toggle()
        row = QtWidgets.QHBoxLayout() if v else layout
        row.addWidget(self.btn_contig)
        row.addWidget(self.btn_merged)
        if v:
            layout.addLayout(row)

        self.slider_tol.valueChanged.connect(lambda x: self.publish(tolerance=x))
        self.slider_exp.valueChanged.connect(lambda x: self.publish(expand_px=x))
        self.btn_contig.toggled.connect(lambda x: self.publish(contiguous=x))
        self.btn_merged.toggled.connect(lambda x: self.publish(sample_all=x))

    def show_options(self, o):
        set_value(self.slider_tol, o["tolerance"])
        self.lbl_tol_val.setText(f"{o['tolerance']}%")
        set_value(self.slider_exp, o["expand_px"])
        self.lbl_exp_val.setText(f"{o['expand_px']:+d}px" if o["expand_px"] else "0px")
        set_checked(self.btn_contig, o["contiguous"])
        set_checked(self.btn_merged, o["sample_all"])

    def retranslate_ui(self):
        self.btn_contig.setText(tr("tool_options.contiguous", "Contíguo"))
        self.btn_merged.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))


class WandOptionsView(OrientedOptionsView):
    def __init__(self, tool_state, orientation, parent=None):
        super().__init__(tool_state, "wand", orientation, parent)

    def build(self, layout):
        v = self.vertical
        if v:
            layout.addLayout(header_row(self, "wand", Text("secondary_bar.wand_title", "VARINHA MÁGICA"))[0])
        else:
            layout.addWidget(icon_label("wand"))
        self.slider_tol = slider(0, 100, None if v else 55)
        self.lbl_tol_val = value_label("20%")
        add_slider(self, TOLERANCE if v else TOLERANCE_SHORT, self.slider_tol, self.lbl_tol_val)

        self.btn_contig, self.btn_merged = toggle(), toggle()
        row = QtWidgets.QHBoxLayout() if v else layout
        row.addWidget(self.btn_contig)
        row.addWidget(self.btn_merged)
        if v:
            layout.addLayout(row)
        self.cbo_mode = combo()
        layout.addWidget(self.cbo_mode)
        self.btn_deselect = deselect_button(self)
        layout.addWidget(self.btn_deselect)

        self.slider_tol.valueChanged.connect(lambda x: self.publish(tolerance=x))
        self.btn_contig.toggled.connect(lambda x: self.publish(contiguous=x))
        self.btn_merged.toggled.connect(lambda x: self.publish(sample_all=x))
        self.cbo_mode.currentIndexChanged.connect(lambda i: self.publish(mode=i))

    def show_options(self, o):
        set_value(self.slider_tol, o["tolerance"])
        self.lbl_tol_val.setText(f"{o['tolerance']}%")
        set_checked(self.btn_contig, o["contiguous"])
        set_checked(self.btn_merged, o["sample_all"])
        self.cbo_mode.setCurrentIndex(o["mode"])

    def retranslate_ui(self):
        self.btn_contig.setText(tr("tool_options.contiguous", "Contíguo"))
        self.btn_merged.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))
        set_combo_items(self.cbo_mode, selection_modes())
        self.btn_deselect.setText(f" {tr('selection.deselect', 'Desmarcar')}")
