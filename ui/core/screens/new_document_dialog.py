"""
NewDocumentDialog — Diálogo Moderno de Novo Documento (Lumenia V2)
===================================================================
Interface profissional de 2 colunas no padrão Lumenia V2:
  - Coluna da Esquerda: Abas de categorias (Ilustração, Web, Social, Cinema) com cards visuais interativos.
  - Coluna da Direita: Dimensões, inversão de orientação rápida, resolução DPI, perfis de cor e papel de fundo.
  - Rodapé: Estimativa dinâmica de consumo de memória RAM e botões de ação.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.i18n import tr
from .new_document import (
    PRESET_CATEGORIES,
    BACKGROUND_COLORS,
    PAPER_TEXTURES,
    COLOR_PROFILES,
    estimate_ram_usage_mb,
    PresetCard,
)


class NewDocumentDialog(BaseFramelessDialog):
    """Diálogo enriquecido para criação de novo documento com cards visuais de presets."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(title=tr("dialogs.new_document_title", "Novo Documento"), icon_name="document", parent=parent, modal=True)
        self.resize(780, 540)
        self.setMinimumSize(720, 490)

        self._selected_category = "illustration"
        self._selected_preset_id: Optional[str] = "a4_print"
        self._preset_cards: List[PresetCard] = []

        self._build_ui()
        self._populate_category("illustration")
        self._select_default_preset()
        self._update_ram_estimate()

        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self):
        # ── Área Central de 2 Colunas ─────────────────────────────────
        content_split = QtWidgets.QHBoxLayout()
        content_split.setSpacing(14)

        # === COLUNA ESQUERDA: CATÁLOGO DE PRESETS ====================
        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(8)

        lbl_cat = QtWidgets.QLabel(tr("dialogs.presets_title", "PRESETS DE PROJETO"))
        lbl_cat.setStyleSheet("font-size: 10px; font-weight: bold;")
        left_col.addWidget(lbl_cat)

        self.tab_categories = QtWidgets.QTabBar()
        self.tab_categories.setExpanding(False)
        self.tab_categories.setCursor(QtCore.Qt.PointingHandCursor)
        self._cat_keys = list(PRESET_CATEGORIES.keys())
        for key in self._cat_keys:
            cat = PRESET_CATEGORIES[key]
            self.tab_categories.addTab(cat["name"])
        self.tab_categories.currentChanged.connect(self._on_category_changed)
        left_col.addWidget(self.tab_categories)

        # Scroll com os Cards da Categoria Ativa
        self.cards_scroll = QtWidgets.QScrollArea()
        self.cards_scroll.setWidgetResizable(True)
        self.cards_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.cards_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 4, 6, 4)
        self.cards_layout.setSpacing(6)
        self.cards_scroll.setWidget(self.cards_container)
        left_col.addWidget(self.cards_scroll, 1)

        content_split.addLayout(left_col, 11)

        # Divisor Vertical
        v_sep = QtWidgets.QFrame()
        v_sep.setFrameShape(QtWidgets.QFrame.VLine)
        v_sep.setObjectName("DialogDivider")
        content_split.addWidget(v_sep)

        # === COLUNA DIREITA: DETALHES E PROPRIEDADES ==================
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(10)

        # 1. Nome do Documento
        row_name = QtWidgets.QHBoxLayout()
        row_name.setSpacing(8)
        lbl_name = QtWidgets.QLabel(f"{tr('dialogs.doc_name', 'Nome')}:")
        lbl_name.setStyleSheet("font-size: 11px; font-weight: bold;")
        self.txt_name = QtWidgets.QLineEdit(tr("dialogs.untitled_doc", "Sem Título-1"))
        self.txt_name.setFixedHeight(26)
        row_name.addWidget(lbl_name)
        row_name.addWidget(self.txt_name, 1)
        right_col.addLayout(row_name)

        # 2. Grupo: Dimensões do Canvas
        grp_dim = QtWidgets.QGroupBox(tr("dialogs.canvas_dimensions", "Dimensões do Canvas"))
        lay_dim = QtWidgets.QVBoxLayout(grp_dim)
        lay_dim.setContentsMargins(10, 10, 10, 10)
        lay_dim.setSpacing(8)

        # Largura & Altura com botão Swap
        row_wh = QtWidgets.QHBoxLayout()
        row_wh.setSpacing(8)

        # Largura
        v_w = QtWidgets.QVBoxLayout()
        v_w.setSpacing(2)
        lbl_w = QtWidgets.QLabel(f"{tr('dialogs.width', 'Largura')}:")
        lbl_w.setStyleSheet("font-size: 10px;")
        self.spn_width = QtWidgets.QSpinBox()
        self.spn_width.setRange(100, 16384)
        self.spn_width.setValue(2480)
        self.spn_width.setSuffix(" px")
        self.spn_width.setFixedHeight(26)
        self.spn_width.valueChanged.connect(self._on_dimension_changed)
        v_w.addWidget(lbl_w)
        v_w.addWidget(self.spn_width)
        row_wh.addLayout(v_w, 1)

        # Botão Swap Orientação
        self.btn_swap_orient = QtWidgets.QToolButton()
        self.btn_swap_orient.setFixedSize(30, 26)
        self.btn_swap_orient.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_swap_orient.setToolTip(tr("dialogs.swap_orientation", "Alternar Orientação (Paisagem ⤨ Retrato)"))
        self.btn_swap_orient.clicked.connect(self._on_swap_orientation)
        v_btn = QtWidgets.QVBoxLayout()
        v_btn.setContentsMargins(0, 12, 0, 0)
        v_btn.addWidget(self.btn_swap_orient)
        row_wh.addLayout(v_btn)

        # Altura
        v_h = QtWidgets.QVBoxLayout()
        v_h.setSpacing(2)
        lbl_h = QtWidgets.QLabel(f"{tr('dialogs.height', 'Altura')}:")
        lbl_h.setStyleSheet("font-size: 10px;")
        self.spn_height = QtWidgets.QSpinBox()
        self.spn_height.setRange(100, 16384)
        self.spn_height.setValue(3508)
        self.spn_height.setSuffix(" px")
        self.spn_height.setFixedHeight(26)
        self.spn_height.valueChanged.connect(self._on_dimension_changed)
        v_h.addWidget(lbl_h)
        v_h.addWidget(self.spn_height)
        row_wh.addLayout(v_h, 1)

        lay_dim.addLayout(row_wh)

        # Resolução DPI
        row_dpi = QtWidgets.QHBoxLayout()
        row_dpi.setSpacing(8)
        lbl_dpi = QtWidgets.QLabel(f"{tr('dialogs.resolution', 'Resolução')}:")
        lbl_dpi.setStyleSheet("font-size: 10px;")
        self.spn_dpi = QtWidgets.QSpinBox()
        self.spn_dpi.setRange(72, 1200)
        self.spn_dpi.setValue(300)
        self.spn_dpi.setSuffix(" DPI")
        self.spn_dpi.setFixedHeight(24)
        self.spn_dpi.valueChanged.connect(self._on_dpi_changed)
        row_dpi.addWidget(lbl_dpi)
        row_dpi.addWidget(self.spn_dpi, 1)
        lay_dim.addLayout(row_dpi)

        # Perfil de Cor
        row_prof = QtWidgets.QHBoxLayout()
        row_prof.setSpacing(8)
        lbl_prof = QtWidgets.QLabel(f"{tr('dialogs.color_space', 'Espaço de Cor')}:")
        lbl_prof.setStyleSheet("font-size: 10px;")
        self.cmb_color_prof = QtWidgets.QComboBox()
        self.cmb_color_prof.setFixedHeight(24)
        for pid, name in COLOR_PROFILES:
            self.cmb_color_prof.addItem(name, pid)
        row_prof.addWidget(lbl_prof)
        row_prof.addWidget(self.cmb_color_prof, 1)
        lay_dim.addLayout(row_prof)

        right_col.addWidget(grp_dim)

        # 3. Grupo: Papel de Fundo (Layer 0)
        grp_paper = QtWidgets.QGroupBox(tr("dialogs.paper_background", "Papel de Fundo (Layer 0)"))
        lay_paper = QtWidgets.QVBoxLayout(grp_paper)
        lay_paper.setContentsMargins(10, 10, 10, 10)
        lay_paper.setSpacing(8)

        row_bg = QtWidgets.QHBoxLayout()
        row_bg.setSpacing(8)
        lbl_bg = QtWidgets.QLabel(f"{tr('dialogs.paper_color', 'Cor')}:")
        lbl_bg.setStyleSheet("font-size: 10px;")
        self.cmb_bg_color = QtWidgets.QComboBox()
        self.cmb_bg_color.setFixedHeight(24)
        for name, color in BACKGROUND_COLORS:
            self.cmb_bg_color.addItem(name, color)
        row_bg.addWidget(lbl_bg)
        row_bg.addWidget(self.cmb_bg_color, 1)
        lay_paper.addLayout(row_bg)

        row_tex = QtWidgets.QHBoxLayout()
        row_tex.setSpacing(8)
        lbl_tex = QtWidgets.QLabel(f"{tr('dialogs.paper_texture', 'Textura')}:")
        lbl_tex.setStyleSheet("font-size: 10px;")
        self.cmb_paper_tex = QtWidgets.QComboBox()
        self.cmb_paper_tex.setFixedHeight(24)
        for name, tid in PAPER_TEXTURES:
            self.cmb_paper_tex.addItem(name, tid)
        row_tex.addWidget(lbl_tex)
        row_tex.addWidget(self.cmb_paper_tex, 1)
        lay_paper.addLayout(row_tex)

        right_col.addWidget(grp_paper)
        right_col.addStretch()

        content_split.addLayout(right_col, 9)
        self.content_layout.addLayout(content_split, 1)

        # ── Rodapé Informativo & Botões de Ação ───────────────────────
        h_sep = QtWidgets.QFrame()
        h_sep.setFrameShape(QtWidgets.QFrame.HLine)
        h_sep.setObjectName("DialogDivider")
        self.content_layout.addWidget(h_sep)

        foot_row = QtWidgets.QHBoxLayout()
        foot_row.setSpacing(10)

        # Indicador de RAM Estimada
        self.lbl_ram_estimate = QtWidgets.QLabel()
        self.lbl_ram_estimate.setStyleSheet("font-size: 10px;")
        foot_row.addWidget(self.lbl_ram_estimate)
        foot_row.addStretch()

        self.btn_cancel = QtWidgets.QPushButton(tr("dialogs.cancel", "Cancelar"))
        self.btn_cancel.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_cancel.setFixedSize(90, 30)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_create = QtWidgets.QPushButton(tr("dialogs.create_document", "Criar Documento"))
        self.btn_create.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_create.setDefault(True)
        self.btn_create.setFixedHeight(30)
        self.btn_create.clicked.connect(self.accept)

        foot_row.addWidget(self.btn_cancel)
        foot_row.addWidget(self.btn_create)
        self.content_layout.addLayout(foot_row)

    def _on_category_changed(self, idx: int):
        if 0 <= idx < len(self._cat_keys):
            self._selected_category = self._cat_keys[idx]
            self._populate_category(self._selected_category)

    def _populate_category(self, cat_key: str):
        # Limpa os cards anteriores
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._preset_cards.clear()

        cat = PRESET_CATEGORIES.get(cat_key, {})
        presets = cat.get("presets", [])

        for pid, name, w, h, dpi, icon_name, desc in presets:
            card = PresetCard(
                preset_id=pid,
                name=name,
                width=w,
                height=h,
                dpi=dpi,
                icon_name=icon_name,
                description=desc,
                parent=self.cards_container,
            )
            card.clicked.connect(self._on_preset_card_clicked)
            if pid == self._selected_preset_id:
                card.set_selected(True)
            self.cards_layout.addWidget(card)
            self._preset_cards.append(card)

        self.cards_layout.addStretch()

    def _select_default_preset(self):
        if self._preset_cards:
            self._preset_cards[0].set_selected(True)
            self._selected_preset_id = self._preset_cards[0].preset_id

    def _on_preset_card_clicked(self, pid: str, w: int, h: int, dpi: int):
        self._selected_preset_id = pid
        for card in self._preset_cards:
            card.set_selected(card.preset_id == pid)

        self.spn_width.blockSignals(True)
        self.spn_height.blockSignals(True)
        self.spn_dpi.blockSignals(True)
        try:
            self.spn_width.setValue(w)
            self.spn_height.setValue(h)
            self.spn_dpi.setValue(dpi)
        finally:
            self.spn_width.blockSignals(False)
            self.spn_height.blockSignals(False)
            self.spn_dpi.blockSignals(False)

        self._update_ram_estimate()

    def _on_dimension_changed(self):
        # Se o usuário alterou valores manualmente, desmarca preset específico
        self._unselect_cards_if_mismatched()
        self._update_ram_estimate()

    def _on_dpi_changed(self):
        self._unselect_cards_if_mismatched()

    def _unselect_cards_if_mismatched(self):
        cw, ch, cdpi = self.spn_width.value(), self.spn_height.value(), self.spn_dpi.value()
        matched = False
        card: PresetCard
        for card in self._preset_cards:
            if (card.p_width == cw and card.p_height == ch and card.p_dpi == cdpi) or                (card.p_width == ch and card.p_height == cw and card.p_dpi == cdpi):
                card.set_selected(True)
                self._selected_preset_id = card.preset_id
                matched = True
            else:
                card.set_selected(False)
        if not matched:
            self._selected_preset_id = None

    def _on_swap_orientation(self):
        w = self.spn_width.value()
        h = self.spn_height.value()
        self.spn_width.setValue(h)
        self.spn_height.setValue(w)

    def _update_ram_estimate(self):
        w = self.spn_width.value()
        h = self.spn_height.value()
        mb = estimate_ram_usage_mb(w, h, num_layers=3)
        mp = (float(w) * float(h)) / 1_000_000.0
        self.lbl_ram_estimate.setText(f"📐 {mp:.1f} Megapixels  •  💾 RAM estimada: ~{mb:.1f} MB (3 camadas)")

    def get_document_params(self) -> Dict[str, Any]:
        """Retorna todos os parâmetros de criação do documento para inicialização do motor."""
        return {
            "name": self.txt_name.text().strip() or "Sem Título",
            "width": self.spn_width.value(),
            "height": self.spn_height.value(),
            "dpi": self.spn_dpi.value(),
            "color_profile_id": self.cmb_color_prof.currentData(),
            "bg_color": self.cmb_bg_color.currentData(),
            "paper_texture_id": self.cmb_paper_tex.currentData(),
        }

    def get_values(self) -> tuple[str, int, int]:
        """Compatibilidade backward com chamadas antigas."""
        p = self.get_document_params()
        return p["name"], p["width"], p["height"]

    def _apply_theme(self, *_):
        tm = ThemeManager.instance()
        bg_main = tm.get_color("bg_base", "#12121a")
        bg_card = tm.get_color("bg_card", "#1e1e24")
        bg_input = tm.get_color("bg_input", "#18181f")
        border = tm.get_color("border", "#2e2e38")
        text = tm.get_color("text_main", "#f3f4f6")
        muted = tm.get_color("text_muted", "#9ca3af")
        accent = tm.get_color("accent", "#6366f1")

        self.btn_swap_orient.setIcon(get_icon("refresh", color=text))
        self.lbl_ram_estimate.setStyleSheet(f"font-size: 10px; color: {muted};")

        self.setStyleSheet(f"""
            NewDocumentDialog {{
                background-color: {bg_main};
                color: {text};
            }}
            QGroupBox {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 8px;
                margin-top: 8px;
                padding: 10px;
                font-weight: bold;
                font-size: 10px;
                color: {accent};
            }}
            QLabel {{
                color: {text};
            }}
            QLineEdit, QComboBox, QSpinBox {{
                background-color: {bg_input};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 6px;
                color: {text};
                font-size: 11px;
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {accent};
            }}
            QToolButton {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton#btnCancel {{
                background-color: {bg_card};
                color: {text};
                border: 1px solid {border};
            }}
            #DialogDivider {{
                color: {border};
                background-color: {border};
            }}
        """)
