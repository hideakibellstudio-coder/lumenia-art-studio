"""
AboutDialog — Diálogo Moderno 'Sobre o Lumenia' (ARCcC i18n).
============================================================
Exibe a identidade visual oficial, especificações do ALADYN Engine e créditos.
"""

from __future__ import annotations
import os
from PySide6 import QtWidgets, QtCore, QtGui
from ui.infrastructure.theme.manager import ThemeManager
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.infrastructure.i18n import tr
from ui.infrastructure.runtime_paths import resource_path
from ui.infrastructure.icons import get_icon


class AboutDialog(BaseFramelessDialog):
    """Diálogo Sobre o Lumenia com design profissional e identidade visual oficial."""

    def __init__(self, parent=None):
        super().__init__(title=tr("dialogs.about_title", "Sobre o Lumenia"), icon_name="info", parent=parent, modal=True)
        self.resize(520, 500)

        self.icon_path = str(resource_path("assets", "images", "icon_lumenia.png"))

        self._build_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

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

        self.lbl_name = QtWidgets.QLabel("LUMENIA")
        self.lbl_name.setProperty("heading", "true")
        
        self.lbl_sub = QtWidgets.QLabel(tr("app.tagline", "Digital Art & Paint Studio • Professional Edition"))
        self.lbl_sub.setProperty("accent", "true")

        self.lbl_ver = QtWidgets.QLabel(f"{tr('dialogs.version', 'Versão')} 2.5.0 (Build 2026.08)")
        self.lbl_ver.setProperty("muted", "true")

        v_info.addWidget(self.lbl_name)
        v_info.addWidget(self.lbl_sub)
        v_info.addWidget(self.lbl_ver)
        header.addLayout(v_info)

        self.content_layout.addLayout(header)

        # Divisor
        self.sep1 = QtWidgets.QFrame()
        self.sep1.setFrameShape(QtWidgets.QFrame.HLine)
        self.content_layout.addWidget(self.sep1)

        # ── Cartão de Recursos / Arquitetura do Motor ───────────────────────
        card = QtWidgets.QFrame()
        card.setObjectName("InfoCard")
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(16, 14, 16, 14)
        card_lay.setSpacing(10)

        self.spec_labels = []
        specs = [
            ("dialogs.spec_engine", "Motor Gráfico", "ALADYN Native Core (C++20 / SIMD AVX2 / TileGrid 64×64)", "zap"),
            ("dialogs.spec_color", "Gerenciador de Cor", "Display P3, Adobe RGB, sRGB & Prova de Cores", "palette"),
            ("dialogs.spec_brushes", "Motores de Pincel", "Catmull-Rom Spline, Óleo/Impasto, Aquarela e Inker", "brush"),
            ("dialogs.spec_selection", "Suíte de Seleções", "Varinha Mágica, Retangular, Elíptica e Laço Poligonal", "target"),
            ("dialogs.spec_transform", "Transformação", "Livre com Pivô Móvel, 8 Alças & Interpolação", "transform"),
        ]

        for key, default, desc, icon_name in specs:
            row = QtWidgets.QHBoxLayout()
            row.setSpacing(8)
            lbl_icon = QtWidgets.QLabel()
            lbl_icon.setFixedSize(16, 16)
            lbl_icon.setPixmap(get_icon(icon_name).pixmap(16, 16))
            lbl_t = QtWidgets.QLabel(f"{tr(key, default)}:")
            lbl_t.setProperty("heading", "true")
            lbl_t.setMinimumWidth(135)
            lbl_d = QtWidgets.QLabel(desc)
            lbl_d.setProperty("muted", "true")
            lbl_d.setWordWrap(True)
            self.spec_labels.append((lbl_t, key, default, lbl_d))
            row.addWidget(lbl_icon)
            row.addWidget(lbl_t)
            row.addWidget(lbl_d, 1)
            card_lay.addLayout(row)

        self.content_layout.addWidget(card)
        self.content_layout.addStretch()

        # ── Botão Fechar ────────────────────────────────────────────────────
        bottom_lay = QtWidgets.QHBoxLayout()
        self.lbl_copy = QtWidgets.QLabel("© 2026 Lumenia Team. All rights reserved.")
        self.lbl_copy.setProperty("muted", "true")
        bottom_lay.addWidget(self.lbl_copy)
        bottom_lay.addStretch()

        self.btn_close = QtWidgets.QPushButton(tr("dialogs.ok", "OK"))
        self.btn_close.setObjectName("accentButton")
        self.btn_close.setFixedWidth(80)
        self.btn_close.setFixedHeight(28)
        self.btn_close.clicked.connect(self.accept)
        bottom_lay.addWidget(self.btn_close)

        self.content_layout.addLayout(bottom_lay)

        from ui.infrastructure.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self) -> None:
        from ui.infrastructure.i18n import tr
        title = tr("dialogs.about_title", "Sobre o Lumenia Studio")
        self.setWindowTitle(title)
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(title)
        if hasattr(self, "lbl_sub"):
            self.lbl_sub.setText(tr("app.tagline", "Digital Art & Paint Studio • Professional Edition"))
        if hasattr(self, "lbl_ver"):
            self.lbl_ver.setText(f"{tr('dialogs.version', 'Versão')} 2.5.0 (Build 2026.08)")
        if hasattr(self, "spec_labels"):
            for item in self.spec_labels:
                lbl_t, key, default = item[0], item[1], item[2]
                lbl_t.setText(f"{tr(key, default)}:")
        if hasattr(self, "btn_close"):
            self.btn_close.setText(tr("dialogs.ok", "OK"))

    def _apply_theme(self, *args):
        theme = ThemeManager.instance()
        bg_card = theme.get_color("bg_panel")
        border = theme.get_color("border")
        accent = theme.get_color("accent")
        accent_hover = theme.get_color("accent_hover")
        text_main = theme.get_color("text_main")
        text_sec = theme.get_color("text_sec")

        self.lbl_name.setStyleSheet(f"font-size: 24px; font-weight: 800; letter-spacing: 2px; color: {text_main};")
        self.lbl_sub.setStyleSheet(f"font-size: 11px; color: {accent}; font-weight: 600;")
        self.lbl_ver.setStyleSheet(f"font-size: 11px; color: {text_sec};")
        self.lbl_copy.setStyleSheet(f"font-size: 10px; color: {text_sec};")
        self.sep1.setStyleSheet(f"background-color: {border}; border: none; height: 1px; max-height: 1px;")

        if hasattr(self, "spec_labels"):
            for item in self.spec_labels:
                lbl_t = item[0]
                lbl_d = item[3] if len(item) > 3 else None
                lbl_t.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {text_main};")
                if lbl_d:
                    lbl_d.setStyleSheet(f"font-size: 11px; color: {text_sec};")

        self.setStyleSheet(f"""
            #InfoCard {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QPushButton#accentButton {{
                background-color: {accent};
                color: {text_main};
                font-weight: 600;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
            }}
            QPushButton#accentButton:hover {{
                background-color: {accent_hover};
            }}
        """)
