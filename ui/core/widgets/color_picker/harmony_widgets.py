"""Faixa de harmonias do painel de cores: escolha da regra + amostras clicáveis."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.config.manager import ConfigManager
from ui.core.i18n import I18nManager, tr
from ui.core.theme.manager import ThemeManager

from .harmony import HarmonyRule, harmony_colors, harmony_hues

_ROTULOS = {
    HarmonyRule.NONE: ("color.harmony_none", "Nenhuma"),
    HarmonyRule.COMPLEMENTARY: ("color.harmony_complementary", "Complementar"),
    HarmonyRule.ANALOGOUS: ("color.harmony_analogous", "Análogas"),
    HarmonyRule.TRIADIC: ("color.harmony_triadic", "Tríade"),
    HarmonyRule.SPLIT_COMPLEMENTARY: ("color.harmony_split_complementary", "Complementar dividida"),
    HarmonyRule.SQUARE: ("color.harmony_square", "Quadrado"),
}
_MAX_AMOSTRAS = 3


class HarmonyStrip(QtWidgets.QWidget):
    """Regra de harmonia (lembrada entre sessões) e as cores parceiras."""

    colorSelected = QtCore.Signal(QtGui.QColor)
    ruleChanged = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._hsv = (0.0, 1.0, 1.0)
        self._cores: list[QtGui.QColor] = []

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.lbl = QtWidgets.QLabel()
        self.lbl.setProperty("muted", "true")
        layout.addWidget(self.lbl)
        self.combo = QtWidgets.QComboBox()
        self.combo.setFixedHeight(22)
        for regra in HarmonyRule:
            self.combo.addItem("", str(regra))
        self.set_rule(HarmonyRule.coerce(ConfigManager.instance().get("color", "harmony", str(HarmonyRule.NONE))))
        self.combo.currentIndexChanged.connect(self._on_regra)
        layout.addWidget(self.combo, 1)

        self.amostras: list[QtWidgets.QPushButton] = []
        for i in range(_MAX_AMOSTRAS):
            btn = QtWidgets.QPushButton(self)
            btn.setFixedSize(22, 22)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.clicked.connect(self._on_amostra)
            btn.setProperty("indice", i)
            layout.addWidget(btn)
            self.amostras.append(btn)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        ThemeManager.instance().themeChanged.connect(self._atualizar_amostras)
        self.retranslate_ui()
        self._atualizar_amostras()

    def rule(self) -> HarmonyRule:
        return HarmonyRule.coerce(self.combo.currentData())

    def set_rule(self, rule: HarmonyRule) -> None:
        self.combo.setCurrentIndex(max(0, self.combo.findData(str(rule))))

    def hues(self) -> list[float]:
        return harmony_hues(self.rule(), self._hsv[0])

    def colors(self) -> list[QtGui.QColor]:
        return list(self._cores)

    def set_base(self, hue: float, saturation: float, value: float) -> None:
        self._hsv = (hue, saturation, value)
        self._atualizar_amostras()

    def retranslate_ui(self, *_args) -> None:
        self.lbl.setText(tr("color.harmony_label", "Harmonia"))
        for i in range(self.combo.count()):
            chave, padrao = _ROTULOS[HarmonyRule.coerce(self.combo.itemData(i))]
            self.combo.setItemText(i, tr(chave, padrao))

    def _on_regra(self, _idx: int) -> None:
        ConfigManager.instance().set("color", "harmony", str(self.rule()))
        self._atualizar_amostras()
        self.ruleChanged.emit()

    def _on_amostra(self) -> None:
        i = int(self.sender().property("indice"))
        if i < len(self._cores):
            self.colorSelected.emit(QtGui.QColor(self._cores[i]))

    def _atualizar_amostras(self, *_args) -> None:
        self._cores = harmony_colors(self.rule(), *self._hsv)
        borda = ThemeManager.instance().get_color("border")
        for i, btn in enumerate(self.amostras):
            if i < len(self._cores):
                cor = self._cores[i]
                btn.setStyleSheet(f"background-color: {cor.name()}; border: 1px solid {borda}; border-radius: 4px;")
                btn.setToolTip(cor.name().upper())
                btn.show()
            else:
                btn.hide()
