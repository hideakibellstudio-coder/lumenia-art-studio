"""
ThemeDialog — Gerenciador & Customizador Completo de Aparência e Temas (Lumenia V2)
===================================================================================
Interface profissional de 2 colunas no padrão Lumenia V2:
  - Coluna da Esquerda: Filtros (Todos, Dark, Light), busca com ícone SVG e lista de ThemeCards.
  - Coluna da Direita: Inspector de Cores, visualização da paleta e ajustes de geometria e tipografia.

Raio dos cantos e fonte são ajustes do usuário por cima de qualquer tema
(`ThemeManager.set_interface_tweaks`, opções em `ui/core/theme/interface_tweaks.py`).
Até 2026-09-24 os dois combos não estavam ligados a nada, e o filtro
Escuros/Claros comparava o texto traduzido com o português (fora do pt-BR
não filtrava).
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.i18n import I18nManager, tr
from ui.core.icons import get_icon
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from .components.interface_tweaks_group import InterfaceTweaksGroup
from .components.theme_card import ColorDot, ThemeMiniSwatches, ThemeCard

logger = logging.getLogger(__name__)


# ── DIÁLOGO PRINCIPAL DE TEMAS ───────────────────────────────────────────────

class ThemeDialog(BaseFramelessDialog):
    """Gerenciador Visual Completo de Temas e Customizações de Interface."""

    def __init__(self, parent=None):
        super().__init__(title=tr("dialogs.theme_title", "Personalização de Interface & Temas"), icon_name="palette", parent=parent, modal=True)
        self.setObjectName("ThemeDialog")
        self.resize(820, 560)

        self.theme_manager = ThemeManager.instance()
        self._available_themes: List[dict] = self.theme_manager.get_available_themes()
        self._active_theme_key: str = self.theme_manager.current_theme
        self._selected_theme_data: dict = self._get_active_theme_data()

        self._cards: List[ThemeCard] = []

        self._setup_ui()
        self._apply_theme()
        self.theme_manager.themeChanged.connect(self._apply_theme)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _get_active_theme_data(self) -> dict:
        for t in self._available_themes:
            if t.get("file") == self._active_theme_key:
                return t
        return self._available_themes[0] if self._available_themes else {}

    def _setup_ui(self):
        cols_widget = QtWidgets.QWidget()
        cols_layout = QtWidgets.QHBoxLayout(cols_widget)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(14)
        self.content_layout.addWidget(cols_widget, 1)

        # ── COLUNA DA ESQUERDA (LISTA DE TEMAS) ─────────────────────────────
        left_col = QtWidgets.QWidget()
        left_col.setFixedWidth(310)
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

        # Campo de busca com ícone de lupa
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Buscar tema...")
        self.search_box.addAction(get_icon("search"), QtWidgets.QLineEdit.LeadingPosition)
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

        cols_layout.addWidget(left_col)

        # ── COLUNA DA DIREITA (INSPECTOR & AJUSTES) ─────────────────────────
        right_col = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_col)
        right_layout.setContentsMargins(12, 4, 4, 4)
        right_layout.setSpacing(14)

        # Header do Tema Selecionado
        header_box = QtWidgets.QHBoxLayout()
        self.lbl_insp_icon = QtWidgets.QToolButton()
        self.lbl_insp_icon.setFixedSize(44, 44)
        self.lbl_insp_icon.setIconSize(QtCore.QSize(24, 24))
        self.lbl_insp_icon.setIcon(get_icon("moon"))
        self.lbl_insp_icon.setStyleSheet("border: none; background: rgba(255,255,255,0.08); border-radius: 8px;")
        header_box.addWidget(self.lbl_insp_icon)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_insp_title = QtWidgets.QLabel("Dark Premium")
        _title_font = QtGui.QFont("Segoe UI", 13)
        _title_font.setBold(True)
        self.lbl_insp_title.setFont(_title_font)

        self.lbl_insp_meta = QtWidgets.QLabel("TEMA ESCURO • por Lumenia")
        self.lbl_insp_meta.setProperty("accent", "true")

        title_box.addWidget(self.lbl_insp_title)
        title_box.addWidget(self.lbl_insp_meta)
        header_box.addLayout(title_box)
        header_box.addStretch()
        right_layout.addLayout(header_box)

        # Paleta de Cores do Tema
        self.palette_group = QtWidgets.QGroupBox()
        palette_layout = QtWidgets.QGridLayout(self.palette_group)
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
            lbl.setProperty("muted", "true")
            lbl.setStyleSheet("font-size: 11px;")

            chip = QtWidgets.QLabel("#000000")
            chip.setFixedHeight(22)
            chip.setAlignment(QtCore.Qt.AlignCenter)
            chip.setStyleSheet("font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 8px;")
            palette_layout.addWidget(chip, row, col + 1)
            self.swatch_items[(k1, k2)] = chip

        right_layout.addWidget(self.palette_group)

        # Ajustes Finos (raio, fonte e escala): componente próprio, view do ThemeManager
        self.tweaks_group = InterfaceTweaksGroup(self.theme_manager)
        right_layout.addWidget(self.tweaks_group)
        right_layout.addStretch()

        # Botões de Ação
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton()
        self.btn_apply.setIcon(get_icon("check"))
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self._on_apply_theme)
        btn_box.addWidget(self.btn_apply)

        btn_box.addSpacing(8)

        self.btn_close = QtWidgets.QPushButton()
        self.btn_close.setFixedHeight(34)
        self.btn_close.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_close)

        right_layout.addLayout(btn_box)
        cols_layout.addWidget(right_col, 1)

        self._build_cards()
        self._select_theme(self._selected_theme_data)

    def retranslate_ui(self) -> None:
        """Atualiza dinamicamente todos os textos deste diálogo quando o idioma muda."""
        self.title_bar.set_title(tr("dialogs.theme_title", "Personalização de Interface & Temas"))

        self.search_box.setPlaceholderText(tr("dialogs.theme_search", "Buscar tema..."))

        self.palette_group.setTitle(tr("dialogs.theme_swatches", "Amostras da Paleta de Cores"))
        self.btn_apply.setText(tr("dialogs.theme_apply", "Aplicar este Tema"))
        self.btn_close.setText(tr("dialogs.close", "Fechar"))

        cur_idx = max(0, self.combo_filter.currentIndex())
        self.combo_filter.blockSignals(True)
        self.combo_filter.clear()
        items = [
            tr("dialogs.theme_filter_all", "Todos os Temas"),
            tr("dialogs.theme_filter_dark", "Temas Escuros (Dark)"),
            tr("dialogs.theme_filter_light", "Temas Claros (Light)"),
        ]
        for label in items:
            self.combo_filter.addItem(label)
        self.combo_filter.setCurrentIndex(cur_idx)
        self.combo_filter.blockSignals(False)

        self.tweaks_group.retranslate()

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
        wanted_type = {1: "dark", 2: "light"}.get(self.combo_filter.currentIndex())  # 0 = todos
        query = self.search_box.text().strip().lower()

        for card in self._cards:
            meta = card.theme_data.get("metadata", {})
            t_type = meta.get("type", "dark")
            t_name = (meta.get("name") or card.theme_data.get("file", "")).lower()
            t_author = meta.get("author", "").lower()

            match_type = wanted_type is None or t_type == wanted_type

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
        meta_key, meta_default = (("dialogs.theme_meta_dark", "TEMA ESCURO • por {author}") if t_type == "dark"
                                  else ("dialogs.theme_meta_light", "TEMA CLARO • por {author}"))
        self.lbl_insp_meta.setText(tr(meta_key, meta_default).format(author=t_author))
        self.lbl_insp_icon.setIcon(get_icon("moon" if t_type == "dark" else "sun"))

        # Atualiza Chips de Cor
        for (k1, k2), chip in self.swatch_items.items():
            hex_val = colors.get(k1) or colors.get(k2) or "#121212"
            chip.setText(hex_val.upper())
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
            self.btn_apply.setText(tr("dialogs.theme_active", "Tema Ativo"))
            self.btn_apply.setEnabled(False)
        else:
            self.btn_apply.setText(tr("dialogs.theme_apply", "Aplicar este Tema"))
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

    def _apply_theme(self, *args):
        from .components.theme_dialog_styles import apply_theme_dialog_styles
        apply_theme_dialog_styles(self, self.theme_manager)

