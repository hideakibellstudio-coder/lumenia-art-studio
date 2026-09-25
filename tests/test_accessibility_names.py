"""Nomes acessíveis (`ui/infrastructure/accessibility.py`).

Até 2026-09-25 nenhum widget tinha nome acessível: o leitor de tela anunciava
"botão" nos 106 botões só com ícone da janela principal e nada nos 85
controles deslizantes. Agora todo controle sem texto visível que tem dica usa a
dica (já traduzida) como nome, e o nome acompanha a troca de idioma.
"""
from __future__ import annotations

from PySide6 import QtWidgets

from ui.infrastructure.accessibility import name_from_tooltips


def _unnamed_with_tooltip(root):
    return [w for w in root.findChildren(QtWidgets.QWidget)
            if isinstance(w, (QtWidgets.QAbstractButton, QtWidgets.QAbstractSlider,
                              QtWidgets.QAbstractSpinBox, QtWidgets.QComboBox))
            and not (isinstance(w, QtWidgets.QAbstractButton) and w.text().strip())
            and w.toolTip().strip() and not w.accessibleName()]


def test_icon_only_button_takes_the_tooltip_as_name(qapp):
    root = QtWidgets.QWidget()
    icon = QtWidgets.QToolButton(root)
    icon.setToolTip("<b>Pincel</b> (B)")
    labeled = QtWidgets.QPushButton("Salvar", root)
    labeled.setToolTip("Salva o documento")
    manual = QtWidgets.QToolButton(root)
    manual.setToolTip("Dica")
    manual.setAccessibleName("Nome dado à mão")
    slider = QtWidgets.QSlider(root)
    slider.setToolTip("Tamanho do pincel")

    assert name_from_tooltips(root) == 2
    assert icon.accessibleName() == "Pincel (B)"
    assert slider.accessibleName() == "Tamanho do pincel"
    assert labeled.accessibleName() == "", "texto visível já é o nome"
    assert manual.accessibleName() == "Nome dado à mão"

    caption = QtWidgets.QLabel("Tolerância:", root)
    tolerance = QtWidgets.QSlider(root)
    caption.setBuddy(tolerance)
    assert name_from_tooltips(root) == 1 and tolerance.accessibleName() == "Tolerância"

    icon.setToolTip("Brush (B)")  # troca de idioma
    assert name_from_tooltips(root) == 1 and icon.accessibleName() == "Brush (B)"
    root.deleteLater()


def test_main_window_controls_with_tooltip_are_all_named(qapp):
    from tests.main_window_fixture import main_window_com_workspace

    window = main_window_com_workspace()
    window._name_controls()
    assert _unnamed_with_tooltip(window) == []
    named = [w for w in window.findChildren(QtWidgets.QWidget) if w.accessibleName()]
    assert len(named) > 50
