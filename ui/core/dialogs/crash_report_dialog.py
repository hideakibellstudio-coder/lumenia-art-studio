"""`CrashReportDialog`: asks whether a crash report may leave the machine.

Shown at start when the previous session died (or when a report is waiting).
The user sees what is in the report and chooses; "always send" turns into the
`diagnostics.consent` preference, revocable in the Help menu.
"""

from __future__ import annotations

from enum import Enum

from PySide6 import QtCore, QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.diagnostics import CrashKind, CrashReport
from ui.infrastructure.i18n import tr


class CrashReportChoice(Enum):
    SEND = "send"
    KEEP = "keep"        # do not send now; the report stays in the folder
    DISCARD = "discard"


class CrashReportDialog(BaseFramelessDialog):
    def __init__(self, report: CrashReport, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(title=tr("distribution.crash.title", "Relatório de erro"), icon_name="info",
                         parent=parent, modal=True)
        self.choice = CrashReportChoice.KEEP
        self.resize(560, 340)
        headline = {
            CrashKind.NATIVE: tr("distribution.crash.native", "O Lumenia fechou inesperadamente na última sessão."),
            CrashKind.PYTHON: tr("distribution.crash.python", "O Lumenia encontrou um erro interno."),
            CrashKind.MANUAL: tr("distribution.crash.manual", "Relatório de diagnóstico criado."),
        }[report.kind]
        lbl_head = QtWidgets.QLabel(headline)
        lbl_head.setProperty("heading", "true")
        lbl_head.setWordWrap(True)
        self.content_layout.addWidget(lbl_head)

        lbl_body = QtWidgets.QLabel(tr(
            "distribution.crash.body",
            "Enviar o relatório ajuda a corrigir o problema. Ele contém a versão ({version}), o sistema, a pilha de "
            "chamadas e o final do registro, sem seu nome de usuário, sem e-mails e sem a sua arte.",
            version=report.app_version))
        lbl_body.setWordWrap(True)
        lbl_body.setProperty("muted", "true")
        self.content_layout.addWidget(lbl_body)

        lbl_summary = QtWidgets.QLabel(report.summary)
        lbl_summary.setWordWrap(True)
        lbl_summary.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.content_layout.addWidget(lbl_summary)

        self.chk_always = QtWidgets.QCheckBox(tr("distribution.crash.always", "Enviar sempre, sem perguntar"))
        self.content_layout.addWidget(self.chk_always)

        buttons = QtWidgets.QHBoxLayout()
        btn_discard = QtWidgets.QPushButton(tr("distribution.crash.discard", "Descartar"))
        btn_discard.clicked.connect(lambda: self._finish(CrashReportChoice.DISCARD))
        btn_keep = QtWidgets.QPushButton(tr("distribution.crash.keep", "Agora não"))
        btn_keep.clicked.connect(lambda: self._finish(CrashReportChoice.KEEP))
        btn_send = QtWidgets.QPushButton(tr("distribution.crash.send", "Enviar relatório"))
        btn_send.setDefault(True)
        btn_send.clicked.connect(lambda: self._finish(CrashReportChoice.SEND))
        buttons.addWidget(btn_discard)
        buttons.addStretch(1)
        buttons.addWidget(btn_keep)
        buttons.addWidget(btn_send)
        self.content_layout.addLayout(buttons)

    @property
    def always_send(self) -> bool:
        return self.chk_always.isChecked()

    def _finish(self, choice: CrashReportChoice) -> None:
        self.choice = choice
        self.accept()
