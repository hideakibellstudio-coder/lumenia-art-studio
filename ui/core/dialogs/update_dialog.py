"""`UpdateDialog`: a new version was found; install it now, when closing, or later.

Shows the version and its release notes.
"""

from __future__ import annotations

from enum import Enum

from PySide6 import QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.updates import UpdateOffer
from ui.infrastructure.i18n import tr


class UpdateChoice(Enum):
    RESTART_NOW = "restart_now"
    ON_EXIT = "on_exit"
    LATER = "later"


class UpdateDialog(BaseFramelessDialog):
    def __init__(self, offer: UpdateOffer, current_version: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(title=tr("distribution.update.title", "Atualização do Lumenia"), icon_name="info",
                         parent=parent, modal=True)
        self.choice = UpdateChoice.LATER
        self.resize(560, 420)
        head = QtWidgets.QLabel(tr("distribution.update.available", "Versão {new} disponível (você usa a {old}).",
                                   new=offer.version, old=current_version or "?"))
        head.setProperty("heading", "true")
        head.setWordWrap(True)
        self.content_layout.addWidget(head)

        lbl_delta = QtWidgets.QLabel(tr("distribution.update.delta", "Só as partes que mudaram serão baixadas."))
        lbl_delta.setWordWrap(True)
        lbl_delta.setProperty("muted", "true")
        self.content_layout.addWidget(lbl_delta)

        notes = QtWidgets.QTextBrowser()
        notes.setMarkdown(offer.readable_notes or tr("distribution.update.no_notes", "Sem notas de versão."))
        self.content_layout.addWidget(notes, 1)

        buttons = QtWidgets.QHBoxLayout()
        btn_later = QtWidgets.QPushButton(tr("distribution.update.later", "Depois"))
        btn_later.clicked.connect(lambda: self._finish(UpdateChoice.LATER))
        buttons.addStretch(1)
        buttons.addWidget(btn_later)
        btn_exit = QtWidgets.QPushButton(tr("distribution.update.on_exit", "Instalar ao fechar"))
        btn_exit.clicked.connect(lambda: self._finish(UpdateChoice.ON_EXIT))
        btn_now = QtWidgets.QPushButton(tr("distribution.update.restart_now", "Atualizar e reiniciar"))
        btn_now.setDefault(True)
        btn_now.clicked.connect(lambda: self._finish(UpdateChoice.RESTART_NOW))
        buttons.addWidget(btn_exit)
        buttons.addWidget(btn_now)
        self.content_layout.addLayout(buttons)

    def _finish(self, choice: UpdateChoice) -> None:
        self.choice = choice
        self.accept()
