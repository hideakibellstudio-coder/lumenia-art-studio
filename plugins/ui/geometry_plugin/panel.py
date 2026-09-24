"""GeometryPanel — escolha e ajuste de guia e simetria na doca.

View do `GeometryState` (ui/core/state), injetado pelo plugin: o seletor e o
diálogo avançado escrevem nele; o canvas, que também o edita (alças, menu),
leva ao motor e ao documento. Até 2026-09-24 o painel guardava uma cópia
própria do estado (`self.state`), lia a do canvas por
`rw.geometry_ctrl.guide_state` e empurrava tudo de volta a cada mudança — a
simetria de um documento vazava para o outro e o diálogo desfazia o ângulo
arrastado no canvas.
"""

from PySide6 import QtWidgets, QtCore
from ui.core.state import GeometryState
from ui.core.theme.manager import ThemeManager
from ui.core.icons import get_icon
from .components.constants import GUIDE_TYPES, SYM_TYPES, get_guide_name, get_sym_name
from .components.geometry_selector import GeometrySelectorButton
from .components.advanced_settings_dialog import AdvancedGeometryDialog


def _index(items: list, key: str) -> int:
    return items.index(key) if key in items else 0


class GeometryPanel(QtWidgets.QWidget):
    """Painel de Réguas, Perspectiva e Simetria na gaveta de ferramentas."""

    def __init__(self, geometry_state: GeometryState, parent=None, canvas_area=None):
        super().__init__(parent)
        self._state = geometry_state
        # Área livre do canvas (WorkspaceService.canvas_area_rect): onde o
        # diálogo avançado abre.
        self._canvas_area = canvas_area
        self.adv_dialog = None
        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()
        geometry_state.guideChanged.connect(self._show_state)
        geometry_state.symmetryChanged.connect(self._show_state)
        self._show_state()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(8)

        from ui.core.i18n import tr, I18nManager

        # 1. Cabeçalho com Engrenagem e Seletor
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(6)

        self.btn_advanced = QtWidgets.QPushButton()
        self.btn_advanced.setIcon(get_icon("settings"))
        self.btn_advanced.setIconSize(QtCore.QSize(18, 18))
        self.btn_advanced.setFixedSize(34, 34)
        self.btn_advanced.setToolTip(tr("geometry.advanced_settings", "Configurações Avançadas de Simetria e Réguas"))
        self.btn_advanced.clicked.connect(self._toggle_advanced)
        header.addWidget(self.btn_advanced)

        self.selector_btn = GeometrySelectorButton()
        self.selector_btn.ruler_changed.connect(lambda _idx, gtype: self._state.set_guide_type(gtype))
        self.selector_btn.symmetry_changed.connect(lambda _idx, stype: self._state.set_symmetry_mode(stype))
        header.addWidget(self.selector_btn, 1)
        main_layout.addLayout(header)

        # 2. Card de Informações e Status
        self.card = QtWidgets.QFrame()
        card_lay = QtWidgets.QVBoxLayout(self.card)
        card_lay.setSpacing(8)

        self.lbl_status = QtWidgets.QLabel(tr("geometry.status_idle", "Selecione um modo de régua ou simetria acima para iniciar o desenho assistido."))
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        card_lay.addWidget(self.lbl_status)

        # Botão Centralizar Pivô
        self.btn_center_pivot = QtWidgets.QPushButton(tr('geometry.center_pivot', 'Centralizar Pivô no Canvas'))
        self.btn_center_pivot.setIcon(get_icon("target", ThemeManager.instance().get_color("text_main")))
        self.btn_center_pivot.clicked.connect(self._state.center_pivot)
        self.btn_center_pivot.setVisible(False)
        card_lay.addWidget(self.btn_center_pivot)

        # Botão Resetar Ângulo
        self.btn_reset_angle = QtWidgets.QPushButton(tr('geometry.reset_axis_angle', 'Resetar Ângulo do Eixo (0°)'))
        self.btn_reset_angle.setIcon(get_icon("reset", ThemeManager.instance().get_color("text_main")))
        self.btn_reset_angle.clicked.connect(self._reset_angle)
        self.btn_reset_angle.setVisible(False)
        card_lay.addWidget(self.btn_reset_angle)

        main_layout.addWidget(self.card)
        main_layout.addStretch()
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self):
        from ui.core.i18n import tr
        self.btn_advanced.setToolTip(tr("geometry.advanced_settings", "Configurações Avançadas de Simetria e Réguas"))
        self.btn_center_pivot.setText(tr('geometry.center_pivot', 'Centralizar Pivô no Canvas'))
        self.btn_reset_angle.setText(tr('geometry.reset_axis_angle', 'Resetar Ângulo do Eixo (0°)'))
        self._show_status()

    def _apply_theme(self, *args):
        tm = ThemeManager.instance()
        bg_panel = tm.get_color("bg_panel", "#1e1e24")
        bg_card = tm.get_color("bg_card", "#181825")
        border = tm.get_color("border", "#313244")
        accent = tm.get_color("accent", "#6366f1")
        text_main = tm.get_color("text_main", "#f3f4f6")
        text_sec = tm.get_color("text_sec", "#9ca3af")
        bg_hover = tm.get_color("accent_muted", "#4f46e5")
        fg_on_accent = tm.get_color("FG_PRIMARY", "#ffffff")

        self.btn_advanced.setIcon(get_icon("settings", color=accent))
        self.btn_advanced.setStyleSheet(f"""
            QPushButton {{
                background: {bg_panel}; border: 1px solid {border};
                border-radius: 6px;
            }}
            QPushButton:hover {{ background: {bg_hover}; border-color: {accent}; }}
        """)

        self.card.setStyleSheet(f"""
            QFrame {{
                background: {bg_card}; border: 1px solid {border};
                border-radius: 8px; padding: 10px;
            }}
            QLabel {{ color: {text_main}; font-size: 11px; }}
            QPushButton {{
                background: {bg_panel}; color: {text_main}; border: 1px solid {border};
                border-radius: 4px; padding: 6px 10px; font-size: 11px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {accent}; color: {fg_on_accent}; }}
        """)
        self._show_status()

    def _toggle_advanced(self):
        if self.adv_dialog and self.adv_dialog.isVisible():
            self.adv_dialog.hide()
            return
        if not self.adv_dialog:
            self.adv_dialog = AdvancedGeometryDialog(self.window(), self._state.fields(), self._canvas_area)
            self.adv_dialog.settingsChanged.connect(self._state.apply_advanced)
        else:
            self.adv_dialog.sync_from_state(self._state.fields())
        self.adv_dialog.show_near(self.btn_advanced)

    def _reset_angle(self):
        self._state.symmetry["angle"] = 0.0 if self._state.symmetry["mode"] == "mirror_h" else 90.0

    # ── Estado → tela ─────────────────────────────────────────────────────

    def _show_state(self) -> None:
        self.selector_btn.set_selection(_index(GUIDE_TYPES, self._state.guide["type"]),
                                        _index(SYM_TYPES, self._state.symmetry["mode"]))
        self._show_status()
        if self.adv_dialog is not None and self.adv_dialog.isVisible():
            # Alça arrastada no canvas aparece no diálogo aberto.
            self.adv_dialog.sync_from_state(self._state.fields())

    def _show_status(self):
        from ui.core.i18n import tr
        guide_type, sym_mode = self._state.guide["type"], self._state.symmetry["mode"]

        lines = []
        if sym_mode != "none":
            lbl_sym = tr("geometry.symmetry_label", "Simetria")
            lines.append(f"<b>{lbl_sym}:</b> {get_sym_name(_index(SYM_TYPES, sym_mode))}")
        if guide_type != "none":
            lbl_ruler = tr("geometry.ruler_label", "Régua")
            lines.append(f"<b>{lbl_ruler}:</b> {get_guide_name(_index(GUIDE_TYPES, guide_type))}")

        tm = ThemeManager.instance()
        accent = tm.get_color("accent", "#6366f1")
        text_sec = tm.get_color("text_sec", "#9ca3af")

        if not lines:
            self.lbl_status.setText(tr("geometry.status_idle", "Selecione um modo de régua ou simetria acima para iniciar o desenho assistido."))
            self.lbl_status.setStyleSheet(f"color: {text_sec}; margin: 8px 0;")
            self.btn_center_pivot.setVisible(False)
            self.btn_reset_angle.setVisible(False)
        else:
            self.lbl_status.setText("<br>".join(lines))
            self.lbl_status.setStyleSheet(f"color: {accent}; margin: 4px 0; font-weight: 500;")
            self.btn_center_pivot.setVisible(True)
            self.btn_reset_angle.setVisible(self._state.has_free_axis())
