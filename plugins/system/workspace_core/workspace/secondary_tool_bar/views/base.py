"""OrientedOptionsView — view de opções da barra secundária numa orientação.

O vínculo com o ToolState (mostrar, publicar, comandos) vem de
`ui.core.widgets.tool_options.ToolOptionsView`, a mesma base das páginas do
painel de pincel. Aqui fica só o que é da barra: a orientação (horizontal
numa linha, vertical em coluna com cabeçalho) e as fábricas dos widgets que
todas as views repetiam à mão.

A barra tem uma view por orientação para cada ferramenta; as duas não se
conhecem e ficam iguais porque mostram o mesmo estado. Até 2026-09-24 cada
handler copiava o valor da versão horizontal para a vertical
(`for sld in (getattr(self, "slider_x_h", None), getattr(self, "slider_x_v", None))`).

Textos: texto fixo (título, rótulo de slider) é declarado junto do widget
com `Text(chave, padrão)` e `view.translate`, e troca sozinho quando o idioma
muda; `retranslate_ui` fica para o que depende de estado (itens de combo,
rótulo que muda com a ferramenta). Até 2026-09-24 os títulos e rótulos
destas views eram literais em pt-BR e não mudavam com o idioma.
"""
from __future__ import annotations

from typing import Callable, NamedTuple

from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.i18n import I18nManager, tr
from ui.infrastructure.icons import get_icon
from ui.core.state import ToolState
from ui.core.widgets.tool_options import ToolOptionsView

VALUE_LABEL_STYLE = "font-size: 11px; font-weight: bold;"
_SWATCH_STYLE = "background: {color}; border-radius: 4px; border: 1px solid rgba(255,255,255,{alpha});"


class Text(NamedTuple):
    """Texto fixo traduzível: chave do locale e padrão em pt-BR."""
    key: str
    default: str


class OrientedOptionsView(ToolOptionsView):
    def __init__(self, tool_state: ToolState, key: str, orientation: QtCore.Qt.Orientation,
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(tool_state, key, parent)
        self._texts: list[tuple[Callable[[str], None], Text]] = []
        self.vertical = orientation == QtCore.Qt.Vertical
        if self.vertical:
            layout = QtWidgets.QVBoxLayout(self)
            layout.setSpacing(6)
        else:
            layout = QtWidgets.QHBoxLayout(self)
            layout.setSpacing(8)
            layout.setAlignment(QtCore.Qt.AlignVCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        self.layout_ = layout
        self.build(layout)
        self.bind()

    def build(self, layout: QtWidgets.QBoxLayout) -> None:
        raise NotImplementedError

    def translate(self, setter: Callable[[str], None], text: Text) -> None:
        """Aplica `text` agora e de novo a cada troca de idioma."""
        self._texts.append((setter, text))
        setter(tr(text.key, text.default))

    def label(self, text: Text) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel()
        self.translate(label.setText, text)
        return label

    def bind(self) -> None:
        I18nManager.instance().languageChanged.connect(self._retranslate_texts)
        super().bind()

    def _retranslate_texts(self) -> None:
        for setter, text in self._texts:
            setter(tr(text.key, text.default))


# ── Fábricas dos widgets que todas as views usam ─────────────────────────────

def icon_label(icon: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel()
    label.setFixedSize(16, 16)
    label.setPixmap(get_icon(icon).pixmap(14, 14))
    return label


def header_row(view: OrientedOptionsView, icon: str,
               title: Text) -> tuple[QtWidgets.QHBoxLayout, QtWidgets.QLabel, QtWidgets.QLabel]:
    """Cabeçalho da orientação vertical: ícone + título em destaque."""
    row = QtWidgets.QHBoxLayout()
    icon_lbl = icon_label(icon)
    title_lbl = view.label(title)
    title_lbl.setProperty("heading", "true")
    row.addWidget(icon_lbl)
    row.addWidget(title_lbl)
    row.addStretch()
    return row, icon_lbl, title_lbl


def value_label(text: str) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text)
    label.setStyleSheet(VALUE_LABEL_STYLE)
    return label


def slider(low: int, high: int, width: int | None = None) -> QtWidgets.QSlider:
    s = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    s.setRange(low, high)
    if width is not None:
        s.setFixedWidth(width)
    return s


def add_slider(view: OrientedOptionsView, caption: Text, s: QtWidgets.QSlider,
               value_lbl: QtWidgets.QLabel) -> QtWidgets.QLabel:
    """Horizontal: rótulo, slider, valor na mesma linha. Vertical: rótulo e valor, slider embaixo."""
    caption_lbl = view.label(caption)
    layout = view.layout_
    if view.vertical:
        row = QtWidgets.QHBoxLayout()
        row.addWidget(caption_lbl)
        row.addStretch()
        row.addWidget(value_lbl)
        layout.addLayout(row)
        layout.addWidget(s)
    else:
        layout.addWidget(caption_lbl)
        layout.addWidget(s)
        layout.addWidget(value_lbl)
    return caption_lbl


def toggle(text: str = "") -> QtWidgets.QToolButton:
    button = QtWidgets.QToolButton()
    button.setText(text)
    button.setCheckable(True)
    button.setFixedHeight(24)
    return button


def tool_button(text: str = "", icon: str | None = None) -> QtWidgets.QToolButton:
    button = QtWidgets.QToolButton()
    button.setText(text)
    if icon:
        button.setIcon(get_icon(icon))
    button.setFixedHeight(24)
    return button


def combo(items: list[str] | None = None) -> QtWidgets.QComboBox:
    box = QtWidgets.QComboBox()
    if items:
        box.addItems(items)
    box.setFixedHeight(24)
    return box


def color_button(size: int) -> QtWidgets.QPushButton:
    button = QtWidgets.QPushButton()
    button.setFixedSize(size, size)
    return button


def paint_swatch(widget: QtWidgets.QWidget, color: QtGui.QColor, border_alpha: str = "0.4") -> None:
    widget.setStyleSheet(_SWATCH_STYLE.format(color=color.name(), alpha=border_alpha))


def set_combo_items(box: QtWidgets.QComboBox, items: list[str]) -> None:
    """Troca os textos (tradução) sem mudar o índice nem emitir sinal."""
    index = max(0, box.currentIndex())
    with QtCore.QSignalBlocker(box):
        box.clear()
        box.addItems(items)
        box.setCurrentIndex(index)


def set_checked(button: QtWidgets.QAbstractButton, checked: bool) -> None:
    if button.isChecked() != checked:
        button.setChecked(checked)


def set_value(widget, value: int) -> None:
    if widget.value() != value:
        widget.setValue(value)
