"""`WelcomeDialog`: first start without a license — free mode explained, activation one click away.

Shown once (the `licensing.welcome_shown` preference), never when a license is
active. It only reports the choice; `DistributionActions` opens the license
dialog or the store.
"""

from __future__ import annotations

from enum import Enum

from PySide6 import QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.infrastructure.i18n import tr


class WelcomeChoice(Enum):
    ACTIVATE = "activate"
    BUY = "buy"
    FREE = "free"   # also closing the dialog any other way


class WelcomeDialog(BaseFramelessDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(title=tr("distribution.welcome.title", "Bem-vindo ao Lumenia"), icon_name="info",
                         parent=parent, modal=True)
        self.choice = WelcomeChoice.FREE
        self.resize(560, 300)
        heading = QtWidgets.QLabel(tr("distribution.welcome.heading", "Você está usando a versão gratuita."))
        heading.setProperty("heading", "true")
        heading.setWordWrap(True)
        self.content_layout.addWidget(heading)
        body = QtWidgets.QLabel(tr(
            "distribution.welcome.body",
            "Todas as ferramentas funcionam. A única diferença: as imagens exportadas saem com a marca "
            "d'água \"LUMENIA FREE\".\n\nSe você comprou uma licença, ative agora com a chave que recebeu "
            "por e-mail. Também dá para ativar depois, em Ajuda > Licença."))
        body.setWordWrap(True)
        body.setProperty("muted", "true")
        self.content_layout.addWidget(body)
        self.content_layout.addStretch(1)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_buy = QtWidgets.QPushButton(tr("distribution.license.buy", "Comprar uma licença"))
        self.btn_buy.clicked.connect(lambda: self._finish(WelcomeChoice.BUY))
        self.btn_free = QtWidgets.QPushButton(tr("distribution.welcome.free", "Continuar na versão gratuita"))
        self.btn_free.clicked.connect(lambda: self._finish(WelcomeChoice.FREE))
        self.btn_activate = QtWidgets.QPushButton(tr("distribution.welcome.activate", "Ativar licença"))
        self.btn_activate.setDefault(True)
        self.btn_activate.clicked.connect(lambda: self._finish(WelcomeChoice.ACTIVATE))
        buttons.addWidget(self.btn_buy)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_free)
        buttons.addWidget(self.btn_activate)
        self.content_layout.addLayout(buttons)

    def _finish(self, choice: WelcomeChoice) -> None:
        self.choice = choice
        self.accept()
