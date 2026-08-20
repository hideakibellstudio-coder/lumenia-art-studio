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


# ── FAIXA DE PRÉ-VISUALIZAÇÃO DE PROVA DE COR (PROOFING SPECTRUM BAR) ─────────

class ProofingPreviewBar(QtWidgets.QWidget):
    """Renderiza uma barra de degradê espectral comparativa simulando o perfil ativo em tempo real."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self._profile_id = 0

    def set_profile(self, profile_id: int):
        self._profile_id = profile_id
        self.update()

    def paintEvent(self, event):
        from ui.core.engine.color_profile import ColorProfileEngine

        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        w = rect.width()
        h = rect.height()

        if w <= 0 or h <= 0:
            return

        # Fundo arredondado
        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        p.setClipPath(path)

        # Cria gradiente espectral padrão
        grad = QtGui.QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.00, QtGui.QColor("#ff0000"))
        grad.setColorAt(0.17, QtGui.QColor("#ffff00"))
        grad.setColorAt(0.33, QtGui.QColor("#00ff00"))
        grad.setColorAt(0.50, QtGui.QColor("#00ffff"))
        grad.setColorAt(0.67, QtGui.QColor("#0000ff"))
        grad.setColorAt(0.83, QtGui.QColor("#ff00ff"))
        grad.setColorAt(1.00, QtGui.QColor("#ffffff"))

        # Renderiza em imagem temporária para aplicar transformação do perfil
        img = QtGui.QImage(w, h, QtGui.QImage.Format_RGBA8888)
        img_painter = QtGui.QPainter(img)
        img_painter.fillRect(0, 0, w, h, QtGui.QBrush(grad))
        img_painter.end()

        # Aplica a transformação vetorizada em tempo real
        if self._profile_id != 0:
            img = ColorProfileEngine.transform_qimage(img, self._profile_id)

        p.drawImage(0, 0, img)
        p.setClipping(False)

        # Borda sutil
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 30), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect, 6, 6)
        p.end()


# ── CARTÃO DO PERFIL (COLUNA ESQUERDA) ───────────────────────────────────────

class ProfileCard(QtWidgets.QFrame):
    """Cartão individual representando um perfil de cor na lista."""

    selected = QtCore.Signal(dict)

    def __init__(self, profile_data: dict, is_selected: bool = False, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.profile_data = profile_data
        self.is_selected = is_selected
        self.is_active = is_active
        self.setCursor(QtCore.Qt.PointingHandCursor)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self.update_style)
        self.update_style()

    def _get_category_icon_name(self, cat: str) -> str:
        if "Digital" in cat:
            return "display"
        elif "Impressão" in cat:
            return "printer"
        elif "Acessibilidade" in cat:
            return "eye"
        return "color_wheel"

    def _build_ui(self):
        self.setFixedHeight(64)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Ícone de categoria vetorial
        cat = self.profile_data.get("category", "")
        self.icon_btn = QtWidgets.QToolButton()
        self.icon_btn.setFixedSize(32, 32)
        self.icon_btn.setIconSize(QtCore.QSize(18, 18))
        self.icon_btn.setIcon(get_icon(self._get_category_icon_name(cat)))
        self.icon_btn.setStyleSheet("border: none; background-color: rgba(255,255,255,0.06); border-radius: 6px;")
        layout.addWidget(self.icon_btn)

        # Textos
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setAlignment(QtCore.Qt.AlignVCenter)

        self.name_label = QtWidgets.QLabel(self.profile_data.get("name", "Perfil"))
        self.name_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        self.cat_label = QtWidgets.QLabel(f"{cat}")
        self.cat_label.setStyleSheet("font-size: 10px; color: #888888;")

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.cat_label)
        layout.addLayout(text_layout)
        layout.addStretch()

        # Tag de ativo
        self.badge_label = QtWidgets.QLabel("ATIVO" if self.is_active else "")
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 2px 6px; border-radius: 4px;" if self.is_active else "color: transparent;"
        )
        layout.addWidget(self.badge_label)

    def set_active_state(self, is_active: bool):
        self.is_active = is_active
        self.badge_label.setText("ATIVO" if is_active else "")
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 2px 6px; border-radius: 4px;" if is_active else "color: transparent;"
        )

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.profile_data)

    def update_style(self):
        tm = ThemeManager.instance()
        if self.is_selected:
            bg = tm.get_color("bg_card_hover")
            border = tm.get_color("accent")
        else:
            bg = tm.get_color("bg_card")
            border = tm.get_color("border")

        text_color = tm.get_color("text_main")

        self.setStyleSheet(f"""
            ProfileCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)


_SETTINGS_ORG = "Lumenia"
_SETTINGS_APP = "LumeniaApp"


def load_render_settings() -> dict:
    """Carrega as configurações salvas de renderização e perfil de cor."""
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.beginGroup("RenderSettings")
    profile_id = s.value("profile_id", 0, type=int)
    low_latency = s.value("low_latency", True, type=bool)
    linear_gamma = s.value("linear_gamma", False, type=bool)
    deep_color = s.value("deep_color", True, type=bool)
    s.endGroup()
    return {
        "profile_id": profile_id,
        "low_latency": low_latency,
        "linear_gamma": linear_gamma,
        "deep_color": deep_color,
    }


def save_render_settings(cfg: dict) -> None:
    """Salva as configurações de renderização e perfil de cor no QSettings."""
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.beginGroup("RenderSettings")
    s.setValue("profile_id", int(cfg.get("profile_id", 0)))
    s.setValue("low_latency", bool(cfg.get("low_latency", True)))
    s.setValue("linear_gamma", bool(cfg.get("linear_gamma", False)))
    s.setValue("deep_color", bool(cfg.get("deep_color", True)))
    s.endGroup()


# ── DIÁLOGO PRINCIPAL (2 COLUNAS) ───────────────────────────────────────────

class RenderSettingsDialog(QtWidgets.QDialog):
    """Central de Renderização e Prova de Cores em 2 colunas."""

    profileChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RenderSettingsDialog")
        self.setWindowTitle("Configurações de Renderização & Modos de Cor")
        self.setFixedSize(820, 560)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

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
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

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

        main_layout.addWidget(left_col)

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
        main_layout.addWidget(right_col)

        self._build_cards()
        self._select_profile(self._selected_profile)

    def _save_switch_settings(self, *args):
        """Salva o estado atual dos switches no QSettings."""
        cfg = {
            "profile_id": self._active_profile_id,
            "low_latency": self.switch_lat.isChecked(),
            "linear_gamma": self.switch_gam.isChecked(),
            "deep_color": self.switch_deep.isChecked(),
        }
        self._saved_cfg = cfg
        save_render_settings(cfg)

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
