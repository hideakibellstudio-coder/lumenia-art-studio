"""
AboutDialog — Diálogo Moderno 'Sobre o Lumenia'
==============================================
Exibe a identidade visual oficial, especificações do ALADYN Engine e créditos.
"""

import os
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core import ThemeManager


class AboutDialog(QtWidgets.QDialog):
    """
    Diálogo Sobre o Lumenia com design profissional e identidade visual oficial.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o Lumenia")
        self.setFixedSize(500, 480)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
        self.icon_path = os.path.join(project_root, "assets", "images", "icon_lumenia.png")

        self._build_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(lambda _: self._apply_theme())

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(28, 28, 28, 24)
        main_layout.setSpacing(18)

        # ── Header: Logo e Nomes ────────────────────────────────────────────
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(20)

        lbl_logo = QtWidgets.QLabel()
        lbl_logo.setFixedSize(96, 96)
        lbl_logo.setScaledContents(True)
        if os.path.exists(self.icon_path):
            pix = QtGui.QPixmap(self.icon_path).scaled(
                96, 96, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            lbl_logo.setPixmap(pix)
            self.setWindowIcon(QtGui.QIcon(pix))
        header.addWidget(lbl_logo)

        v_info = QtWidgets.QVBoxLayout()
        v_info.setSpacing(4)
        v_info.setAlignment(QtCore.Qt.AlignVCenter)

        lbl_name = QtWidgets.QLabel("LUMENIA")
        lbl_name.setStyleSheet("font-size: 26px; font-weight: 800; letter-spacing: 2px; color: #ffffff;")
        
        lbl_sub = QtWidgets.QLabel("Digital Art & Paint Studio • Professional Edition")
        lbl_sub.setStyleSheet("font-size: 12px; color: #c084fc; font-weight: 600;")

        lbl_ver = QtWidgets.QLabel("Versão 2.5.0 (Build 2026.08)")
        lbl_ver.setStyleSheet("font-size: 11px; color: #a1a1aa;")

        v_info.addWidget(lbl_name)
        v_info.addWidget(lbl_sub)
        v_info.addWidget(lbl_ver)
        header.addLayout(v_info)

        main_layout.addLayout(header)

        # Divisor
        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.HLine)
        sep1.setStyleSheet("color: rgba(255,255,255,0.12);")
        main_layout.addWidget(sep1)

        # ── Cartão de Recursos / Arquitetura do Motor ───────────────────────
        card = QtWidgets.QFrame()
        card.setObjectName("InfoCard")
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(10)

        specs = [
            ("⚡ Motor Gráfico:", "ALADYN Native Core (C++17 / SIMD / TileGrid 64×64)"),
            ("🎨 Gerenciador de Cor:", "Display P3, Adobe RGB, sRGB & Prova de Cores CMYK"),
            ("🖌️ Motores de Pincel:", "Catmull-Rom Spline, Óleo/Impasto, Aquarela e Inker"),
            ("📐 Suíte de Seleções:", "Varinha Mágica, Retangular, Elíptica e Laço Poligonal"),
            ("🔄 Transformação:", "Livre com Pivô Móvel, 8 Alças & Interpolação Bicúbica"),
        ]

        for title, desc in specs:
            row = QtWidgets.QHBoxLayout()
            lbl_t = QtWidgets.QLabel(title)
            lbl_t.setStyleSheet("font-size: 11px; font-weight: 700; color: #e4e4e7; min-width: 135px;")
            lbl_d = QtWidgets.QLabel(desc)
            lbl_d.setStyleSheet("font-size: 11px; color: #a1a1aa;")
            lbl_d.setWordWrap(True)
            row.addWidget(lbl_t)
            row.addWidget(lbl_d, 1)
            card_lay.addLayout(row)

        main_layout.addWidget(card)

        main_layout.addStretch()

        # ── Botão Fechar ────────────────────────────────────────────────────
        bottom_lay = QtWidgets.QHBoxLayout()
        lbl_copy = QtWidgets.QLabel("© 2026 Lumenia Team. Todos os direitos reservados.")
        lbl_copy.setStyleSheet("font-size: 10px; color: #71717a;")
        bottom_lay.addWidget(lbl_copy)
        bottom_lay.addStretch()

        btn_close = QtWidgets.QPushButton("OK")
        btn_close.setFixedWidth(80)
        btn_close.setFixedHeight(28)
        btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        bottom_lay.addWidget(btn_close)

        main_layout.addLayout(bottom_lay)

    def _apply_theme(self):
        theme = ThemeManager.instance()
        bg_panel = theme.get_color("bg_panel") or "#181524"
        bg_card = theme.get_color("bg_card") or "#221c33"
        border = theme.get_color("border") or "#342c4c"
        text_main = theme.get_color("text_main") or "#ffffff"
        accent = theme.get_color("accent") or "#9333ea"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_panel};
                color: {text_main};
            }}
            #InfoCard {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                font-weight: 600;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: #a855f7;
            }}
        """)
