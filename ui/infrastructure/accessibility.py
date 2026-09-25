"""Nomes acessíveis a partir das dicas: o que o leitor de tela anuncia.

Até 2026-09-25 nenhum widget tinha nome acessível: o leitor de tela anunciava
os botões só com ícone como "botão" e os 85 controles deslizantes da janela
principal sem nome. A dica (tooltip) já é o texto traduzido que descreve o
controle, então vira o nome dele; sem dica, vale o rótulo ligado ao controle
por `QLabel.setBuddy` (os deslizantes das barras de opções). Só onde o widget
não tem texto visível nem um nome dado à mão. Chamado pela janela principal (ao montar e a cada troca de
idioma) e pelos diálogos ao aparecerem.
"""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets

_AUTO = "lumeniaAutoAccessibleName"
_NAMED = (QtWidgets.QAbstractButton, QtWidgets.QAbstractSlider, QtWidgets.QAbstractSpinBox, QtWidgets.QComboBox)


def _plain(tooltip: str) -> str:
    return QtGui.QTextDocumentFragment.fromHtml(tooltip).toPlainText().strip() if tooltip else ""


def _needs_name(widget: QtWidgets.QWidget) -> bool:
    return not (isinstance(widget, QtWidgets.QAbstractButton) and widget.text().strip())


def _buddy_captions(root: QtWidgets.QWidget) -> dict[int, str]:
    """Texto do rótulo ligado a cada controle por `QLabel.setBuddy`."""
    captions = {}
    for label in root.findChildren(QtWidgets.QLabel):
        buddy = label.buddy()
        text = _plain(label.text()).rstrip(":").strip()
        if buddy is not None and text:
            captions[id(buddy)] = text
    return captions


def name_from_tooltips(root: QtWidgets.QWidget) -> int:
    """Dá a cada controle sem texto visível o nome da própria dica (ou, sem dica,
    do rótulo ligado a ele por `setBuddy`). Devolve quantos nomes mudaram."""
    named = 0
    captions = _buddy_captions(root)
    for widget in root.findChildren(QtWidgets.QWidget):
        if not isinstance(widget, _NAMED) or not _needs_name(widget):
            continue
        current = widget.accessibleName()
        # Nome dado à mão fica; nome que nós demos acompanha a dica (idioma).
        if current and current != widget.property(_AUTO):
            continue
        tip = _plain(widget.toolTip()) or captions.get(id(widget), "")
        if tip and tip != current:
            widget.setAccessibleName(tip)
            widget.setProperty(_AUTO, tip)
            named += 1
    return named
