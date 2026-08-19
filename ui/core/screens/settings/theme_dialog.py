"""
ThemeDialog — Gerenciador & Customizador Completo de Aparência e Temas (Lumenia V2)
===================================================================================
Interface profissional de 2 colunas no padrão Lumenia V2:
  - Coluna da Esquerda: Filtros (Todos, Dark, Light), busca instantânea e lista de ThemeCards com swatches.
  - Coluna da Direita: Inspector de Cores, visualização da paleta completa e ajustes de tipografia e raio de bordas.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager

logger = logging.getLogger(__name__)


# ── SWATCHES DE CORES INLINE ──────────────────────────────────────────────────

class ColorDot(QtWidgets.QFrame):
    """Círculo colorido representativo de um canal de cor."""

    def __init__(self, color_hex: str, size: int = 14, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setStyleSheet(f"""
            background-color: {color_hex};
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: {size // 2}px;
        """)


class ThemeMiniSwatches(QtWidgets.QWidget):
    """Grupo de 4 cores principais do tema."""

    def __init__(self, colors: dict, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        bg = colors.get("bg_main") or colors.get("BG_DARKEST") or "#121212"
        panel = colors.get("bg_panel") or colors.get("BG_DARKER") or "#1e1e1e"
        accent = colors.get("accent") or colors.get("ACCENT") or "#ff5252"
        text = colors.get("text_main") or colors.get("FG_PRIMARY") or "#ffffff"

        layout.addWidget(ColorDot(bg, 14))
        layout.addWidget(ColorDot(panel, 14))
        layout.addWidget(ColorDot(accent, 14))
        layout.addWidget(ColorDot(text, 14))


# ── CARTÃO INDIVIDUAL DO TEMA (COLUNA ESQUERDA) ───────────────────────────────

class ThemeCard(QtWidgets.QFrame):
    """Cartão individual representando um tema na lista esquerda."""

    selected = QtCore.Signal(dict)

    def __init__(self, theme_data: dict, is_selected: bool = False, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.theme_data = theme_data
        self.is_selected = is_selected
        self.is_active = is_active
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._build_ui()
        self.update_style()

    def _build_ui(self):
        self.setFixedHeight(68)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Ícone de tipo (Sol / Lua)
        meta = self.theme_data.get("metadata", {})
        t_type = meta.get("type", "dark")
        self.icon_label = QtWidgets.QLabel("🌙" if t_type == "dark" else "☀️")
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 16px; background-color: rgba(255,255,255,0.06); border-radius: 6px;")
        layout.addWidget(self.icon_label)

        # Informações do Tema
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setAlignment(QtCore.Qt.AlignVCenter)

        name = meta.get("name") or self.theme_data.get("file", "Tema")
        author = meta.get("author", "Lumenia")
        self.name_label = QtWidgets.QLabel(name)
        self.name_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        self.author_label = QtWidgets.QLabel(f"por {author}")
        self.author_label.setStyleSheet("font-size: 10px; color: #888888;")

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.author_label)
        layout.addLayout(text_layout)
        layout.addStretch()

        # Swatches e Badge
        right_box = QtWidgets.QVBoxLayout()
        right_box.setSpacing(4)
        right_box.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        self.swatches = ThemeMiniSwatches(self.theme_data.get("colors", {}))
        right_box.addWidget(self.swatches)

        self.badge_label = QtWidgets.QLabel("ATIVO" if self.is_active else "")
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 1px 5px; border-radius: 4px;" if self.is_active else "color: transparent;"
        )
        right_box.addWidget(self.badge_label)
        layout.addLayout(right_box)

    def set_active_state(self, is_active: bool):
        self.is_active = is_active
        self.badge_label.setText("ATIVO" if is_active else "")
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 1px 5px; border-radius: 4px;" if is_active else "color: transparent;"
        )

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.theme_data)

    def update_style(self):
        is_dark = getattr(ThemeManager.instance(), "is_dark", True)
        if self.is_selected:
            bg = "#2a3441" if is_dark else "#e2e8f0"
            border = "#ff5252"
        else:
            bg = "#1e1e1e" if is_dark else "#ffffff"
            border = "#2e2e2e" if is_dark else "#e0e0e0"

        text_color = "#ffffff" if is_dark else "#1a202c"

        self.setStyleSheet(f"""
            ThemeCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)


# ── DIÁLOGO PRINCIPAL (2 COLUNAS) ───────────────────────────────────────────

class ThemeDialog(QtWidgets.QDialog):
    """Central de Customização de Aparência & Temas em 2 Colunas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações de Aparência & Temas")
        self.setFixedSize(820, 560)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.theme_manager = ThemeManager.instance()
        self._initial_theme = self.theme_manager.current_theme
        self._selected_theme_data: dict = {}
        self._active_theme_key: str = self._initial_theme
        self._cards: List[ThemeCard] = []

        self._load_data()
        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

    def _load_data(self):
        self.theme_manager.load_all_themes()
        self._available_themes = self.theme_manager.get_available_themes()

        # Encontra o tema ativo inicial
        for t in self._available_themes:
            if t.get("file") == self._active_theme_key:
                self._selected_theme_data = t
                break
        if not self._selected_theme_data and self._available_themes:
            self._selected_theme_data = self._available_themes[0]

    def _setup_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ── COLUNA DA ESQUERDA (330px) ──────────────────────────────────────
        left_col = QtWidgets.QWidget()
        left_col.setFixedWidth(330)
        left_layout = QtWidgets.QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Filtro de tipo
        self.combo_filter = QtWidgets.QComboBox()
        self.combo_filter.addItems([
            "Todos os Temas",
            "Temas Escuros (Dark)",
            "Temas Claros (Light)"
        ])
        self.combo_filter.currentIndexChanged.connect(self._filter_themes)
        left_layout.addWidget(self.combo_filter)

        # Campo de busca
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("🔍 Buscar tema...")
        self.search_box.textChanged.connect(self._filter_themes)
        left_layout.addWidget(self.search_box)

        # ScrollArea com lista de cartões
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.cards_container)
        left_layout.addWidget(self.scroll_area)

        main_layout.addWidget(left_col)

        # ── COLUNA DA DIREITA (INSPECTOR & AJUSTES) ─────────────────────────
        right_col = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_col)
        right_layout.setContentsMargins(12, 4, 4, 4)
        right_layout.setSpacing(14)

        # Header do Tema Selecionado
        header_box = QtWidgets.QHBoxLayout()
        self.lbl_insp_icon = QtWidgets.QLabel("🌙")
        self.lbl_insp_icon.setFixedSize(44, 44)
        self.lbl_insp_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_insp_icon.setStyleSheet("font-size: 22px; background: rgba(255,255,255,0.08); border-radius: 8px;")
        header_box.addWidget(self.lbl_insp_icon)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_insp_title = QtWidgets.QLabel("Dark Premium")
        font = self.lbl_insp_title.font()
        font.setPointSize(13)
        font.setBold(True)
        self.lbl_insp_title.setFont(font)

        self.lbl_insp_meta = QtWidgets.QLabel("TEMA ESCURO • por Lumenia")
        self.lbl_insp_meta.setStyleSheet("color: #ff5252; font-size: 11px; font-weight: bold;")

        title_box.addWidget(self.lbl_insp_title)
        title_box.addWidget(self.lbl_insp_meta)
        header_box.addLayout(title_box)
        header_box.addStretch()
        right_layout.addLayout(header_box)

        # Paleta de Cores do Tema (Swatches Detalhados)
        palette_group = QtWidgets.QGroupBox("Amostras da Paleta de Cores")
        palette_layout = QtWidgets.QGridLayout(palette_group)
        palette_layout.setContentsMargins(12, 12, 12, 12)
        palette_layout.setSpacing(8)

        self.swatch_items = {}
        color_keys = [
            ("Fundo Principal", "BG_DARKEST", "bg_main"),
            ("Painéis & Barras", "BG_DARKER", "bg_panel"),
            ("Controles & Docks", "BG_MID", "border_control"),
            ("Destaque (Accent)", "ACCENT", "accent"),
            ("Texto Primário", "FG_PRIMARY", "text_main"),
            ("Bordas da UI", "BORDER", "border"),
        ]

        for i, (label, k1, k2) in enumerate(color_keys):
            row = i // 2
            col = (i % 2) * 2

            lbl = QtWidgets.QLabel(label)
            lbl.setStyleSheet("font-size: 11px; color: #a1a1aa;")
            palette_layout.addWidget(lbl, row, col)

            chip = QtWidgets.QLabel("#000000")
            chip.setFixedHeight(22)
            chip.setAlignment(QtCore.Qt.AlignCenter)
            chip.setStyleSheet("font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
            palette_layout.addWidget(chip, row, col + 1)
            self.swatch_items[(k1, k2)] = chip

        right_layout.addWidget(palette_group)

        # Ajustes de Interface (UI Tweaks)
        tweaks_group = QtWidgets.QGroupBox("Ajustes Globais de Geometria & Tipografia")
        tweaks_layout = QtWidgets.QVBoxLayout(tweaks_group)
        tweaks_layout.setContentsMargins(12, 12, 12, 12)
        tweaks_layout.setSpacing(10)

        # Raio dos Cantos
        row_radius = QtWidgets.QHBoxLayout()
        lbl_rad = QtWidgets.QLabel("Arredondamento dos Cantos:")
        lbl_rad.setStyleSheet("font-size: 12px;")
        self.combo_radius = QtWidgets.QComboBox()
        self.combo_radius.addItems(["Compacto (4px)", "Padrão Studio (6px)", "Arredondado (8px)", "Ultra-Smooth (12px)"])
        self.combo_radius.setCurrentIndex(1)
        row_radius.addWidget(lbl_rad)
        row_radius.addStretch()
        row_radius.addWidget(self.combo_radius)
        tweaks_layout.addLayout(row_radius)

        # Família da Fonte
        row_font = QtWidgets.QHBoxLayout()
        lbl_fnt = QtWidgets.QLabel("Família da Fonte da Interface:")
        lbl_fnt.setStyleSheet("font-size: 12px;")
        self.combo_font = QtWidgets.QComboBox()
        self.combo_font.addItems(["Segoe UI (Padrão Windows)", "Roboto / System", "Inter Display", "Helvetica / Arial"])
        row_font.addWidget(lbl_fnt)
        row_font.addStretch()
        row_font.addWidget(self.combo_font)
        tweaks_layout.addLayout(row_font)

        right_layout.addWidget(tweaks_group)
        right_layout.addStretch()

        # Botões de Ação
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("✓ Aplicar este Tema")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self._on_apply_theme)
        btn_box.addWidget(self.btn_apply)

        btn_box.addSpacing(8)

        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        right_layout.addLayout(btn_box)
        main_layout.addWidget(right_col)

        self._build_cards()
        self._select_theme(self._selected_theme_data)

    def _build_cards(self):
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for theme in self._available_themes:
            t_key = theme.get("file", "")
            is_sel = (t_key == self._selected_theme_data.get("file", ""))
            is_act = (t_key == self._active_theme_key)
            card = ThemeCard(theme, is_selected=is_sel, is_active=is_act)
            card.selected.connect(self._select_theme)
            self._cards.append(card)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _filter_themes(self):
        filter_text = self.combo_filter.currentText()
        query = self.search_box.text().strip().lower()

        for card in self._cards:
            meta = card.theme_data.get("metadata", {})
            t_type = meta.get("type", "dark")
            t_name = (meta.get("name") or card.theme_data.get("file", "")).lower()
            t_author = meta.get("author", "").lower()

            match_type = True
            if filter_text == "Temas Escuros (Dark)" and t_type != "dark":
                match_type = False
            elif filter_text == "Temas Claros (Light)" and t_type != "light":
                match_type = False

            match_query = not query or (query in t_name) or (query in t_author)
            card.setVisible(match_type and match_query)

    def _select_theme(self, theme_data: dict):
        self._selected_theme_data = theme_data
        t_key = theme_data.get("file", "")

        for card in self._cards:
            card.is_selected = (card.theme_data.get("file") == t_key)
            card.update_style()

        meta = theme_data.get("metadata", {})
        colors = theme_data.get("colors", {})
        t_name = meta.get("name") or t_key
        t_author = meta.get("author", "Lumenia")
        t_type = meta.get("type", "dark")

        self.lbl_insp_title.setText(t_name)
        self.lbl_insp_meta.setText(f"TEMA {'ESCURO' if t_type == 'dark' else 'CLARO'} • por {t_author}")
        self.lbl_insp_icon.setText("🌙" if t_type == "dark" else "☀️")

        # Atualiza Chips de Cor
        for (k1, k2), chip in self.swatch_items.items():
            hex_val = colors.get(k1) or colors.get(k2) or "#121212"
            chip.setText(hex_val.upper())
            # Contraste de texto preto/branco no chip
            chip.setStyleSheet(f"""
                background-color: {hex_val};
                color: {'#ffffff' if t_type == 'dark' or k1 in ('ACCENT', 'BG_DARKEST') else '#000000'};
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            """)

        # Atualiza botão
        if t_key == self._active_theme_key:
            self.btn_apply.setText("✓ Tema Ativo")
            self.btn_apply.setEnabled(False)
        else:
            self.btn_apply.setText("✓ Aplicar este Tema")
            self.btn_apply.setEnabled(True)

    def _on_apply_theme(self):
        t_key = self._selected_theme_data.get("file", "")
        if not t_key:
            return

        self._active_theme_key = t_key
        self.theme_manager.apply_theme(t_key)

        for card in self._cards:
            card.set_active_state(card.theme_data.get("file") == t_key)

        self._select_theme(self._selected_theme_data)

    def _apply_theme(self):
        is_dark = getattr(ThemeManager.instance(), "is_dark", True)
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #18181b;
                    color: #f4f4f5;
                }
                QGroupBox {
                    font-size: 11px;
                    font-weight: bold;
                    color: #a1a1aa;
                    border: 1px solid #27272a;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding-top: 14px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 4px;
                }
                QLineEdit, QComboBox {
                    background-color: #27272a;
                    color: #f4f4f5;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QComboBox QAbstractItemView {
                    background-color: #27272a;
                    color: #f4f4f5;
                    selection-background-color: #ff5252;
                    border: 1px solid #3f3f46;
                }
                QPushButton {
                    background-color: #27272a;
                    color: #f4f4f5;
                    border: 1px solid #3f3f46;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #3f3f46;
                }
                QPushButton:disabled {
                    background-color: #1f1f23;
                    color: #71717a;
                    border-color: #27272a;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #f8fafc;
                    color: #0f172a;
                }
                QGroupBox {
                    font-size: 11px;
                    font-weight: bold;
                    color: #64748b;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    margin-top: 12px;
                    padding-top: 14px;
                }
                QLineEdit, QComboBox {
                    background-color: #ffffff;
                    color: #0f172a;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #0f172a;
                    selection-background-color: #ff5252;
                    selection-color: #ffffff;
                    border: 1px solid #cbd5e1;
                }
                QPushButton {
                    background-color: #ffffff;
                    color: #0f172a;
                    border: 1px solid #cbd5e1;
                    border-radius: 6px;
                    padding: 6px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #f1f5f9;
                }
                QPushButton:disabled {
                    background-color: #e2e8f0;
                    color: #94a3b8;
                }
            """)
