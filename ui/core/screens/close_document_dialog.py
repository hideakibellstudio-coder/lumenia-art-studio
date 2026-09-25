"""CloseDocumentDialog — Diálogo Moderno de Confirmação para Salvar/Descartar Alterações."""

from __future__ import annotations
from PySide6 import QtWidgets, QtCore
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog


class CloseDocumentDialog(BaseFramelessDialog):
    SAVE = 1
    DISCARD = 2
    CANCEL = 3

    def __init__(self, doc_name: str, parent=None):
        super().__init__(title="Fechar Documento", icon_name="trash", parent=parent, modal=True)
        self.resize(420, 190)
        self._doc_name = doc_name
        self.result_code = self.CANCEL
        
        self.setup_ui()
        self.apply_theme()
        ThemeManager.instance().themeChanged.connect(self.apply_theme)
        
    def setup_ui(self):
        # Message label
        lbl_msg = QtWidgets.QLabel(f"Deseja salvar as alterações do documento\n\"{self._doc_name}\" antes de fechar?")
        lbl_msg.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lbl_msg.setStyleSheet("font-size: 12px; font-weight: 500; line-height: 1.4;")
        self.content_layout.addWidget(lbl_msg)
        
        self.content_layout.addStretch()

        # Buttons layout
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.addStretch()
        
        self.btn_save = QtWidgets.QPushButton("Salvar")
        self.btn_save.setObjectName("SaveBtn")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save)
        
        self.btn_discard = QtWidgets.QPushButton("Não Salvar")
        self.btn_discard.setObjectName("DiscardBtn")
        self.btn_discard.clicked.connect(self._on_discard)
        
        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.setObjectName("CancelBtn")
        self.btn_cancel.clicked.connect(self._on_cancel)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_discard)
        btn_layout.addWidget(self.btn_cancel)
        
        self.content_layout.addLayout(btn_layout)
        
    def _on_save(self):
        self.result_code = self.SAVE
        self.accept()
        
    def _on_discard(self):
        self.result_code = self.DISCARD
        self.accept()
        
    def _on_cancel(self):
        self.result_code = self.CANCEL
        self.reject()
        
    def apply_theme(self, *args):
        theme = ThemeManager.instance()
        border = theme.get_color("border", "#374151")
        accent = theme.get_color("accent", "#8b5cf6")
        text_main = theme.get_color("text_main", "#f3f4f6")
        bg_btn = theme.get_color("bg_panel", "#1f2937")
        accent_hover = theme.get_color("accent_hover", "#a855f7")

        self.setStyleSheet(f"""
            QLabel {{
                color: {text_main};
            }}
            QPushButton {{
                padding: 6px 16px;
                border: 1px solid {border};
                border-radius: 6px;
                background-color: {bg_btn};
                color: {text_main};
                font-size: 11px;
                min-width: 75px;
            }}
            QPushButton:hover {{
                border-color: {accent};
            }}
            QPushButton#SaveBtn {{
                background-color: {accent};
                border-color: {accent};
                color: {text_main};
                font-weight: bold;
            }}
            QPushButton#SaveBtn:hover {{
                background-color: {accent_hover};
            }}
        """)
