import os
import logging
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager

logger = logging.getLogger(__name__)

class ThemePreviewSwatch(QtWidgets.QFrame):
    """Retângulo colorido inline que mostra as cores do tema."""
    def __init__(self, bg_color: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(52, 28)
        self.setStyleSheet(
            f"background-color: {bg_color};"
            f"border: 2px solid {accent_color};"
            "border-radius: 5px;"
        )

class ThemeDialog(QtWidgets.QDialog):
    """Diálogo de Aparência - seleção de tema com preview visual e auto-reversão."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações de Aparência")
        self.resize(380, 420)
        self.setModal(True)
        
        self.theme_manager = ThemeManager.instance()
        self._initial_theme = self.theme_manager.current_theme
        self._selected_theme = self._initial_theme
        
        self._radio_group = QtWidgets.QButtonGroup(self)
        self._available_themes = self.theme_manager.get_available_themes()
        
        self.setup_ui()

    def setup_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Grupo: Tema
        theme_group = QtWidgets.QGroupBox("Temas Disponíveis")
        theme_layout = QtWidgets.QVBoxLayout(theme_group)
        theme_layout.setSpacing(12)
        theme_layout.setContentsMargins(12, 20, 12, 12)
        
        # Scroll Area para permitir rolar se houver muitos temas
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        scroll_content = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(10)
        
        if not self._available_themes:
            no_theme_lbl = QtWidgets.QLabel("Nenhum tema encontrado.")
            scroll_layout.addWidget(no_theme_lbl)
        else:
            for idx, theme in enumerate(self._available_themes):
                row = self._build_theme_row(theme, idx)
                scroll_layout.addWidget(row)
                
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        theme_layout.addWidget(scroll)
        
        main_layout.addWidget(theme_group)
        
        # Nota informativa
        from ui.core.theme.manager import ThemeManager
        note = QtWidgets.QLabel(
            "A troca de tema é aplicada imediatamente para visualização rápida. "
            "Se cancelar a janela, o tema original será restaurado."
        )
        note.setStyleSheet(ThemeManager.instance().compile_qss("font-size: 11px; color: @FG_SECONDARY;"))
        note.setWordWrap(True)
        main_layout.addWidget(note)
        
        # Botões de OK / Cancelar
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_ok = QtWidgets.QPushButton("Confirmar")
        self.btn_ok.setStyleSheet(ThemeManager.instance().compile_qss(
            "font-weight: bold; background-color: @ACCENT; color: white;"
        ))
        self.btn_ok.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        
        main_layout.addLayout(btn_layout)

    def _build_theme_row(self, theme: dict, idx: int) -> QtWidgets.QWidget:
        file_key = theme["file"]
        meta = theme["metadata"]
        colors = theme["colors"]
        name = meta.get("name", file_key)
        theme_type = meta.get("type", "dark")
        
        bg_color = colors.get("bg_panel", "#1e293b" if theme_type == "dark" else "#ffffff")
        accent_color = colors.get("accent", "#3b82f6")
        
        row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(4, 4, 4, 4)
        row_layout.setSpacing(12)
        
        radio = QtWidgets.QRadioButton()
        radio.setChecked(file_key == self._selected_theme)
        radio.toggled.connect(lambda checked, k=file_key: self._on_radio_toggled(checked, k))
        self._radio_group.addButton(radio, idx)
        
        swatch = ThemePreviewSwatch(bg_color, accent_color)
        
        name_lbl = QtWidgets.QLabel(name)
        name_lbl.setStyleSheet("font-weight: 500;")
        
        type_lbl = QtWidgets.QLabel(theme_type.upper())
        type_lbl.setStyleSheet(ThemeManager.instance().compile_qss("font-size: 10px; color: @FG_SECONDARY;"))
        type_lbl.setFixedWidth(50)
        type_lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        
        row_layout.addWidget(radio)
        row_layout.addWidget(swatch)
        row_layout.addWidget(name_lbl)
        row_layout.addStretch()
        row_layout.addWidget(type_lbl)
        
        return row

    def _on_radio_toggled(self, checked: bool, file_key: str):
        if not checked:
            return
        self._selected_theme = file_key
        # Aplica o tema imediatamente para feedback visual
        self.theme_manager.apply_theme(file_key)

    def reject(self):
        # Restaura o tema original se cancelado
        if self.theme_manager.current_theme != self._initial_theme:
            self.theme_manager.apply_theme(self._initial_theme)
        super().reject()

    def accept(self):
        # Confirma e mantém o tema selecionado
        logger.info(f"ThemeDialog: Tema confirmado e fixado: {self._selected_theme}")
        super().accept()
