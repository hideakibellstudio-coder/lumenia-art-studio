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
from .render_settings_components import ProofingPreviewBar, ProfileCard



def load_render_settings() -> dict:
    """Carrega as configurações salvas de renderização e perfil de cor."""
    s = QtCore.QSettings("Lumenia", "LumeniaArtStudio")
    return {
        "profile_id": s.value("render/profile_id", 0, type=int),
        "low_latency": s.value("render/low_latency", True, type=bool),
        "linear_gamma": s.value("render/linear_gamma", False, type=bool),
        "deep_color": s.value("render/deep_color", True, type=bool),
        "undo_limit_mb": s.value("render/undo_limit_mb", 256, type=int),
        "undo_max_steps": s.value("render/undo_max_steps", 50, type=int),
    }


def save_render_settings(cfg_dict: dict) -> None:
    """Salva as configurações de renderização e perfil de cor no QSettings."""
    s = QtCore.QSettings("Lumenia", "LumeniaArtStudio")
    s.setValue("render/profile_id", int(cfg_dict.get("profile_id", 0)))
    s.setValue("render/low_latency", bool(cfg_dict.get("low_latency", True)))
    s.setValue("render/linear_gamma", bool(cfg_dict.get("linear_gamma", False)))
    s.setValue("render/deep_color", bool(cfg_dict.get("deep_color", True)))
    s.setValue("render/undo_limit_mb", int(cfg_dict.get("undo_limit_mb", 256)))
    s.setValue("render/undo_max_steps", int(cfg_dict.get("undo_max_steps", 50)))


# ── DIÁLOGO PRINCIPAL (2 COLUNAS) ───────────────────────────────────────────

class RenderSettingsDialog(BaseFramelessDialog):
    """Central de Renderização e Prova de Cores em 2 colunas."""

    profileChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(title="Configurações de Renderização & Modos de Cor", icon_name="settings", parent=parent, modal=True)
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
        font = self.lbl_insp_title.font()
        font.setPointSize(13)
        font.setBold(True)
        self.lbl_insp_title.setFont(font)

        self.lbl_insp_cat = QtWidgets.QLabel("Digital (RGB)")
        self.lbl_insp_cat.setStyleSheet("color: #ff5252; font-size: 11px; font-weight: bold;")

        title_box.addWidget(self.lbl_insp_title)
        title_box.addWidget(self.lbl_insp_cat)
        header_box.addLayout(title_box)
        header_box.addStretch()
        right_layout.addLayout(header_box)

        # Descrição do Perfil
        self.lbl_insp_desc = QtWidgets.QLabel("")
        self.lbl_insp_desc.setWordWrap(True)
        self.lbl_insp_desc.setStyleSheet("font-size: 12px; color: #a0aec0; line-height: 1.4;")
        right_layout.addWidget(self.lbl_insp_desc)

        # Barra de Simulação / Prova de Cores
        lbl_bar = QtWidgets.QLabel("Simulação de Gamut & Prova de Cores (Soft Proofing):")
        lbl_bar.setStyleSheet("font-size: 11px; font-weight: bold; margin-top: 4px;")
        right_layout.addWidget(lbl_bar)

        self.preview_bar = ProofingPreviewBar()
        right_layout.addWidget(self.preview_bar)

        # Grupo de Configurações Avançadas do Motor
        engine_group = QtWidgets.QGroupBox("Pipeline de Renderização & Motor Físico")
        engine_layout = QtWidgets.QVBoxLayout(engine_group)
        engine_layout.setContentsMargins(14, 14, 14, 14)
        engine_layout.setSpacing(10)

        # 1. Baixa Latência
        row_lat = QtWidgets.QHBoxLayout()
        lbl_lat_title = QtWidgets.QLabel("Modo de Baixa Latência (Ultra-Low Latency)")
        lbl_lat_title.setToolTip("Bypass na fila de sincronização para resposta em < 4ms")
        self.switch_lat = ToggleSwitch()
        self.switch_lat.setChecked(self._saved_cfg.get("low_latency", True))
        self.switch_lat.toggled.connect(self._save_switch_settings)
        row_lat.addWidget(lbl_lat_title)
        row_lat.addStretch()
        row_lat.addWidget(self.switch_lat)
        engine_layout.addLayout(row_lat)

        # 2. Correção Gama
        row_gam = QtWidgets.QHBoxLayout()
        lbl_gam_title = QtWidgets.QLabel("Correção Gama Linear (sRGB Physical Blending)")
        lbl_gam_title.setToolTip("Composição física no espaço linear eliminando bordas escuras")
        self.switch_gam = ToggleSwitch()
        self.switch_gam.setChecked(self._saved_cfg.get("linear_gamma", False))
        self.switch_gam.toggled.connect(self._save_switch_settings)
        row_gam.addWidget(lbl_gam_title)
        row_gam.addStretch()
        row_gam.addWidget(self.switch_gam)
        engine_layout.addLayout(row_gam)

        # 3. Deep Color
        row_deep = QtWidgets.QHBoxLayout()
        lbl_deep_title = QtWidgets.QLabel("Deep Color 64-bit (Half-Float RGBA16F Precision)")
        lbl_deep_title.setToolTip("Elimina 100% de banding em gradientes suaves e aquarelas")
        self.switch_deep = ToggleSwitch()
        self.switch_deep.setChecked(self._saved_cfg.get("deep_color", True))
        self.switch_deep.toggled.connect(self._save_switch_settings)
        row_deep.addWidget(lbl_deep_title)
        row_deep.addStretch()
        row_deep.addWidget(self.switch_deep)
        engine_layout.addLayout(row_deep)

        # 4. Histórico de Desfazer / Refazer (Undo/Redo)
        row_undo = QtWidgets.QHBoxLayout()
        lbl_undo = QtWidgets.QLabel("Memória do Histórico (Undo / Redo)")
        lbl_undo.setToolTip("Limite dinâmico de memória RAM alocada para snapshots de tiles desfazer/refazer")
        self.combo_undo = QtWidgets.QComboBox()
        undo_opts = [(128, "128 MB"), (256, "256 MB (Padrão)"), (512, "512 MB"), (1024, "1024 MB (1 GB)"), (2048, "2048 MB (2 GB)"), (4096, "4096 MB (4 GB)")]
        for mb, lbl in undo_opts:
            self.combo_undo.addItem(lbl, mb)
        cur_mb = self._saved_cfg.get("undo_limit_mb", 256)
        idx = self.combo_undo.findData(cur_mb)
        if idx >= 0: self.combo_undo.setCurrentIndex(idx)
        self.combo_undo.currentIndexChanged.connect(self._save_switch_settings)
        row_undo.addWidget(lbl_undo); row_undo.addStretch(); row_undo.addWidget(self.combo_undo)
        engine_layout.addLayout(row_undo)

        right_layout.addWidget(engine_group)
        right_layout.addStretch()

        # Botões de Ação na base
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("Aplicar como Modo Ativo")
        self.btn_apply.setIcon(get_icon("check"))
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self._on_apply_profile)
        btn_box.addWidget(self.btn_apply)

        btn_box.addSpacing(8)

        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        right_layout.addLayout(btn_box)
        cols_layout.addWidget(right_col, 1)

        self._build_cards()
        self._select_profile(self._selected_profile)

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

        self.setStyleSheet(f"""
            QDialog#RenderSettingsDialog {{
                background-color: {bg_app};
                color: {text_main};
            }}
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
