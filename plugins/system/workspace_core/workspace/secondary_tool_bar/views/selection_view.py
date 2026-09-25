"""Seleção retangular, elíptica e laço: suavização da borda, anti-alias e modo de combinação.

As três ferramentas têm opções separadas no ToolState ("rect_select",
"ellipse_select", "lasso"); cada uma tem a sua view. Até 2026-09-24 retângulo
e elipse dividiam um painel que decidia para quem publicar olhando
`getattr(self, "_active_tool_id", "")`.
"""
from __future__ import annotations

from PySide6 import QtWidgets

from ui.infrastructure.i18n import tr

from .base import (
    OrientedOptionsView, Text, add_slider, combo, header_row, icon_label, set_checked, set_combo_items,
    set_value, slider, toggle, value_label,
)
from .fill_views import deselect_button, selection_modes

_SELECTION = Text("secondary_bar.selection_title", "SELEÇÃO")
_LOOK = {
    "rect_select": ("select_rect", _SELECTION),
    "ellipse_select": ("select_ellipse", _SELECTION),
    "lasso": ("lasso", Text("secondary_bar.lasso_title", "LAÇO DE SELEÇÃO")),
}


class SelectionOptionsView(OrientedOptionsView):
    def __init__(self, tool_state, key: str, orientation, parent=None):
        super().__init__(tool_state, key, orientation, parent)

    def build(self, layout):
        v = self.vertical
        icon, title = _LOOK[self.key]
        if v:
            layout.addLayout(header_row(self, icon, title)[0])
        else:
            layout.addWidget(icon_label(icon))
        self.slider_feather = slider(0, 50, None if v else 50)
        self.lbl_feather_val = value_label("0px")
        add_slider(self, Text("secondary_bar.feather", "Suavização:"), self.slider_feather, self.lbl_feather_val)

        self.btn_aa = toggle()
        self.cbo_mode = combo()
        self.btn_deselect = deselect_button(self)
        if v:
            row = QtWidgets.QHBoxLayout()
            row.addWidget(self.btn_aa)
            row.addWidget(self.btn_deselect)
            layout.addLayout(row)
            layout.addWidget(self.cbo_mode)
        else:
            layout.addWidget(self.btn_aa)
            layout.addWidget(self.cbo_mode)
            layout.addWidget(self.btn_deselect)

        self.slider_feather.valueChanged.connect(lambda x: self.publish(feather_px=x))
        self.btn_aa.toggled.connect(lambda x: self.publish(aa=x))
        self.cbo_mode.currentIndexChanged.connect(lambda i: self.publish(mode=i))

    def show_options(self, o):
        set_value(self.slider_feather, o["feather_px"])
        self.lbl_feather_val.setText(f"{o['feather_px']}px")
        set_checked(self.btn_aa, o["aa"])
        self.cbo_mode.setCurrentIndex(o["mode"])

    def retranslate_ui(self):
        self.btn_aa.setText(tr("selection.anti_alias", "Anti-Alias"))
        set_combo_items(self.cbo_mode, selection_modes())
        self.btn_deselect.setText(f" {tr('selection.deselect', 'Desmarcar')}")
