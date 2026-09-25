"""
Timelapse Export Dialog — Diálogo de Progresso de Exportação (ARCcC).
=====================================================================
Interface visual moderna para monitoramento da compilação de vídeo/ZIP:
  - Barra de progresso com porcentagem e status detalhado em tempo real.
  - Suporte a cancelamento seguro do processo de exportação.
  - Estilização harmonizada com o tema escuro do Lumenia.
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtWidgets

from ui.infrastructure.i18n import tr
from ui.infrastructure.theme.manager import ThemeManager


class TimelapseExportDialog(QtWidgets.QDialog):
    """Diálogo modal leve com indicador de progresso para a compilação do timelapse."""

    cancel_requested = QtCore.Signal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle(tr("recording.export_title", "Exportando Timelapse"))
        self.setFixedSize(400, 150)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowContextHelpButtonHint)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.lbl_status = QtWidgets.QLabel(tr("recording.export_preparing", "Preparando para exportar..."))
        self.lbl_status.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(self.lbl_status)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.lbl_details = QtWidgets.QLabel(tr("recording.export_processing", "Processando quadros..."))
        self.lbl_details.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.lbl_details)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch()
        self.btn_cancel = QtWidgets.QPushButton(tr("common.cancel", "Cancelar"))
        self.btn_cancel.setFixedSize(80, 26)
        self.btn_cancel.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self._on_cancel_clicked)
        btn_row.addWidget(self.btn_cancel)

        layout.addLayout(btn_row)

    def _apply_theme(self) -> None:
        theme = ThemeManager.instance()
        bg = theme.get_color("bg_dark")
        fg = theme.get_color("text_main")
        fg_sec = theme.get_color("text_muted")
        border = theme.get_color("border")
        accent = theme.get_color("accent")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QLabel {{
                color: {fg};
            }}
            QProgressBar {{
                border: 1px solid {border};
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                background-color: #161b22;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 3px;
            }}
            QPushButton {{
                background-color: {border};
                color: {fg};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: {theme.get_color("accent_muted")};
            }}
        """)
        self.lbl_details.setStyleSheet(f"color: {fg_sec}; font-size: 11px;")

    def update_progress(self, percent: int, status_text: str, details_text: str) -> None:
        """Atualiza visualmente a porcentagem e os textos de status."""
        self.progress_bar.setValue(percent)
        self.lbl_status.setText(status_text)
        self.lbl_details.setText(details_text)

    def _on_cancel_clicked(self) -> None:
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText(tr("recording.export_cancelling", "Cancelando exportação..."))
        self.cancel_requested.emit()
