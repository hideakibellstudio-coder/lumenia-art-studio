"""
InterfaceTweaksGroup — "Ajustes Finos" do diálogo de temas.
===========================================================
Raio dos cantos, família da fonte e escala da interface: ajustes do usuário
que valem para qualquer tema. É uma view do `ThemeManager` (recebido pelo
construtor): mudar um combo chama `set_interface_tweaks`/`set_ui_scale`, e
mudança de escala vinda de fora volta para o combo.

Separado do `ThemeDialog` em 2026-09-24 (o diálogo estava na parede dos 450
linhas). Os combos de raio e fonte existiam antes sem estar ligados a nada.
"""
from __future__ import annotations

from PySide6 import QtWidgets

from ui.core.i18n import tr
from ui.core.theme.interface_tweaks import FONT_CHOICES, RADIUS_CHOICES
from ui.core.theme.manager import ThemeManager

SCALE_VALUES = (0.8, 1.0, 1.25, 1.5, 1.75, 2.0)


def _labels() -> dict[str, list[str]]:
    return {
        "radius": [
            tr("dialogs.theme_rad_default", "Padrão do Tema"),
            tr("dialogs.theme_rad_square", "Quadrado (0px)"),
            tr("dialogs.theme_rad_soft", "Suave (4px)"),
            tr("dialogs.theme_rad_rounded", "Arredondado (8px)"),
            tr("dialogs.theme_rad_capsule", "Cápsula (16px)"),
        ],
        "font": [
            tr("dialogs.theme_font_segoe", "Segoe UI (Padrão Windows)"),
            tr("dialogs.theme_font_roboto", "Roboto / System"),
            tr("dialogs.theme_font_inter", "Inter Display"),
            tr("dialogs.theme_font_helvetica", "Helvetica / Arial"),
        ],
        "scale": [
            tr("scale.80", "80% (Compacto)"),
            tr("scale.100", "100% (Padrão)"),
            tr("scale.125", "125% (Médio)"),
            tr("scale.150", "150% (Grande / HiDPI)"),
            tr("scale.175", "175% (Muito Grande)"),
            tr("scale.200", "200% (Ultra HiDPI)"),
        ],
    }


class InterfaceTweaksGroup(QtWidgets.QGroupBox):
    def __init__(self, theme: ThemeManager, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = theme
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        self.lbl_rad, self.combo_radius = self._row(layout)
        self.lbl_fnt, self.combo_font = self._row(layout)
        self.lbl_scale, self.combo_scale = self._row(layout)
        self.retranslate()
        self.combo_radius.currentIndexChanged.connect(self._on_tweak_changed)
        self.combo_font.currentIndexChanged.connect(self._on_tweak_changed)
        self.combo_scale.currentIndexChanged.connect(self._on_scale_changed)
        theme.scaleChanged.connect(self._show_state)

    @staticmethod
    def _row(layout: QtWidgets.QVBoxLayout) -> tuple[QtWidgets.QLabel, QtWidgets.QComboBox]:
        row = QtWidgets.QHBoxLayout()
        label = QtWidgets.QLabel()
        label.setStyleSheet("font-size: 12px;")
        combo = QtWidgets.QComboBox()
        row.addWidget(label)
        row.addStretch()
        row.addWidget(combo)
        layout.addLayout(row)
        return label, combo

    def retranslate(self) -> None:
        self.setTitle(tr("dialogs.theme_tweaks", "Ajustes Finos (Geometria & Tipografia)"))
        self.lbl_rad.setText(tr("dialogs.theme_radius", "Raio dos Cantos:"))
        self.lbl_fnt.setText(tr("dialogs.theme_font", "Família da Fonte:"))
        self.lbl_scale.setText(tr("dialogs.theme_scale", "Escala da Interface:"))
        labels = _labels()
        for combo, key in ((self.combo_radius, "radius"), (self.combo_font, "font"), (self.combo_scale, "scale")):
            combo.blockSignals(True)
            combo.clear()
            combo.addItems(labels[key])
            combo.blockSignals(False)
        self._show_state()

    def _show_state(self, *_args) -> None:
        """Os combos mostram o que o ThemeManager tem agora."""
        theme = self._theme
        scale_index = next((i for i, v in enumerate(SCALE_VALUES) if abs(v - theme.ui_scale) < 0.05), 1)
        for combo, index in (
            (self.combo_radius, RADIUS_CHOICES.index(theme.corner_radius)),
            (self.combo_font, FONT_CHOICES.index(theme.font_key) if theme.font_key in FONT_CHOICES else 0),
            (self.combo_scale, scale_index),
        ):
            combo.blockSignals(True)
            combo.setCurrentIndex(index)
            combo.blockSignals(False)

    def _on_tweak_changed(self, _index: int = 0) -> None:
        self._theme.set_interface_tweaks(
            RADIUS_CHOICES[max(0, self.combo_radius.currentIndex())],
            FONT_CHOICES[max(0, self.combo_font.currentIndex())],
        )

    def _on_scale_changed(self, index: int) -> None:
        if 0 <= index < len(SCALE_VALUES):
            self._theme.set_ui_scale(SCALE_VALUES[index])
