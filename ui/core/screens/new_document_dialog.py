"""
NewDocumentDialog — Diálogo de Novo Documento (Estilo ALADYN ENGINE + Temas Lumenia UI)
========================================================================================
Combina os recursos completos de presets de dimensão, opções de papel de fundo (Layer 0)
e texturas de papel do ALADYN ENGINE, 100% integrado ao sistema de temas (ThemeManager) da Lumenia UI.
"""

from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager


class NewDocumentDialog(QtWidgets.QDialog):
    PRESETS = [
        ("Quadrado Padrão (600 × 600 px)", 600, 600, 72),
        ("Full HD (1920 × 1080 px)", 1920, 1080, 72),
        ("4K UHD (3840 × 2160 px)", 3840, 2160, 72),
        ("A4 Ilustração (2480 × 3508 px - 300 DPI)", 2480, 3508, 300),
        ("Mobile Portrait (1080 × 1920 px)", 1080, 1920, 72),
        ("Customizado", 800, 800, 72),
    ]

    BACKGROUND_COLORS = [
        ("Branco Neve (#FFFFFF)", (255, 255, 255, 255)),
        ("Papel Marfim (#FDF6E3)", (253, 246, 227, 255)),
        ("Cinza Neutro (#808080)", (128, 128, 128, 255)),
        ("Preto Escuro (#1A1A1A)", (26, 26, 26, 255)),
        ("Transparente (Sem Fundo)", (0, 0, 0, 0)),
    ]

    PAPER_TEXTURES = [
        ("Nenhuma (Superfície Lisa)", 0),
        ("Papel Fino de Desenho (Fine Grain)", 1),
        ("Textura de Aquarela Algodão (Rough)", 2),
        ("Tela de Pintura (Linen Canvas)", 3),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Documento")
        self.setModal(True)
        self.setFixedSize(460, 440)

        self.setup_ui()
        self.apply_theme()
        ThemeManager.instance().themeChanged.connect(self.apply_theme)

    def setup_ui(self):
        layout_main = QtWidgets.QVBoxLayout(self)
        layout_main.setContentsMargins(16, 16, 16, 16)
        layout_main.setSpacing(12)

        # Nome do documento
        row_name = QtWidgets.QHBoxLayout()
        lbl_name = QtWidgets.QLabel("Nome do Documento:")
        lbl_name.setStyleSheet("font-weight: bold;")
        self.txt_name = QtWidgets.QLineEdit("Sem Título")
        row_name.addWidget(lbl_name)
        row_name.addWidget(self.txt_name, 1)
        layout_main.addLayout(row_name)

        # Grupo: Presets e Dimensões
        self.grp_dim = QtWidgets.QGroupBox("Dimensões do Canvas")
        lay_dim = QtWidgets.QFormLayout(self.grp_dim)
        lay_dim.setSpacing(10)

        self.cmb_preset = QtWidgets.QComboBox()
        for name, w, h, dpi in self.PRESETS:
            self.cmb_preset.addItem(name)
        self.cmb_preset.currentIndexChanged.connect(self._on_preset_changed)

        self.spn_width = QtWidgets.QSpinBox()
        self.spn_width.setRange(100, 8192)
        self.spn_width.setValue(1920)
        self.spn_width.setSuffix(" px")

        self.spn_height = QtWidgets.QSpinBox()
        self.spn_height.setRange(100, 8192)
        self.spn_height.setValue(1080)
        self.spn_height.setSuffix(" px")

        self.spn_dpi = QtWidgets.QSpinBox()
        self.spn_dpi.setRange(72, 1200)
        self.spn_dpi.setValue(72)
        self.spn_dpi.setSuffix(" DPI")

        lay_dim.addRow("Preset:", self.cmb_preset)
        lay_dim.addRow("Largura:", self.spn_width)
        lay_dim.addRow("Altura:", self.spn_height)
        lay_dim.addRow("Resolução:", self.spn_dpi)

        layout_main.addWidget(self.grp_dim)

        # Grupo: Propriedades do Papel de Fundo
        self.grp_paper = QtWidgets.QGroupBox("Papel de Fundo (Layer 0)")
        lay_paper = QtWidgets.QFormLayout(self.grp_paper)
        lay_paper.setSpacing(10)

        self.cmb_bg_color = QtWidgets.QComboBox()
        for name, color in self.BACKGROUND_COLORS:
            self.cmb_bg_color.addItem(name, color)

        self.cmb_paper_tex = QtWidgets.QComboBox()
        for name, tex_id in self.PAPER_TEXTURES:
            self.cmb_paper_tex.addItem(name, tex_id)

        lay_paper.addRow("Cor Inicial:", self.cmb_bg_color)
        lay_paper.addRow("Textura do Papel:", self.cmb_paper_tex)

        layout_main.addWidget(self.grp_paper)

        # Divisor
        self.sep = QtWidgets.QFrame()
        self.sep.setFrameShape(QtWidgets.QFrame.HLine)
        layout_main.addWidget(self.sep)

        # Botões OK / Cancelar
        lay_btns = QtWidgets.QHBoxLayout()
        lay_btns.addStretch()

        self.btn_cancel = QtWidgets.QPushButton("Cancelar")
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QtWidgets.QPushButton("Criar Documento")
        self.btn_ok.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_ok.setDefault(True)
        self.btn_ok.clicked.connect(self.accept)

        lay_btns.addWidget(self.btn_cancel)
        lay_btns.addWidget(self.btn_ok)

        layout_main.addLayout(lay_btns)

        # Define 1920x1080 como preset inicial selecionado (Full HD)
        self.cmb_preset.setCurrentIndex(1)

    def _on_preset_changed(self, idx: int):
        if 0 <= idx < len(self.PRESETS) - 1:
            _, w, h, dpi = self.PRESETS[idx]
            self.spn_width.setValue(w)
            self.spn_height.setValue(h)
            self.spn_dpi.setValue(dpi)

    def get_document_params(self):
        return {
            "name": self.txt_name.text().strip() or "Sem Título",
            "width": self.spn_width.value(),
            "height": self.spn_height.value(),
            "dpi": self.spn_dpi.value(),
            "bg_color": self.cmb_bg_color.currentData(),
            "paper_texture_id": self.cmb_paper_tex.currentData(),
        }

    def get_values(self):
        """Compatibilidade backward com chamadas antigas."""
        p = self.get_document_params()
        return p["name"], p["width"], p["height"]

    def apply_theme(self):
        tm = ThemeManager.instance()
        bg_main = tm.get_color("bg_base", "#12121a")
        bg_panel = tm.get_color("bg_panel", "#1e1e24")
        border = tm.get_color("border", "#2e2e38")
        text = tm.get_color("text_main", "#f3f4f6")
        accent = tm.get_color("accent", "#6366f1")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_main};
                color: {text};
            }}
            QGroupBox {{
                background-color: {bg_panel};
                border: 1px solid {border};
                border-radius: 8px;
                margin-top: 10px;
                padding: 12px;
                font-weight: bold;
                color: {accent};
            }}
            QLabel {{
                color: {text};
                font-size: 12px;
            }}
            QLineEdit, QComboBox, QSpinBox {{
                background-color: {bg_main};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 5px;
                color: {text};
                font-size: 12px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton#btnCancel {{
                background-color: {bg_panel};
                color: {text};
                border: 1px solid {border};
            }}
            QFrame {{
                color: {border};
            }}
        """)
