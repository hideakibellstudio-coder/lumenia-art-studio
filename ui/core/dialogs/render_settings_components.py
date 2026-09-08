"""
Components for RenderSettingsDialog (ProofingPreviewBar, ProfileCard, EnginePipelineGroup).
===========================================================================================
Contém os componentes de prova de impressão espectral, cartões de perfis de cor,
painel de configurações do motor de renderização e persistência de preferências de cor.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from ui.core.widgets.toggle.toggle_switch import ToggleSwitch


# ── CARREGAMENTO / PERSISTÊNCIA ──────────────────────────────────────────────

def load_render_settings() -> dict:
    """Carrega as configurações salvas de renderização e perfil de cor do ConfigManager (JSON)."""
    from ui.core.config import ConfigManager
    sec = ConfigManager.instance().get_section("render")
    return {
        "profile_id": int(sec.get("profile_id", 0)) if isinstance(sec.get("profile_id"), (int, float)) else 0,
        "low_latency": bool(sec.get("low_latency", True)),
        "linear_gamma": bool(sec.get("linear_gamma", False)),
        "deep_color": bool(sec.get("deep_color", True)),
        "undo_limit_mb": int(sec.get("undo_limit_mb", 256)),
        "undo_max_steps": int(sec.get("undo_max_steps", 50)),
    }


def save_render_settings(cfg_dict: dict) -> None:
    """Salva as configurações de renderização e perfil de cor no ConfigManager (JSON)."""
    from ui.core.config import ConfigManager
    ConfigManager.instance().set_section("render", cfg_dict)


# ── COMPONENTES VISUAIS ──────────────────────────────────────────────────────

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
        w, h = rect.width(), rect.height()

        if w <= 0 or h <= 0:
            return

        path = QtGui.QPainterPath()
        path.addRoundedRect(rect, 6, 6)
        p.setClipPath(path)

        grad = QtGui.QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.00, QtGui.QColor("#ff0000"))
        grad.setColorAt(0.17, QtGui.QColor("#ffff00"))
        grad.setColorAt(0.33, QtGui.QColor("#00ff00"))
        grad.setColorAt(0.50, QtGui.QColor("#00ffff"))
        grad.setColorAt(0.67, QtGui.QColor("#0000ff"))
        grad.setColorAt(0.83, QtGui.QColor("#ff00ff"))
        grad.setColorAt(1.00, QtGui.QColor("#ffffff"))

        img = QtGui.QImage(w, h, QtGui.QImage.Format_RGBA8888)
        img_painter = QtGui.QPainter(img)
        img_painter.fillRect(0, 0, w, h, QtGui.QBrush(grad))
        img_painter.end()

        if self._profile_id != 0:
            img = ColorProfileEngine.transform_qimage(img, self._profile_id)

        p.drawImage(0, 0, img)
        p.setClipping(False)

        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 30), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(rect, 6, 6)
        p.end()


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

        cat = self.profile_data.get("category", "")
        self.icon_btn = QtWidgets.QToolButton()
        self.icon_btn.setFixedSize(32, 32)
        self.icon_btn.setIconSize(QtCore.QSize(18, 18))
        self.icon_btn.setIcon(get_icon(self._get_category_icon_name(cat)))
        self.icon_btn.setStyleSheet("border: none; background-color: rgba(255,255,255,0.06); border-radius: 6px;")
        layout.addWidget(self.icon_btn)

        text_layout = QtWidgets.QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setAlignment(QtCore.Qt.AlignVCenter)

        self.name_label = QtWidgets.QLabel(self.profile_data.get("name", "Perfil"))
        self.name_label.setProperty("heading", "true")

        self.cat_label = QtWidgets.QLabel(f"{cat}")
        self.cat_label.setProperty("muted", "true")

        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.cat_label)
        layout.addLayout(text_layout)
        layout.addStretch()

        from ui.core.i18n import tr, I18nManager
        badge_text = tr("render.badge_active", "ATIVO") if self.is_active else ""
        self.badge_label = QtWidgets.QLabel(badge_text)
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 2px 6px; border-radius: 4px;" if self.is_active else "color: transparent;"
        )
        layout.addWidget(self.badge_label)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def set_active_state(self, is_active: bool):
        from ui.core.i18n import tr
        self.is_active = is_active
        badge_text = tr("render.badge_active", "ATIVO") if is_active else ""
        self.badge_label.setText(badge_text)
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 2px 6px; border-radius: 4px;" if is_active else "color: transparent;"
        )

    def retranslate_ui(self):
        from ui.core.i18n import tr
        if hasattr(self, "badge_label") and self.is_active:
            self.badge_label.setText(tr("render.badge_active", "ATIVO"))

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.selected.emit(self.profile_data)

    def update_style(self, *args):
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_card_hover") if self.is_selected else tm.get_color("bg_card")
        border = tm.get_color("accent") if self.is_selected else tm.get_color("border")
        text_color = tm.get_color("text_main")
        text_sec = tm.get_color("text_sec")

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
        if hasattr(self, "cat_label"):
            self.cat_label.setStyleSheet(f"color: {text_sec}; font-size: 11px;")


class EnginePipelineGroup(QtWidgets.QGroupBox):
    """Grupo de controles do pipeline de renderização e motor físico."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, saved_cfg: dict, parent=None):
        super().__init__("Pipeline de Renderização & Motor Físico", parent)
        self._saved_cfg = saved_cfg
        self._build_ui()

    def _build_ui(self):
        engine_layout = QtWidgets.QVBoxLayout(self)
        engine_layout.setContentsMargins(14, 14, 14, 14)
        engine_layout.setSpacing(10)

        # 1. Baixa Latência
        row_lat = QtWidgets.QHBoxLayout()
        self.lbl_lat = QtWidgets.QLabel("Modo de Baixa Latência (Ultra-Low Latency)")
        self.lbl_lat.setToolTip("Bypass na fila de sincronização para resposta em < 4ms")
        self.switch_lat = ToggleSwitch()
        self.switch_lat.setChecked(self._saved_cfg.get("low_latency", True))
        self.switch_lat.toggled.connect(self._on_setting_changed)
        row_lat.addWidget(self.lbl_lat)
        row_lat.addStretch()
        row_lat.addWidget(self.switch_lat)
        engine_layout.addLayout(row_lat)

        # 2. Correção Gama
        row_gam = QtWidgets.QHBoxLayout()
        self.lbl_gam = QtWidgets.QLabel("Correção Gama Linear (sRGB Physical Blending)")
        self.lbl_gam.setToolTip("Composição física no espaço linear eliminando bordas escuras")
        self.switch_gam = ToggleSwitch()
        self.switch_gam.setChecked(self._saved_cfg.get("linear_gamma", False))
        self.switch_gam.toggled.connect(self._on_setting_changed)
        row_gam.addWidget(self.lbl_gam)
        row_gam.addStretch()
        row_gam.addWidget(self.switch_gam)
        engine_layout.addLayout(row_gam)

        # 3. Deep Color
        row_deep = QtWidgets.QHBoxLayout()
        self.lbl_deep = QtWidgets.QLabel("Deep Color 64-bit (Half-Float RGBA16F Precision)")
        self.lbl_deep.setToolTip("Elimina 100% de banding em gradientes suaves e aquarelas")
        self.switch_deep = ToggleSwitch()
        self.switch_deep.setChecked(self._saved_cfg.get("deep_color", True))
        self.switch_deep.toggled.connect(self._on_setting_changed)
        row_deep.addWidget(self.lbl_deep)
        row_deep.addStretch()
        row_deep.addWidget(self.switch_deep)
        engine_layout.addLayout(row_deep)

        # 4. Histórico Undo / Redo
        row_undo = QtWidgets.QHBoxLayout()
        self.lbl_undo = QtWidgets.QLabel("Memória do Histórico (Undo / Redo)")
        self.lbl_undo.setToolTip("Limite dinâmico de memória RAM alocada para snapshots de tiles desfazer/refazer")
        self.combo_undo = QtWidgets.QComboBox()
        undo_opts = [
            (128, "128 MB"), (256, "256 MB (Padrão)"), (512, "512 MB"),
            (1024, "1024 MB (1 GB)"), (2048, "2048 MB (2 GB)"), (4096, "4096 MB (4 GB)"),
        ]
        for mb, lbl in undo_opts:
            self.combo_undo.addItem(lbl, mb)
        cur_mb = self._saved_cfg.get("undo_limit_mb", 256)
        idx = self.combo_undo.findData(cur_mb)
        if idx >= 0:
            self.combo_undo.setCurrentIndex(idx)
        self.combo_undo.currentIndexChanged.connect(self._on_setting_changed)
        row_undo.addWidget(self.lbl_undo)
        row_undo.addStretch()
        row_undo.addWidget(self.combo_undo)
        engine_layout.addLayout(row_undo)

    def _on_setting_changed(self, *args):
        mb = int(self.combo_undo.currentData() or 256) if hasattr(self, "combo_undo") else 256
        data = {
            "low_latency": self.switch_lat.isChecked(),
            "linear_gamma": self.switch_gam.isChecked(),
            "deep_color": self.switch_deep.isChecked(),
            "undo_limit_mb": mb,
        }
        self.settingsChanged.emit(data)

    def get_settings(self) -> dict:
        mb = int(self.combo_undo.currentData() or 256) if hasattr(self, "combo_undo") else 256
        return {
            "low_latency": self.switch_lat.isChecked(),
            "linear_gamma": self.switch_gam.isChecked(),
            "deep_color": self.switch_deep.isChecked(),
            "undo_limit_mb": mb,
        }
