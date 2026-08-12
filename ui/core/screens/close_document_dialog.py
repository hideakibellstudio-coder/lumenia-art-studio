from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager

class CloseDocumentDialog(QtWidgets.QDialog):
    SAVE = 1
    DISCARD = 2
    CANCEL = 3

    def __init__(self, doc_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Fechar Documento")
        self.setModal(True)
        self.setFixedSize(380, 160)
        self._doc_name = doc_name
        self.result_code = self.CANCEL
        
        self.setup_ui()
        self.apply_theme()
        
    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Message label
        lbl_msg = QtWidgets.QLabel(f"Deseja salvar as alterações do documento\n\"{self._doc_name}\" antes de fechar?")
        lbl_msg.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        lbl_msg.setStyleSheet("font-size: 12px; font-weight: 500; line-height: 1.4;")
        layout.addWidget(lbl_msg)
        
        # Separator line
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setStyleSheet("background-color: @BORDER;")
        layout.addWidget(sep)
        
        # Buttons layout
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.setSpacing(8)
        
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
        
        layout.addLayout(btn_layout)
        
    def _on_save(self):
        self.result_code = self.SAVE
        self.accept()
        
    def _on_discard(self):
        self.result_code = self.DISCARD
        self.accept()
        
    def _on_cancel(self):
        self.result_code = self.CANCEL
        self.reject()
        
    def apply_theme(self):
        qss = """
            QDialog {
                background-color: @BG_DARK;
            }
            QLabel {
                color: @FG_PRIMARY;
            }
            QPushButton {
                padding: 6px 16px;
                border: 1px solid @BORDER;
                border-radius: 4px;
                background-color: @BG_DARKER;
                color: @FG_PRIMARY;
                font-size: 11px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: @BG_MID;
                border-color: @ACCENT;
            }
            QPushButton#SaveBtn {
                background-color: @ACCENT;
                border-color: @ACCENT;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton#SaveBtn:hover {
                background-color: @ACCENT_HOVER;
            }
        """
        self.setStyleSheet(ThemeManager.instance().compile_qss(qss))
