"""Conta-gotas (amostragem + cor capturada) e transformação (comandos + interpolação)."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.i18n import tr
from ui.core.icons import get_icon
from ui.core.state import BrushState
from ui.core.theme.manager import ThemeManager
from ui.core.tools import ToolCommand
from ui.core.widgets.tool_options import SAMPLE_RADII

from .base import (
    OrientedOptionsView, VALUE_LABEL_STYLE, combo, header_row, icon_label, paint_swatch, set_checked,
    set_combo_items, toggle, tool_button,
)


class EyedropOptionsView(OrientedOptionsView):
    """Também mostra a cor do pincel: é a cor que o conta-gotas capturou por último."""

    def __init__(self, tool_state, brush_state: BrushState, orientation, parent=None):
        super().__init__(tool_state, "eyedrop", orientation, parent)
        brush_state.colorChanged.connect(self._show_color)
        self._show_color(brush_state.color)

    def build(self, layout):
        v = self.vertical
        if v:
            layout.addLayout(header_row("eyedrop", "CONTA-GOTAS")[0])
        else:
            layout.addWidget(icon_label("eyedrop"))
        self.cbo_sample = combo()
        self.btn_merged = toggle()
        self.swatch = QtWidgets.QLabel()
        self.swatch.setFixedSize(20, 20)
        self.lbl_hex = QtWidgets.QLabel()
        self.lbl_hex.setStyleSheet(VALUE_LABEL_STYLE)
        layout.addWidget(self.cbo_sample)
        layout.addWidget(self.btn_merged)
        if v:
            row = QtWidgets.QHBoxLayout()
            row.addWidget(QtWidgets.QLabel("Cor:"))
            row.addWidget(self.swatch)
            row.addWidget(self.lbl_hex)
            row.addStretch()
            layout.addLayout(row)
        else:
            layout.addWidget(self.swatch)
            layout.addWidget(self.lbl_hex)

        self.cbo_sample.currentIndexChanged.connect(self._on_sample_changed)
        self.btn_merged.toggled.connect(lambda x: self.publish(sample_all=x))

    def _on_sample_changed(self, index: int) -> None:
        if 0 <= index < len(SAMPLE_RADII):
            self.publish(sample_radius=SAMPLE_RADII[index])

    def _show_color(self, color: QtGui.QColor) -> None:
        paint_swatch(self.swatch, color, border_alpha="0.3")
        self.lbl_hex.setText(color.name().upper())

    def show_options(self, o):
        self.cbo_sample.setCurrentIndex(SAMPLE_RADII.index(o["sample_radius"]))
        set_checked(self.btn_merged, o["sample_all"])

    def retranslate_ui(self):
        average = tr("tool_options.sample_3x3", "Média").split()[-1]
        set_combo_items(self.cbo_sample, [
            tr("tool_options.sample_1x1", "1x1 Ponto"),
            tr("tool_options.sample_3x3", "3x3 Média"),
            tr("tool_options.sample_5x5", "5x5 Média"),
            f"11x11 {average}",
        ])
        self.btn_merged.setText(tr("tool_options.sample_all_layers", "Todas Camadas"))


class TransformOptionsView(OrientedOptionsView):
    def __init__(self, tool_state, orientation, parent=None):
        super().__init__(tool_state, "transform", orientation, parent)

    def build(self, layout):
        v = self.vertical
        text_color = ThemeManager.instance().get_color("text_main")
        self.btn_commit = tool_button()
        self.btn_commit.setObjectName("successButton")
        self.btn_commit.setIcon(get_icon("check", text_color))
        self.btn_cancel = tool_button()
        self.btn_cancel.setIcon(get_icon("close", text_color))
        self.btn_flip_h, self.btn_flip_v, self.btn_rot_90 = tool_button(), tool_button(), tool_button()
        self.btn_aspect, self.btn_distort = toggle(), toggle()
        self.cbo_interp = combo()
        self.lbl_title = self.lbl_interp = None

        if v:
            self.lbl_title = QtWidgets.QLabel()
            self.lbl_title.setProperty("heading", "true")
            layout.addWidget(self.lbl_title)
            for row_widgets in ((self.btn_commit, self.btn_cancel), (self.btn_flip_h, self.btn_flip_v),
                                (self.btn_rot_90, self.btn_aspect, self.btn_distort)):
                row = QtWidgets.QHBoxLayout()
                for w in row_widgets:
                    row.addWidget(w)
                layout.addLayout(row)
            layout.addWidget(self.cbo_interp)
        else:
            self.lbl_interp = QtWidgets.QLabel()
            for w in (self.btn_commit, self.btn_cancel, self.btn_flip_h, self.btn_flip_v, self.btn_rot_90,
                      self.lbl_interp, self.cbo_interp, self.btn_aspect, self.btn_distort):
                layout.addWidget(w)

        commands = {
            self.btn_commit: ToolCommand.TRANSFORM_COMMIT, self.btn_cancel: ToolCommand.TRANSFORM_CANCEL,
            self.btn_flip_h: ToolCommand.TRANSFORM_FLIP_H, self.btn_flip_v: ToolCommand.TRANSFORM_FLIP_V,
            self.btn_rot_90: ToolCommand.TRANSFORM_ROTATE_90,
        }
        for button, command in commands.items():
            button.clicked.connect(lambda _=False, c=command: self.commandRequested.emit(c.value))
        self.cbo_interp.currentIndexChanged.connect(lambda i: self.publish(interp_mode=i))
        self.btn_aspect.toggled.connect(lambda x: self.publish(lock_aspect=x))
        self.btn_distort.toggled.connect(lambda x: self.publish(distort=x))

    def show_options(self, o):
        self.cbo_interp.setCurrentIndex(o["interp_mode"])
        set_checked(self.btn_aspect, o["lock_aspect"])
        set_checked(self.btn_distort, o["distort"])

    def retranslate_ui(self):
        self.btn_commit.setText(tr("common.apply", "Aplicar"))
        self.btn_commit.setToolTip(tr("tool_options.commit_text", "Confirmar"))
        self.btn_cancel.setText(tr("common.cancel", "Cancelar"))
        self.btn_cancel.setToolTip(tr("tool_options.cancel_text", "Cancelar"))
        self.btn_flip_h.setText(tr("transform.flip_h", "Espelhar H"))
        self.btn_flip_v.setText(tr("transform.flip_v", "Espelhar V"))
        self.btn_rot_90.setText(tr("transform.rotate_90", "Girar 90°"))
        # Na vertical a coluna é estreita: o rótulo curto cabe, o longo não.
        self.btn_aspect.setText("Proporção" if self.vertical else tr("transform.lock_aspect", "Travar Proporção"))
        self.btn_aspect.setToolTip(tr("tool_options.lock_aspect", "Travar Proporções"))
        self.btn_distort.setText(tr("tools.transform_distort", "Distorcer"))
        self.btn_distort.setToolTip(tr("tool_options.distort_tip", "Arraste cada canto livremente (perspectiva)"))
        if self.lbl_title is not None:
            self.lbl_title.setText(tr("transform.title", "TRANSFORMAÇÃO"))
        if self.lbl_interp is not None:
            self.lbl_interp.setText(tr("transform.interp", "Interp:"))
        set_combo_items(self.cbo_interp, [
            tr("transform.interp_nearest", "Mais Próximo"),
            tr("transform.interp_bilinear", "Bilinear"),
            tr("transform.interp_bicubic", "Bicúbica"),
        ])
