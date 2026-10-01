"""
Components for RenderSettingsDialog (ProofingPreviewBar, ProfileCard, EnginePipelineGroup).
===========================================================================================
Contém os componentes de prova de impressão espectral, cartões de perfis de cor,
painel de configurações do motor de renderização e persistência de preferências de cor.
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.backend_protocols import ColorProtocol, RoleProvider
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.icons import get_icon
from ui.core.widgets.toggle.toggle_switch import ToggleSwitch


# ── CARREGAMENTO / PERSISTÊNCIA ──────────────────────────────────────────────

def load_render_settings() -> dict:
    """Carrega as configurações salvas de renderização e perfil de cor do ConfigManager (JSON)."""
    from ui.infrastructure.config import ConfigManager
    sec = ConfigManager.instance().get_section("render")
    raw_profile = sec.get("profile_id", 0)
    aliases = {"srgb": 0, "display_p3": 1, "p3": 1, "adobe_rgb": 2, "rec2020": 3}
    if isinstance(raw_profile, str):
        profile_id = aliases.get(raw_profile.strip().lower(), 0)
    else:
        try:
            profile_id = int(raw_profile)
        except (TypeError, ValueError):
            profile_id = 0
    return {
        "profile_id": profile_id,
        "rendering_intent": int(sec.get("rendering_intent", 1)),
        "bpc": bool(sec.get("bpc", True)),
        "soft_proof_enabled": bool(sec.get("soft_proof_enabled", False)),
        "proof_profile_id": int(sec.get("proof_profile_id", 5)),
        "gamut_warning": bool(sec.get("gamut_warning", False)),
        "low_latency": bool(sec.get("low_latency", True)),
        "linear_gamma": bool(sec.get("linear_gamma", False)),
        "deep_color": bool(sec.get("deep_color", False)),
        "undo_limit_mb": int(sec.get("undo_limit_mb", 512)),
        "undo_max_steps": int(sec.get("undo_max_steps", 50)),
    }


def save_render_settings(cfg_dict: dict) -> None:
    """Salva as configurações de renderização e perfil de cor no ConfigManager (JSON)."""
    from ui.infrastructure.config import ConfigManager
    ConfigManager.instance().set_section("render", cfg_dict)


# ── COMPONENTES VISUAIS ──────────────────────────────────────────────────────

class ProofingPreviewBar(QtWidgets.QWidget):
    """Renderiza uma barra de degradê espectral comparativa simulando o perfil ativo em tempo real."""

    def __init__(self, backend: RoleProvider[ColorProtocol], parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self._backend = backend
        self._profile_id = 0

    def set_profile(self, profile_id: int):
        self._profile_id = profile_id
        self.update()

    def paintEvent(self, event):
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

        backend = self._backend()
        sp_active = False
        if backend:
            sp = backend.get_soft_proofing()
            sp_active = bool(sp and getattr(sp, "enabled", False))

        if (self._profile_id != 0 or sp_active) and backend:
            raw = backend.transform_rgba_for_profile(bytes(img.bits()), self._profile_id)
            img = QtGui.QImage(raw, w, h, w * 4, QtGui.QImage.Format_RGBA8888).copy()

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

        from ui.infrastructure.i18n import tr, I18nManager
        badge_text = tr("render.badge_active", "ATIVO") if self.is_active else ""
        self.badge_label = QtWidgets.QLabel(badge_text)
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 2px 6px; border-radius: 4px;" if self.is_active else "color: transparent;"
        )
        layout.addWidget(self.badge_label)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def set_active_state(self, is_active: bool):
        from ui.infrastructure.i18n import tr
        self.is_active = is_active
        badge_text = tr("render.badge_active", "ATIVO") if is_active else ""
        self.badge_label.setText(badge_text)
        self.badge_label.setStyleSheet(
            "font-size: 9px; font-weight: bold; color: #ff5252; background: rgba(255,82,82,0.15); "
            "padding: 2px 6px; border-radius: 4px;" if is_active else "color: transparent;"
        )

    def retranslate_ui(self):
        from ui.infrastructure.i18n import tr
        if self.is_active:
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
        self.cat_label.setStyleSheet(f"color: {text_sec}; font-size: 11px;")


class EnginePipelineGroup(QtWidgets.QGroupBox):
    """Grupo de controles do pipeline de renderização e motor físico."""

    settingsChanged = QtCore.Signal(dict)

    def __init__(self, saved_cfg: dict, capabilities: Optional[dict] = None, parent=None):
        super().__init__("Pipeline de Renderização & Motor Físico", parent)
        self._saved_cfg = saved_cfg
        self._capabilities = dict(capabilities or {})
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
        self.lbl_deep = QtWidgets.QLabel("Deep Color (composição de precisão estendida)")
        self.lbl_deep.setToolTip("Calcula cada composição em precisão estendida antes da quantização final de 8 bits")
        self.switch_deep = ToggleSwitch()
        self.switch_deep.setChecked(self._saved_cfg.get("deep_color", False))
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

        self._apply_capabilities()

    def _apply_capabilities(self) -> None:
        controls = (
            ("low_latency", self.lbl_lat, self.switch_lat),
            ("linear_gamma", self.lbl_gam, self.switch_gam),
            ("deep_color", self.lbl_deep, self.switch_deep),
            ("history", self.lbl_undo, self.combo_undo),
        )
        for capability, label, control in controls:
            supported = bool(self._capabilities.get(capability, False))
            label.setEnabled(supported)
            control.setEnabled(supported)
            if not supported:
                message = "Indisponível no backend ativo."
                label.setToolTip(message)
                control.setToolTip(message)

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


def apply_render_dialog_styles(dialog: QtWidgets.QDialog) -> None:
    """Aplica a estilização completa de tema e contraste para o RenderSettingsDialog."""
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

    if hasattr(dialog, "root_container") and dialog.root_container:
        dialog.root_container.setStyleSheet(f"""
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

    dialog.setStyleSheet(f"""
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
            selection-color: {text_main};
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
            color: {text_main};
        }}
        QPushButton:disabled {{
            background-color: {bg_panel};
            color: {text_sec};
            border-color: {border_muted};
        }}
    """)
    if hasattr(dialog, "lbl_insp_icon") and dialog.lbl_insp_icon:
        dialog.lbl_insp_icon.setStyleSheet(f"border: 1px solid {border}; background: {bg_card}; border-radius: 8px;")

    if hasattr(dialog, "btn_apply") and dialog.btn_apply:
        dialog.btn_apply.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                color: {text_main};
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
