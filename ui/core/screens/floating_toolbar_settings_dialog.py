"""
FloatingToolbarSettingsDialog — Central de Configurações da Barra Rápida Flutuante (Lumenia V2)
================================================================================================
Interface moderna de 2 colunas no padrão Lumenia V2:
  - Coluna da Esquerda: Catálogo de ferramentas com switches individuais, atalhos e busca.
  - Coluna da Direita: Preview interativo da toolbar em tempo real, velocidade de recolhimento e docking magnético.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from ui.core.tools import TOOL_META, DEFAULT_TOOLS

_SETTINGS_ORG = "Lumenia"
_SETTINGS_APP = "LumeniaApp"


# ── SWITCH ANIMADO ESTILO LUMENIA V2 ─────────────────────────────────────────

class ModernToggle(QtWidgets.QCheckBox):
    """Switch animado estilo iOS / Lumenia V2."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedSize(44, 22)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        checked = self.isChecked()
        track_color = QtGui.QColor("#ff5252") if checked else QtGui.QColor("#404040")
        thumb_color = QtGui.QColor("#ffffff")

        # Track
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QBrush(track_color))
        p.drawRoundedRect(0, 2, 42, 18, 9, 9)

        # Thumb
        p.setBrush(QtGui.QBrush(thumb_color))
        thumb_x = 24 if checked else 2
        p.drawEllipse(thumb_x, 1, 18, 18)
        p.end()


# ── PREVIEW VISUAL DA TOOLBAR ────────────────────────────────────────────────

class ToolbarLivePreview(QtWidgets.QFrame):
    """Miniatura gráfica da toolbar atualizando os botões ativos em tempo real."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(54)
        self._active_tools: List[str] = []
        self._build_ui()

    def _build_ui(self):
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(8, 4, 8, 4)
        self.layout.setSpacing(6)
        self.layout.setAlignment(QtCore.Qt.AlignCenter)

    def set_tools(self, tool_ids: List[str]):
        self._active_tools = list(tool_ids)
        # Limpa layout
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Handle de arraste
        handle = QtWidgets.QLabel("⋮⋮")
        handle.setStyleSheet("color: #71717a; font-size: 13px; font-weight: bold; margin-right: 4px;")
        self.layout.addWidget(handle)

        for tid in self._active_tools:
            meta = TOOL_META.get(tid, {})
            icon_key = meta.get("icon", "brush")
            btn = QtWidgets.QLabel()
            btn.setFixedSize(28, 28)
            btn.setAlignment(QtCore.Qt.AlignCenter)
            btn.setStyleSheet("background: rgba(255,255,255,0.08); border-radius: 6px;")
            icon = get_icon(icon_key, color="#ffffff")
            if icon and not icon.isNull():
                btn.setPixmap(icon.pixmap(16, 16))
            self.layout.addWidget(btn)

        self.update_style()

    def update_style(self):
        is_dark = getattr(ThemeManager.instance(), "is_dark", True)
        bg = "#1f1f23" if is_dark else "#f1f5f9"
        border = "#3f3f46" if is_dark else "#cbd5e1"
        self.setStyleSheet(f"""
            ToolbarLivePreview {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
        """)


# ── CARTÃO DA FERRAMENTA (COLUNA ESQUERDA) ───────────────────────────────────

class ToolToggleCard(QtWidgets.QFrame):
    """Cartão individual de ferramenta com switch liga/desliga."""

    toggled = QtCore.Signal(str, bool)  # tool_id, is_active

    def __init__(self, tool_id: str, is_active: bool = True, parent=None):
        super().__init__(parent)
        self.tool_id = tool_id
        self.is_active = is_active
        self.meta = TOOL_META.get(tool_id, {"name": tool_id.capitalize(), "icon": "brush"})

        self._build_ui()
        self.update_style()

    def _build_ui(self):
        self.setFixedHeight(56)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # Ícone
        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setFixedSize(32, 32)
        self.icon_label.setAlignment(QtCore.Qt.AlignCenter)
        self.icon_label.setStyleSheet("background: rgba(255,255,255,0.06); border-radius: 6px;")
        icon = get_icon(self.meta.get("icon", "brush"), color="#ffffff")
        if icon and not icon.isNull():
            self.icon_label.setPixmap(icon.pixmap(18, 18))
        layout.addWidget(self.icon_label)

        # Nome
        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setAlignment(QtCore.Qt.AlignVCenter)

        self.name_label = QtWidgets.QLabel(self.meta.get("name", "Ferramenta"))
        self.name_label.setStyleSheet("font-size: 12px; font-weight: bold;")

        shortcuts_map = {
            "brush": "B", "eraser": "E", "bucket": "G", "eyedrop": "I / Alt",
            "wand": "W", "transform": "Ctrl+T", "rect_select": "M", "ellipse_select": "Shift+M",
            "lasso": "L", "smudge": "R"
        }
        key_text = f"Atalho: {shortcuts_map.get(self.tool_id, '-')}"
        self.sub_label = QtWidgets.QLabel(key_text)
        self.sub_label.setStyleSheet("font-size: 10px; color: #888888;")

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.sub_label)
        layout.addLayout(text_layout)
        layout.addStretch()

        # Switch
        self.switch = ModernToggle()
        self.switch.setChecked(self.is_active)
        self.switch.toggled.connect(self._on_toggled)
        layout.addWidget(self.switch)

    def _on_toggled(self, checked: bool):
        self.is_active = checked
        self.toggled.emit(self.tool_id, checked)

    def set_checked(self, checked: bool):
        self.switch.blockSignals(True)
        self.switch.setChecked(checked)
        self.is_active = checked
        self.switch.blockSignals(False)

    def update_style(self):
        is_dark = getattr(ThemeManager.instance(), "is_dark", True)
        bg = "#1e1e1e" if is_dark else "#ffffff"
        border = "#2e2e2e" if is_dark else "#e0e0e0"
        text_color = "#ffffff" if is_dark else "#1a202c"

        self.setStyleSheet(f"""
            ToolToggleCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)


# ── DIÁLOGO PRINCIPAL (2 COLUNAS) ───────────────────────────────────────────

def load_floating_toolbar_settings() -> dict:
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    tools = s.value("floating_toolbar/tools", DEFAULT_TOOLS)
    if isinstance(tools, str):
        tools = [t.strip() for t in tools.split(",") if t.strip()]
    elif not isinstance(tools, list):
        tools = list(DEFAULT_TOOLS)

    return {
        "active": s.value("floating_toolbar/active", True, type=bool),
        "speed": s.value("floating_toolbar/speed", "Rápido", type=str),
        "tools": list(tools),
    }


def save_floating_toolbar_settings(cfg: dict) -> None:
    s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
    s.setValue("floating_toolbar/active", cfg["active"])
    s.setValue("floating_toolbar/speed", cfg["speed"])
    s.setValue("floating_toolbar/tools", cfg["tools"])


class FloatingToolbarSettingsDialog(QtWidgets.QDialog):
    """Central de Configuração da Barra Flutuante em 2 colunas."""

    settings_applied = QtCore.Signal(dict)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Configurações da Barra Rápida Flutuante")
        self.setFixedSize(820, 560)
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self._cards: Dict[str, ToolToggleCard] = {}
        self._cfg = load_floating_toolbar_settings()

        self._setup_ui()
        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

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

        # Header da lista com contador
        self.lbl_count = QtWidgets.QLabel("Ferramentas Visíveis:")
        self.lbl_count.setStyleSheet("font-size: 12px; font-weight: bold;")
        left_layout.addWidget(self.lbl_count)

        # Busca
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("🔍 Filtrar ferramentas...")
        self.search_box.textChanged.connect(self._filter_tools)
        left_layout.addWidget(self.search_box)

        # ScrollArea com lista de cards
        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QtWidgets.QFrame.NoFrame)

        self.cards_container = QtWidgets.QWidget()
        self.cards_layout = QtWidgets.QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 4, 0)
        self.cards_layout.setSpacing(6)

        active_set = set(self._cfg.get("tools", []))
        for tid in DEFAULT_TOOLS:
            is_act = tid in active_set
            card = ToolToggleCard(tid, is_active=is_act)
            card.toggled.connect(self._on_tool_toggled)
            self._cards[tid] = card
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
        self.scroll_area.setWidget(self.cards_container)
        left_layout.addWidget(self.scroll_area)

        # Botões de seleção rápida
        quick_box = QtWidgets.QHBoxLayout()
        btn_all = QtWidgets.QPushButton("Todas")
        btn_all.clicked.connect(self._select_all_tools)
        btn_none = QtWidgets.QPushButton("Nenhuma")
        btn_none.clicked.connect(self._deselect_all_tools)
        quick_box.addWidget(btn_all)
        quick_box.addWidget(btn_none)
        left_layout.addLayout(quick_box)

        main_layout.addWidget(left_col)

        # ── COLUNA DA DIREITA (INSPECTOR & COMPORTAMENTO) ───────────────────
        right_col = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_col)
        right_layout.setContentsMargins(12, 4, 4, 4)
        right_layout.setSpacing(14)

        # Header
        header_box = QtWidgets.QHBoxLayout()
        icon_lbl = QtWidgets.QLabel("🪄")
        icon_lbl.setFixedSize(44, 44)
        icon_lbl.setAlignment(QtCore.Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 22px; background: rgba(255,255,255,0.08); border-radius: 8px;")
        header_box.addWidget(icon_lbl)

        title_box = QtWidgets.QVBoxLayout()
        title_box.setSpacing(2)
        lbl_title = QtWidgets.QLabel("Barra de Ferramentas Flutuante")
        f = lbl_title.font()
        f.setPointSize(13)
        f.setBold(True)
        lbl_title.setFont(f)

        lbl_sub = QtWidgets.QLabel("ENCAIXE MAGNÉTICO & ACESSO RÁPIDO")
        lbl_sub.setStyleSheet("color: #ff5252; font-size: 11px; font-weight: bold;")

        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_box.addLayout(title_box)
        header_box.addStretch()
        right_layout.addLayout(header_box)

        # Descrição
        lbl_desc = QtWidgets.QLabel(
            "A barra flutuante oferece acesso imediato às ferramentas essenciais sem obstruir a tela. "
            "Ao aproximar das bordas do canvas, ela se acopla magneticamente com animação suave."
        )
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("font-size: 12px; color: #a0aec0; line-height: 1.4;")
        right_layout.addWidget(lbl_desc)

        # Preview Interativo da Toolbar
        lbl_prev = QtWidgets.QLabel("Pré-visualização da Barra em Tempo Real:")
        lbl_prev.setStyleSheet("font-size: 11px; font-weight: bold; color: #cbd5e1; margin-top: 4px;")
        right_layout.addWidget(lbl_prev)

        self.toolbar_preview = ToolbarLivePreview()
        right_layout.addWidget(self.toolbar_preview)

        # Grupo de Comportamento & Física
        group_physics = QtWidgets.QGroupBox("Comportamento, Velocidade & Acoplamento")
        physics_layout = QtWidgets.QVBoxLayout(group_physics)
        physics_layout.setContentsMargins(14, 14, 14, 14)
        physics_layout.setSpacing(12)

        # 1. Master Switch
        row_master = QtWidgets.QHBoxLayout()
        lbl_m = QtWidgets.QLabel("Ativar Barra Flutuante no Canvas:")
        lbl_m.setStyleSheet("font-size: 12px; font-weight: bold;")
        self.switch_master = ModernToggle()
        self.switch_master.setChecked(self._cfg.get("active", True))
        self.switch_master.toggled.connect(self._on_master_toggled)
        row_master.addWidget(lbl_m)
        row_master.addStretch()
        row_master.addWidget(self.switch_master)
        physics_layout.addLayout(row_master)

        # 2. Velocidade de Recolhimento
        row_spd = QtWidgets.QHBoxLayout()
        lbl_s = QtWidgets.QLabel("Velocidade de Auto-Recolhimento:")
        lbl_s.setStyleSheet("font-size: 12px;")
        self.combo_speed = QtWidgets.QComboBox()
        self.combo_speed.addItems(["Desativado (Sempre Visível)", "Lento (500ms)", "Rápido (200ms)", "Ultra Rápido (80ms)"])
        cur_speed = self._cfg.get("speed", "Rápido")
        for i in range(self.combo_speed.count()):
            if cur_speed in self.combo_speed.itemText(i):
                self.combo_speed.setCurrentIndex(i)
                break
        row_spd.addWidget(lbl_s)
        row_spd.addStretch()
        row_spd.addWidget(self.combo_speed)
        physics_layout.addLayout(row_spd)

        # 3. Orientação e Dock Magnético
        row_dock = QtWidgets.QHBoxLayout()
        lbl_d = QtWidgets.QLabel("Sensibilidade do Encaixe Magnético (Snap):")
        lbl_d.setStyleSheet("font-size: 12px;")
        self.combo_snap = QtWidgets.QComboBox()
        self.combo_snap.addItems(["Sensível (50px)", "Moderado (35px)", "Desativado"])
        row_dock.addWidget(lbl_d)
        row_dock.addStretch()
        row_dock.addWidget(self.combo_snap)
        physics_layout.addLayout(row_dock)

        right_layout.addWidget(group_physics)
        right_layout.addStretch()

        # Botões de Ação
        btn_box = QtWidgets.QHBoxLayout()
        self.btn_apply = QtWidgets.QPushButton("✓ Aplicar Configurações")
        self.btn_apply.setFixedHeight(34)
        self.btn_apply.clicked.connect(self._on_apply)
        btn_box.addWidget(self.btn_apply)

        btn_box.addSpacing(8)

        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        right_layout.addLayout(btn_box)
        main_layout.addWidget(right_col)

        self._update_preview()
        self._update_counter()

    def _on_tool_toggled(self, tool_id: str, is_active: bool):
        self._update_preview()
        self._update_counter()

    def _on_master_toggled(self, is_active: bool):
        self.combo_speed.setEnabled(is_active)
        self.combo_snap.setEnabled(is_active)
        self.scroll_area.setEnabled(is_active)

    def _select_all_tools(self):
        for card in self._cards.values():
            card.set_checked(True)
        self._update_preview()
        self._update_counter()

    def _deselect_all_tools(self):
        for card in self._cards.values():
            card.set_checked(False)
        self._update_preview()
        self._update_counter()

    def _filter_tools(self):
        query = self.search_box.text().strip().lower()
        for tid, card in self._cards.items():
            name = card.meta.get("name", "").lower()
            card.setVisible(not query or query in name or query in tid)

    def _get_active_tool_ids(self) -> List[str]:
        return [tid for tid, card in self._cards.items() if card.is_active]

    def _update_preview(self):
        active_tools = self._get_active_tool_ids()
        self.toolbar_preview.set_tools(active_tools)

    def _update_counter(self):
        active_tools = self._get_active_tool_ids()
        total = len(self._cards)
        self.lbl_count.setText(f"Ferramentas Visíveis ({len(active_tools)} de {total}):")

    def _on_apply(self):
        speed_raw = self.combo_speed.currentText().split()[0]
        if "Desativado" in speed_raw:
            speed_raw = "Desativado"

        cfg = {
            "active": self.switch_master.isChecked(),
            "speed": speed_raw,
            "tools": self._get_active_tool_ids(),
        }
        save_floating_toolbar_settings(cfg)
        self.settings_applied.emit(cfg)

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
