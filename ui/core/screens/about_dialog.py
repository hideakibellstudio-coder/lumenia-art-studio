"""
AboutDialog — Diálogo Moderno 'Sobre o Lumenia' (ARCcC i18n).
============================================================
Exibe a identidade visual oficial, especificações do ALADYN Engine e créditos.
"""

from __future__ import annotations
import os
from PySide6 import QtWidgets, QtCore, QtGui
from ui.core.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.i18n import tr


class AboutDialog(BaseFramelessDialog):
    """Diálogo Sobre o Lumenia com design profissional e identidade visual oficial."""

    def __init__(self, parent=None):
        super().__init__(title=tr("dialogs.about_title", "Sobre o Lumenia"), icon_name="info", parent=parent, modal=True)
        self.resize(520, 500)

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(current_dir))))
        self.icon_path = os.path.join(project_root, "assets", "images", "icon_lumenia.png")

        self._build_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(lambda _: self._apply_theme())

    def _build_ui(self):
        # ── Header: Logo e Nomes ────────────────────────────────────────────
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(20)

        lbl_logo = QtWidgets.QLabel()
        lbl_logo.setFixedSize(80, 80)
        lbl_logo.setScaledContents(True)
        if os.path.exists(self.icon_path):
            pix = QtGui.QPixmap(self.icon_path).scaled(
                80, 80, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
            )
            lbl_logo.setPixmap(pix)
            self.setWindowIcon(QtGui.QIcon(pix))
        header.addWidget(lbl_logo)

        v_info = QtWidgets.QVBoxLayout()
        v_info.setSpacing(4)
        v_info.setAlignment(QtCore.Qt.AlignVCenter)

        lbl_name = QtWidgets.QLabel("LUMENIA")
        lbl_name.setStyleSheet("font-size: 24px; font-weight: 800; letter-spacing: 2px; color: #ffffff;")
        
        lbl_sub = QtWidgets.QLabel(tr("app.tagline", "Digital Art & Paint Studio • Professional Edition"))
        lbl_sub.setStyleSheet("font-size: 11px; color: #c084fc; font-weight: 600;")

        lbl_ver = QtWidgets.QLabel(f"{tr('dialogs.version', 'Versão')} 2.5.0 (Build 2026.08)")
        lbl_ver.setStyleSheet("font-size: 11px; color: #a1a1aa;")

        v_info.addWidget(lbl_name)
        v_info.addWidget(lbl_sub)
        v_info.addWidget(lbl_ver)
        header.addLayout(v_info)

        self.content_layout.addLayout(header)

        # Divisor
        sep1 = QtWidgets.QFrame()
        sep1.setFrameShape(QtWidgets.QFrame.HLine)
        sep1.setStyleSheet("color: rgba(255,255,255,0.12);")
        self.content_layout.addWidget(sep1)

        # ── Cartão de Recursos / Arquitetura do Motor ───────────────────────
        card = QtWidgets.QFrame()
        card.setObjectName("InfoCard")
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(10)

        specs = [
            (f"⚡ {tr('dialogs.spec_engine', 'Motor Gráfico')}:", "ALADYN Native Core (C++20 / SIMD AVX2 / TileGrid 64×64)"),
            (f"🎨 {tr('dialogs.spec_color', 'Gerenciador de Cor')}:", "Display P3, Adobe RGB, sRGB & Prova de Cores"),
            (f"🖌️ {tr('dialogs.spec_brushes', 'Motores de Pincel')}:", "Catmull-Rom Spline, Óleo/Impasto, Aquarela e Inker"),
            (f"📐 {tr('dialogs.spec_selection', 'Suíte de Seleções')}:", "Varinha Mágica, Retangular, Elíptica e Laço Poligonal"),
            (f"🔄 {tr('dialogs.spec_transform', 'Transformação')}:", "Livre com Pivô Móvel, 8 Alças & Interpolação"),
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

        self.content_layout.addWidget(card)
        self.content_layout.addStretch()

        # ── Botão Fechar ────────────────────────────────────────────────────
        bottom_lay = QtWidgets.QHBoxLayout()
        lbl_copy = QtWidgets.QLabel("© 2026 Lumenia Team. All rights reserved.")
        lbl_copy.setStyleSheet("font-size: 10px; color: #71717a;")
        bottom_lay.addWidget(lbl_copy)
        bottom_lay.addStretch()

        btn_close = QtWidgets.QPushButton(tr("dialogs.ok", "OK"))
        btn_close.setFixedWidth(80)
        btn_close.setFixedHeight(28)
        btn_close.setCursor(QtCore.Qt.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        bottom_lay.addWidget(btn_close)

        self.content_layout.addLayout(bottom_lay)

    def _apply_theme(self):
        theme = ThemeManager.instance()
        bg_card = theme.get_color("bg_panel") or "#221c33"
        border = theme.get_color("border") or "#342c4c"
        accent = theme.get_color("accent") or "#9333ea"

        self.setStyleSheet(f"""
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
