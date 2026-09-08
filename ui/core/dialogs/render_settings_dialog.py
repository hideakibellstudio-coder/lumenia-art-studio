"""
RenderSettingsDialog — Central de Renderização, Perfis de Cor & Prova de Impressão (Lumenia V2)
================================================================================================
Interface moderna de 2 colunas no padrão Lumenia V2:
  - Coluna da Esquerda: Categorias (Digital RGB, Impressão CMYK, Daltonismo, Motor), busca e cards de perfis.
  - Coluna da Direita: Inspector detalhado com especificações técnicas, controle de renderização (Baixa Latência,
    Gama Linear, Deep Color 64-bit) e faixa de pré-visualização de gamut / prova de cores em tempo real.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.widgets.toggle.toggle_switch import ToggleSwitch
from ui.core.theme.manager import ThemeManager
from ui.core.engine.registry import EngineRegistry
from ui.core.icons import get_icon
from ui.core.dialogs.base_dialog import BaseFramelessDialog
from .render_settings_components import (
    ProofingPreviewBar,
    ProfileCard,
    EnginePipelineGroup,
    load_render_settings,
    save_render_settings,
)

__all__ = [
    "RenderSettingsDialog",
    "ProofingPreviewBar",
    "ProfileCard",
    "EnginePipelineGroup",
    "load_render_settings",
    "save_render_settings",
]


# ── DIÁLOGO PRINCIPAL (2 COLUNAS) ───────────────────────────────────────────

class RenderSettingsDialog(BaseFramelessDialog):
    """Central de Renderização e Prova de Cores em 2 colunas."""

    profileChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        from ui.core.i18n import tr, I18nManager
        super().__init__(title=tr("dialogs.render_title", "Configurações de Renderização & Modos de Cor"), icon_name="settings", parent=parent, modal=True)
        self.setObjectName("RenderSettingsDialog")
        self.resize(860, 580)

        self._all_profiles: List[dict] = []
        self._cards: List[ProfileCard] = []
        self._selected_profile: dict = {}
        self._active_profile_id: int = 0
        self._saved_cfg: dict = load_render_settings()

        self._load_data()
        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def _load_data(self):
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_available_color_profiles"):
            self._all_profiles = backend.get_available_color_profiles()
        else:
            from ui.engine_backends.aladyn import AladynBackend
            self._all_profiles = AladynBackend().get_available_color_profiles()

        # Prioriza o perfil ativo salvo no backend ou nas preferências persistentes
        if backend and hasattr(backend, "get_color_profile"):
            backend_pid = backend.get_color_profile()
            self._active_profile_id = backend_pid if backend_pid != 0 else self._saved_cfg.get("profile_id", 0)
        else:
            self._active_profile_id = self._saved_cfg.get("profile_id", 0)

        # Sincroniza o backend se necessário
        if backend and hasattr(backend, "set_color_profile"):
            backend.set_color_profile(self._active_profile_id)

        # Seleção inicial = perfil ativo
        for p in self._all_profiles:
            if p.get("id") == self._active_profile_id:
                self._selected_profile = p
                break
        if not self._selected_profile and self._all_profiles:
            self._selected_profile = self._all_profiles[0]

    def _setup_ui(self):
        cols_widget = QtWidgets.QWidget()
        cols_layout = QtWidgets.QHBoxLayout(cols_widget)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(16)
        self.content_layout.addWidget(cols_widget, 1)

        # ── COLUNA DA ESQUERDA (330px) ──────────────────────────────────────
        left_col = QtWidgets.QWidget()
        left_col.setFixedWidth(330)
        left_layout = QtWidgets.QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Filtro de categorias
        self.combo_cat = QtWidgets.QComboBox()
        self.combo_cat.addItems([
            "Todas as Categorias",
            "Digital (RGB)",
            "Impressão (CMYK)",
            "Acessibilidade",
            "Motor Físico"
        ])
        self.combo_cat.currentIndexChanged.connect(self._filter_profiles)
        left_layout.addWidget(self.combo_cat)

        # Campo de busca com ícone SVG
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Buscar perfil de cor...")
        self.search_box.addAction(get_icon("search"), QtWidgets.QLineEdit.LeadingPosition)
        self.search_box.textChanged.connect(self._filter_profiles)
        left_layout.addWidget(self.search_box)

        # ScrollArea com lista de cards
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

        # ── COLUNA DA DIREITA (INSPECTOR) ───────────────────────────────────
        right_col = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_col)
        right_layout.setContentsMargins(12, 4, 4, 4)
        right_layout.setSpacing(14)

        # Header do Perfil Selecionado
        header_box = QtWidgets.QHBoxLayout()
        self.lbl_insp_icon = QtWidgets.QToolButton()
        self.lbl_insp_icon.setFixedSize(44, 44)
        self.lbl_insp_icon.setIconSize(QtCore.QSize(24, 24))
        self.lbl_insp_icon.setIcon(get_icon("display"))
        self.lbl_insp_icon.setStyleSheet("border: none; background: rgba(255,255,255,0.08); border-radius: 8px;")
        header_box.addWidget(self.lbl_insp_icon)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        self.lbl_insp_title = QtWidgets.QLabel("Padrão (sRGB)")
        _title_font = QtGui.QFont("Segoe UI", 13)
        _title_font.setBold(True)
        self.lbl_insp_title.setFont(_title_font)

        self.lbl_insp_cat = QtWidgets.QLabel("Digital (RGB)")
        self.lbl_insp_cat.setProperty("accent", "true")

        title_box.addWidget(self.lbl_insp_title)
        title_box.addWidget(self.lbl_insp_cat)
        header_box.addLayout(title_box)
        header_box.addStretch()
        right_layout.addLayout(header_box)

        # Descrição do Perfil
        self.lbl_insp_desc = QtWidgets.QLabel("")
        self.lbl_insp_desc.setWordWrap(True)
        self.lbl_insp_desc.setProperty("muted", "true")
        right_layout.addWidget(self.lbl_insp_desc)

        # Barra de Simulação / Prova de Cores
        lbl_bar = QtWidgets.QLabel("Simulação de Gamut & Prova de Cores (Soft Proofing):")
        lbl_bar.setStyleSheet("font-size: 11px; font-weight: bold; margin-top: 4px;")
        right_layout.addWidget(lbl_bar)

        self.preview_bar = ProofingPreviewBar()
        right_layout.addWidget(self.preview_bar)

        # Grupo de Configurações Avançadas do Motor
        self.engine_group = EnginePipelineGroup(self._saved_cfg, self)
        self.switch_lat = self.engine_group.switch_lat
        self.switch_gam = self.engine_group.switch_gam
        self.switch_deep = self.engine_group.switch_deep
        self.combo_undo = self.engine_group.combo_undo
        self.engine_group.settingsChanged.connect(self._save_switch_settings)
        right_layout.addWidget(self.engine_group)
        right_layout.addStretch()

        # Botões de Ação na base
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Aplicar como Modo Ativo")
        self.btn_apply.setIcon(get_icon("check"))
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self._on_apply_profile)
        btn_box.addWidget(self.btn_apply)

        btn_box.addSpacing(8)

        self.btn_close = QtWidgets.QPushButton("Fechar")
        self.btn_close.setFixedHeight(34)
        self.btn_close.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_close)

        right_layout.addLayout(btn_box)
        cols_layout.addWidget(right_col, 1)

        self._build_cards()
        self._select_profile(self._selected_profile)

    def retranslate_ui(self) -> None:
        """Atualiza dinamicamente todos os textos deste diálogo quando o idioma muda."""
        from ui.core.i18n import tr
        if hasattr(self, "title_bar") and self.title_bar:
            self.title_bar.set_title(tr("dialogs.render_title", "Configurações de Renderização & Modos de Cor"))

        if hasattr(self, "search_box"):
            self.search_box.setPlaceholderText(tr("dialogs.render_search", "Buscar perfil de cor..."))

        if hasattr(self, "combo_cat"):
            cur_idx = max(0, self.combo_cat.currentIndex())
            self.combo_cat.blockSignals(True)
            self.combo_cat.clear()
            items = [
                tr("dialogs.render_cat_all", "Todas as Categorias"),
                tr("dialogs.render_cat_rgb", "Digital (RGB)"),
                tr("dialogs.render_cat_cmyk", "Impressão (CMYK)"),
                tr("dialogs.render_cat_a11y", "Acessibilidade"),
                tr("dialogs.render_cat_physics", "Motor Físico"),
            ]
            for label in items:
                self.combo_cat.addItem(label)
            self.combo_cat.setCurrentIndex(cur_idx)
            self.combo_cat.blockSignals(False)

        if hasattr(self, "btn_apply"):
            self.btn_apply.setText(tr("dialogs.render_apply_btn", "Aplicar como Modo Ativo"))
        if hasattr(self, "btn_close"):
            self.btn_close.setText(tr("dialogs.close", "Fechar"))

    def _save_switch_settings(self, *args):
        """Salva o estado atual dos switches e limites no QSettings e aplica ao motor."""
        mb = int(self.combo_undo.currentData() or 256) if hasattr(self, "combo_undo") else 256
        cfg = {
            "profile_id": self._active_profile_id,
            "low_latency": self.switch_lat.isChecked(),
            "linear_gamma": self.switch_gam.isChecked(),
            "deep_color": self.switch_deep.isChecked(),
            "undo_limit_mb": mb,
            "undo_max_steps": self._saved_cfg.get("undo_max_steps", 50),
        }
        self._saved_cfg = cfg
        save_render_settings(cfg)
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_undo_memory_limit_mb"):
            backend.set_undo_memory_limit_mb(mb)

    def _build_cards(self):
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for profile in self._all_profiles:
            card = ProfileCard(
                profile_data=profile,
                is_selected=(profile.get("id") == self._selected_profile.get("id")),
                is_active=(profile.get("id") == self._active_profile_id)
            )
            card.selected.connect(self._select_profile)
            self._cards.append(card)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _filter_profiles(self, *args):
        cat_filter = self.combo_cat.currentText()
        query = self.search_box.text().strip().lower()

        for card in self._cards:
            p_cat = card.profile_data.get("category", "")
            p_name = card.profile_data.get("name", "").lower()
            p_desc = card.profile_data.get("description", "").lower()

            match_cat = (cat_filter == "Todas as Categorias") or (cat_filter in p_cat)
            match_query = not query or (query in p_name) or (query in p_desc)

            card.setVisible(match_cat and match_query)

    def _select_profile(self, profile_data: dict):
        self._selected_profile = profile_data
        pid = profile_data.get("id", 0)

        for card in self._cards:
            card.is_selected = (card.profile_data.get("id") == pid)
            card.update_style()

        cat = profile_data.get("category", "")
        self.lbl_insp_title.setText(profile_data.get("name", "Perfil"))
        self.lbl_insp_cat.setText(cat.upper())
        self.lbl_insp_desc.setText(profile_data.get("description", ""))

        # Ícone vetorial dinâmico
        if "Digital" in cat:
            self.lbl_insp_icon.setIcon(get_icon("display"))
        elif "Impressão" in cat:
            self.lbl_insp_icon.setIcon(get_icon("printer"))
        elif "Acessibilidade" in cat:
            self.lbl_insp_icon.setIcon(get_icon("eye"))
        else:
            self.lbl_insp_icon.setIcon(get_icon("color_wheel"))

        self.preview_bar.set_profile(pid)

        if pid == self._active_profile_id:
            self.btn_apply.setText("Modo de Cor Ativo")
            self.btn_apply.setEnabled(False)
        else:
            self.btn_apply.setText("Aplicar como Modo Ativo")
            self.btn_apply.setEnabled(True)

    def _on_apply_profile(self):
        pid = self._selected_profile.get("id", 0)
        self._active_profile_id = pid

        cfg = {
            "profile_id": pid,
            "low_latency": self.switch_lat.isChecked(),
            "linear_gamma": self.switch_gam.isChecked(),
            "deep_color": self.switch_deep.isChecked(),
        }
        self._saved_cfg = cfg
        save_render_settings(cfg)

        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_color_profile"):
            backend.set_color_profile(pid)

        for card in self._cards:
            card.set_active_state(card.profile_data.get("id") == pid)

        self._select_profile(self._selected_profile)
        self.profileChanged.emit(pid)

    def _apply_theme(self, *args):
        tm = ThemeManager.instance()
        bg_app = tm.get_color("bg_main")
        bg_panel = tm.get_color("bg_panel")
        bg_card = tm.get_color("bg_card")
        border = tm.get_color("border")
        border_muted = tm.get_color("border_muted")
        text_main = tm.get_color("text_main")
        text_sec = tm.get_color("text_sec")
        accent = tm.get_color("accent")
        accent_hover = tm.get_color("accent_hover")

        if hasattr(self, "root_container") and self.root_container:
            self.root_container.setStyleSheet(f"""
                QWidget#DialogRootContainer {{
                    background-color: {bg_app};
                    border: 1px solid {border};
                    border-radius: 10px;
                }}
                QFrame#DialogHeaderSep {{
                    background-color: {border};
                    border: none;
                }}
            """)

        self.setStyleSheet(f"""
            QGroupBox {{
                font-size: 11px;
                font-weight: bold;
                color: {text_sec};
                border: 1px solid {border};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 14px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }}
            QLineEdit, QComboBox {{
                background-color: {bg_card};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg_card};
                color: {text_main};
                selection-background-color: {accent};
                selection-color: #ffffff;
                border: 1px solid {border};
            }}
            QPushButton {{
                background-color: {bg_card};
                color: {text_main};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: #ffffff;
            }}
            QPushButton:disabled {{
                background-color: {bg_panel};
                color: {text_sec};
                border-color: {border_muted};
            }}
        """)
        if hasattr(self, "lbl_insp_icon") and self.lbl_insp_icon:
            self.lbl_insp_icon.setStyleSheet(f"border: 1px solid {border}; background: {bg_card}; border-radius: 8px;")

        self.btn_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            QPushButton:disabled {{
                background-color: {bg_panel};
                color: {text_sec};
                border: 1px solid {border_muted};
            }}
        """)
