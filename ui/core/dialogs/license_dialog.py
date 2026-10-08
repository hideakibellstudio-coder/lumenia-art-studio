"""`LicenseDialog`: shows the license of this installation and takes a new one (Help > License).

A view of the `LicenseService`: it shows the status, sends a pasted key to
`activate` and reflects what the engine answered. It never judges a key itself.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.licensing import LicenseService, LicenseState, LicenseStatus
from ui.infrastructure.i18n import tr

PURCHASE_URL = "https://lumeniateam.itch.io/lumenia"


def describe(status: LicenseStatus) -> str:
    """One sentence about the license, for this dialog and the status bar."""
    if status.is_licensed:
        until = (tr("distribution.license.updates_until", "atualizações até {date}", date=status.updates_until)
                 if status.updates_until else tr("distribution.license.updates_forever", "atualizações sem prazo"))
        return tr("distribution.license.licensed_to", "Licenciado para {name} ({sku}, {until}).",
                  name=status.holder_name or status.license_id, sku=status.sku, until=until)
    messages = {
        LicenseState.UNLICENSED: tr("distribution.license.state_unlicensed",
                                    "Modo gratuito: tudo funciona; imagens exportadas saem com marca d'água."),
        LicenseState.MALFORMED: tr("distribution.license.state_malformed", "Isso não é uma chave do Lumenia."),
        LicenseState.BAD_SIGNATURE: tr("distribution.license.state_bad_signature",
                                       "Chave inválida: não foi emitida pela equipe do Lumenia."),
        LicenseState.EXPIRED: tr("distribution.license.state_expired", "Esta licença expirou em {date}.",
                                 date=status.expires_on),
        LicenseState.REVOKED: tr("distribution.license.state_revoked",
                                 "Esta licença foi revogada. Fale com lumeniateam@protonmail.com."),
        LicenseState.UPDATES_EXPIRED: tr("distribution.license.state_updates_expired",
                                         "Esta versão é posterior ao período de atualizações da licença ({date}).",
                                         date=status.updates_until),
        LicenseState.UNSUPPORTED: tr("distribution.license.state_unsupported",
                                     "Não foi possível conferir a licença nesta instalação."),
    }
    return messages.get(status.state, messages[LicenseState.UNSUPPORTED])


class LicenseDialog(BaseFramelessDialog):
    def __init__(self, service: LicenseService, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(title=tr("distribution.license.title", "Licença do Lumenia"), icon_name="info",
                         parent=parent, modal=True)
        self._service = service
        self.resize(560, 360)
        self._build_ui()
        self._show_status(service.status)
        service.statusChanged.connect(self._show_status)

    def _build_ui(self) -> None:
        self.lbl_status = QtWidgets.QLabel()
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setProperty("heading", "true")
        self.content_layout.addWidget(self.lbl_status)

        self.lbl_hint = QtWidgets.QLabel(tr("distribution.license.paste_hint",
                                            "Cole abaixo a chave que você recebeu por e-mail (começa com LUMENIA1-)."))
        self.lbl_hint.setWordWrap(True)
        self.lbl_hint.setProperty("muted", "true")
        self.content_layout.addWidget(self.lbl_hint)

        self.txt_key = QtWidgets.QPlainTextEdit()
        self.txt_key.setPlaceholderText("LUMENIA1-...")
        self.txt_key.setFixedHeight(96)
        self.content_layout.addWidget(self.txt_key)

        self.lbl_result = QtWidgets.QLabel()
        self.lbl_result.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_result)

        buttons = QtWidgets.QHBoxLayout()
        self.btn_buy = QtWidgets.QPushButton(tr("distribution.license.buy", "Comprar uma licença"))
        self.btn_buy.clicked.connect(self._open_store)
        self.btn_remove = QtWidgets.QPushButton(tr("distribution.license.remove", "Remover licença"))
        self.btn_remove.clicked.connect(self._remove)
        self.btn_activate = QtWidgets.QPushButton(tr("distribution.license.activate", "Ativar"))
        self.btn_activate.setDefault(True)
        self.btn_activate.clicked.connect(self._activate)
        self.btn_close = QtWidgets.QPushButton(tr("distribution.close", "Fechar"))
        self.btn_close.clicked.connect(self.accept)
        buttons.addWidget(self.btn_buy)
        buttons.addWidget(self.btn_remove)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_activate)
        buttons.addWidget(self.btn_close)
        self.content_layout.addLayout(buttons)

    def _show_status(self, status: LicenseStatus) -> None:
        self.lbl_status.setText(describe(status))
        self.btn_remove.setVisible(status.state is not LicenseState.UNLICENSED)
        self.btn_buy.setVisible(not status.is_licensed)

    def _activate(self) -> None:
        token = self.txt_key.toPlainText().strip()
        if not token:
            return
        status = self._service.activate(token)
        if status.is_licensed:
            self.txt_key.clear()
            self.lbl_result.setText(tr("distribution.license.activated", "Licença ativada. Obrigado por apoiar o Lumenia!"))
        else:
            self.lbl_result.setText(describe(status))

    def _remove(self) -> None:
        answer = QtWidgets.QMessageBox.question(
            self, tr("distribution.license.remove", "Remover licença"),
            tr("distribution.license.remove_confirm",
               "Remover a licença deste computador? Você pode ativá-la de novo com a mesma chave."))
        if answer == QtWidgets.QMessageBox.Yes:
            self._service.deactivate()
            self.lbl_result.clear()

    @staticmethod
    def _open_store() -> None:
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QtCore.QUrl(PURCHASE_URL))
