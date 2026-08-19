"""
RenderSettingsDialog — Central de Renderização, Perfis de Cor & Prova de Impressão (Lumenia V2)
================================================================================================
Interface moderna de 2 colunas no padrão Lumenia V2 (inspirada no PluginsWindow e FilterDialog):
  - Coluna da Esquerda: Categorias (Digital RGB, Impressão CMYK, Daltonismo, Motor), busca e cards de perfis.
  - Coluna da Direita: Inspector detalhado com especificações técnicas, controle de renderização (Baixa Latência,
    Gama Linear, Deep Color 64-bit) e faixa de pré-visualização de gamut / prova de cores em tempo real.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.engine.registry import EngineRegistry


# ── SWITCH ESTILO LUMENIA V2 / INFINITE PAINTER ──────────────────────────────

class ModernToggleSwitch(QtWidgets.QCheckBox):
    """Switch animado estilo iOS / Infinite Painter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedSize(46, 24)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        checked = self.isChecked()
        track_color = QtGui.QColor("#ff5252") if checked else QtGui.QColor("#404040")
        thumb_color = QtGui.QColor("#ffffff")

        # Track
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QBrush(track_color))
        p.drawRoundedRect(0, 2, 44, 20, 10, 10)

        # Thumb
        p.setBrush(QtGui.QBrush(thumb_color))
        thumb_x = 24 if checked else 2
        p.drawEllipse(thumb_x, 1, 20, 20)
        p.end()


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

        # Transforma os pixels via backend nativo se perfil ativo for diferente de sRGB
        backend = EngineRegistry.instance().get_backend()
        if self._profile_id != 0 and backend and hasattr(backend, "_native") and backend._native:
            try:
                ptr = img.bits()
                backend._native.ColorProfileManager.transform_buffer(
                    ptr, ptr, w * h, self._profile_id
                )
            except Exception:
                pass

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

    def _build_ui(self):
        self.setFixedHeight(64)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Ícone de categoria
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(32, 32)
        cat = self.profile_data.get("category", "")
        icon_char = "🖥" if "Digital" in cat else ("🖨" if "Impressão" in cat else ("👁" if "Acessibilidade" in cat else "◐"))
        self.icon_label.setText(icon_char)
        self.icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 16px; background-color: rgba(255,255,255,0.06); border-radius: 6px;")
        layout.addWidget(self.icon_label)

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
        is_dark = getattr(ThemeManager.instance(), "is_dark", True)
        if self.is_selected:
            bg = "#2a3441" if is_dark else "#e2e8f0"
            border = "#ff5252"
        else:
            bg = "#1e1e1e" if is_dark else "#ffffff"
            border = "#2e2e2e" if is_dark else "#e0e0e0"

        text_color = "#ffffff" if is_dark else "#1a202c"

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


# ── DIÁLOGO PRINCIPAL (2 COLUNAS) ───────────────────────────────────────────

class RenderSettingsDialog(QtWidgets.QDialog):
    """Central de Renderização e Prova de Cores em 2 colunas."""

    profileChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações de Renderização & Modos de Cor")
        self.setFixedSize(820, 560)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self._all_profiles: List[dict] = []
        self._cards: List[ProfileCard] = []
        self._selected_profile: dict = {}
        self._active_profile_id: int = 0

        self._load_data()
        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

    def _load_data(self):
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_available_color_profiles"):
            self._all_profiles = backend.get_available_color_profiles()
        else:
            self._all_profiles = [
                {"id": 0, "name": "Padrão (sRGB)", "category": "Digital (RGB)", "description": "Espaço de cor universal padrão para telas"}
            ]

        if backend and hasattr(backend, "get_color_profile"):
            self._active_profile_id = backend.get_color_profile()
        else:
            self._active_profile_id = 0

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

        # ── COLUNA DA ESQUERDA (320px) ──────────────────────────────────────
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
            "Escala de Cinza",
            "Acessibilidade"
        ])
        self.combo_cat.currentIndexChanged.connect(self._filter_profiles)
        left_layout.addWidget(self.combo_cat)

        # Campo de busca
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("🔍 Buscar perfil de cor...")
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
        self.lbl_insp_icon = QtWidgets.QLabel("🖥")
        self.lbl_insp_icon.setFixedSize(44, 44)
        self.lbl_insp_icon.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_insp_icon.setStyleSheet("font-size: 22px; background: rgba(255,255,255,0.08); border-radius: 8px;")
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
        lbl_bar.setStyleSheet("font-size: 11px; font-weight: bold; color: #cbd5e1; margin-top: 4px;")
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
        self.switch_lat = ModernToggleSwitch()
        self.switch_lat.setChecked(True)
        row_lat.addWidget(lbl_lat_title)
        row_lat.addStretch()
        row_lat.addWidget(self.switch_lat)
        engine_layout.addLayout(row_lat)

        # 2. Correção Gama
        row_gam = QtWidgets.QHBoxLayout()
        lbl_gam_title = QtWidgets.QLabel("Correção Gama Linear (sRGB Physical Blending)")
        lbl_gam_title.setToolTip("Composição física no espaço linear eliminando bordas escuras")
        self.switch_gam = ModernToggleSwitch()
        self.switch_gam.setChecked(False)
        row_gam.addWidget(lbl_gam_title)
        row_gam.addStretch()
        row_gam.addWidget(self.switch_gam)
        engine_layout.addLayout(row_gam)

        # 3. Deep Color
        row_deep = QtWidgets.QHBoxLayout()
        lbl_deep_title = QtWidgets.QLabel("Deep Color 64-bit (Half-Float RGBA16F Precision)")
        lbl_deep_title.setToolTip("Elimina 100% de banding em gradientes suaves e aquarelas")
        self.switch_deep = ModernToggleSwitch()
        self.switch_deep.setChecked(True)
        row_deep.addWidget(lbl_deep_title)
        row_deep.addStretch()
        row_deep.addWidget(self.switch_deep)
        engine_layout.addLayout(row_deep)

        right_layout.addWidget(engine_group)
        right_layout.addStretch()

        # Botões de Ação na base
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("✓ Aplicar como Modo Ativo")
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

    def _build_cards(self):
        # Limpa cards existentes
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()

        # Remove itens do layout
        while self.cards_layout.count() > 1:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for prof in self._all_profiles:
            is_sel = (prof.get("id") == self._selected_profile.get("id"))
            is_act = (prof.get("id") == self._active_profile_id)
            card = ProfileCard(prof, is_selected=is_sel, is_active=is_act)
            card.selected.connect(self._select_profile)
            self._cards.append(card)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

    def _filter_profiles(self):
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

        # Atualiza seleção visual dos cards
        for card in self._cards:
            card.is_selected = (card.profile_data.get("id") == pid)
            card.update_style()

        # Atualiza Inspector
        cat = profile_data.get("category", "")
        self.lbl_insp_title.setText(profile_data.get("name", "Perfil"))
        self.lbl_insp_cat.setText(cat.upper())
        self.lbl_insp_desc.setText(profile_data.get("description", ""))

        icon_char = "🖥" if "Digital" in cat else ("🖨" if "Impressão" in cat else ("👁" if "Acessibilidade" in cat else "◐"))
        self.lbl_insp_icon.setText(icon_char)

        # Atualiza preview bar
        self.preview_bar.set_profile(pid)

        # Atualiza botão
        if pid == self._active_profile_id:
            self.btn_apply.setText("✓ Modo de Cor Ativo")
            self.btn_apply.setEnabled(False)
        else:
            self.btn_apply.setText("✓ Aplicar como Modo Ativo")
            self.btn_apply.setEnabled(True)

    def _on_apply_profile(self):
        pid = self._selected_profile.get("id", 0)
        self._active_profile_id = pid

        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_color_profile"):
            backend.set_color_profile(pid)

        for card in self._cards:
            card.set_active_state(card.profile_data.get("id") == pid)

        self._select_profile(self._selected_profile)
        self.profileChanged.emit(pid)

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
