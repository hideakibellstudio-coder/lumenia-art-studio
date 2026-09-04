"""
StabilizerLabPanel — Painel Visual do Laboratório de Estabilização.
===================================================================
Oferece:
1. Seleção rápida por Perfis Artísticos Semânticos (Fluido, Pintura, Lineart, Contorno Esculpido, Fita de Seda).
2. Slider de Ajuste Fino 100% diluído e perceptualmente uniforme (zero zona morta).
3. Sincronização bidirecional em tempo real com a barra superior (ToolSidebar).
4. Suporte a comparação com os motores Infinite Painter (Kalman) e Lumenia Baseline antigo.
"""

from __future__ import annotations
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.theme.manager import ThemeManager
from ui.core.widgets.compact_slider import CompactSlider
from ui.core.widgets.card_box import PanelCardBox
from ui.core.engine.stabilizer_hub import StabilizerHub


class StabilizerLabPanel(QtWidgets.QWidget):
    """Painel visual acoplável com controle por perfis e diluição contínua."""

    modeChanged = QtCore.Signal(str)          # "profiles" | "kalman" | "baseline"
    masterToggled = QtCore.Signal(bool)       # True / False

    def __init__(self, plugin=None, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StabilizerLabPanel")
        self.plugin = plugin
        self.hub = StabilizerHub.instance()
        self._engine_mode = "profiles"  # "profiles" | "kalman" | "baseline"

        self._build_ui()
        self._connect_hub()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(6)

        # ── 1. Botão Mestre de Ativação ──
        self.btn_master = QtWidgets.QPushButton("🟢 ESTABILIZADOR LAB: ATIVO")
        self.btn_master.setObjectName("BtnMasterStabilizer")
        self.btn_master.setFixedHeight(30)
        self.btn_master.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_master.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: bold; border-radius: 4px; font-size: 11px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.btn_master.clicked.connect(self._on_toggle_master)
        main_layout.addWidget(self.btn_master)

        # ── 2. Seletor de Perfil Principal (Sincronizado com o Topo) ──
        lbl_profile = QtWidgets.QLabel("PERFIL DE TRAÇO (ESTABILIZAÇÃO):")
        lbl_profile.setStyleSheet("font-size: 10px; font-weight: bold; color: #a5b4fc; margin-top: 2px;")
        main_layout.addWidget(lbl_profile)

        self.combo_profile = QtWidgets.QComboBox()
        self.combo_profile.setFixedHeight(26)
        from ui.core.icons import get_icon
        for pid, pdata in self.hub.PROFILES.items():
            icon = get_icon(pdata.get("icon_name", "stabilizer"), "FG_SECONDARY")
            self.combo_profile.addItem(icon, pdata["name"], pid)
        self.combo_profile.currentIndexChanged.connect(self._on_combo_profile_changed)
        main_layout.addWidget(self.combo_profile)

        # Label de descrição do perfil ativo
        self.lbl_profile_desc = QtWidgets.QLabel("")
        self.lbl_profile_desc.setWordWrap(True)
        self.lbl_profile_desc.setStyleSheet("font-size: 9px; color: #9ca3af; margin-bottom: 2px;")
        main_layout.addWidget(self.lbl_profile_desc)

        # ── 3. Slider de Ajuste Fino (Diluição Uniforme de 0% a 100%) ──
        card_fine = PanelCardBox("AJUSTE FINO DO PERFIL (DILUIÇÃO 100%)")
        lo_fine = QtWidgets.QVBoxLayout(card_fine)
        lo_fine.setContentsMargins(6, 6, 6, 6)
        lo_fine.setSpacing(6)

        self.slider_fine_tuning = CompactSlider("Intensidade: ", 0, 100, "%")
        self.slider_fine_tuning.setValue(self.hub.fine_tuning_pct)
        self.slider_fine_tuning.valueChanged.connect(self._on_fine_tuning_slider_changed)
        lo_fine.addWidget(self.slider_fine_tuning)

        # Status em tempo real dos parâmetros calculados
        self.lbl_calculated_info = QtWidgets.QLabel("Buffer: 24 amostras | Inércia α: 0.226")
        self.lbl_calculated_info.setStyleSheet("font-size: 9px; color: #6ee7b7; font-weight: bold;")
        lo_fine.addWidget(self.lbl_calculated_info)

        # Checkbox Suavização de Pressão
        self.chk_smooth_pressure = QtWidgets.QCheckBox("Amortecer Pressão da Caneta (Linha Firme)")
        self.chk_smooth_pressure.setChecked(True)
        self.chk_smooth_pressure.setStyleSheet("font-size: 10px; color: #e5e7eb;")
        self.chk_smooth_pressure.toggled.connect(self._on_pressure_toggled)
        lo_fine.addWidget(self.chk_smooth_pressure)

        # Velocidade do Flush no Pen Up
        self.slider_flush_speed = CompactSlider("Velocidade Flush Pen Up: ", 50, 200, "%")
        self.slider_flush_speed.setValue(int(self.hub.flush_speed * 100))
        self.slider_flush_speed.valueChanged.connect(self._on_flush_speed_changed)
        lo_fine.addWidget(self.slider_flush_speed)

        main_layout.addWidget(card_fine)

        # ── 4. Seletor de Comparação / Motores Alternativos ──
        lbl_alt = QtWidgets.QLabel("COMPARAR COM OUTROS MOTORES:")
        lbl_alt.setStyleSheet("font-size: 9px; font-weight: bold; color: #9ca3af; margin-top: 4px;")
        main_layout.addWidget(lbl_alt)

        self.combo_engine = QtWidgets.QComboBox()
        self.combo_engine.addItem("🌟 Novo Motor por Perfis (Lumenia Inking v2)", "profiles")
        self.combo_engine.addItem("🌀 Infinite Painter (Kalman 4D Cinemático)", "kalman")
        self.combo_engine.addItem("⏳ Lumenia Baseline Antigo (Rampa Quadrática)", "baseline")
        self.combo_engine.setFixedHeight(24)
        self.combo_engine.currentIndexChanged.connect(self._on_engine_mode_changed)
        main_layout.addWidget(self.combo_engine)

        # ── 5. Telemetria e Diagnóstico ──
        card_telem = PanelCardBox("DIAGNÓSTICO DO TRAÇO")
        lo_telem = QtWidgets.QVBoxLayout(card_telem)
        lo_telem.setContentsMargins(6, 6, 6, 6)
        lo_telem.setSpacing(3)

        self.lbl_telem_status = QtWidgets.QLabel("Status: Pronto")
        self.lbl_telem_status.setStyleSheet("font-size: 10px; color: #e5e7eb;")
        lo_telem.addWidget(self.lbl_telem_status)

        self.lbl_telem_details = QtWidgets.QLabel("Buffer: 0 amostras | Resíduo: 0.00px")
        self.lbl_telem_details.setStyleSheet("font-size: 9px; color: #9ca3af;")
        lo_telem.addWidget(self.lbl_telem_details)

        main_layout.addWidget(card_telem)

        # ── 6. Botão Resetar ──
        btn_reset = QtWidgets.QPushButton("Restaurar Padrão do Perfil (50%)")
        btn_reset.setFixedHeight(24)
        btn_reset.setCursor(QtCore.Qt.PointingHandCursor)
        btn_reset.clicked.connect(self._on_reset_profile_defaults)
        main_layout.addWidget(btn_reset)

        main_layout.addStretch(1)
        self._sync_ui_from_hub()

    # ── Conexão e Sincronização com o StabilizerHub ──

    def _connect_hub(self) -> None:
        self.hub.profileChanged.connect(self._on_hub_profile_changed)
        self.hub.fineTuningChanged.connect(self._on_hub_fine_tuning_changed)
        self.hub.activeToggled.connect(self._on_hub_active_toggled)
        self.hub.parametersChanged.connect(self._update_calculated_display)

    def _sync_ui_from_hub(self) -> None:
        idx = self.combo_profile.findData(self.hub.current_profile)
        if idx >= 0:
            self.combo_profile.blockSignals(True)
            self.combo_profile.setCurrentIndex(idx)
            self.combo_profile.blockSignals(False)

        self.slider_fine_tuning.blockSignals(True)
        self.slider_fine_tuning.setValue(self.hub.fine_tuning_pct)
        self.slider_fine_tuning.blockSignals(False)

        self._update_calculated_display()

    def _update_calculated_display(self) -> None:
        p_info = self.hub.PROFILES.get(self.hub.current_profile, {})
        self.lbl_profile_desc.setText(p_info.get("description", ""))

        params = self.hub.get_calculated_params()
        if params["profile_id"] == "off":
            self.lbl_calculated_info.setText("Amortecimento: DESATIVADO (Sensor Cru 1:1)")
        else:
            self.lbl_calculated_info.setText(
                f"Buffer: {params['buffer_capacity']} amostras | Inércia α: {params['alpha']:.3f} | γ: {params['gamma']:.2f}"
            )

    def _on_combo_profile_changed(self, idx: int) -> None:
        pid = self.combo_profile.currentData()
        if pid:
            self.hub.set_profile(pid)

    def _on_fine_tuning_slider_changed(self, val: int) -> None:
        self.hub.set_fine_tuning_pct(val)

    def _on_hub_profile_changed(self, pid: str) -> None:
        idx = self.combo_profile.findData(pid)
        if idx >= 0 and self.combo_profile.currentIndex() != idx:
            self.combo_profile.blockSignals(True)
            self.combo_profile.setCurrentIndex(idx)
            self.combo_profile.blockSignals(False)
        self._update_calculated_display()

    def _on_hub_fine_tuning_changed(self, val: int) -> None:
        if self.slider_fine_tuning.value() != val:
            self.slider_fine_tuning.blockSignals(True)
            self.slider_fine_tuning.setValue(val)
            self.slider_fine_tuning.blockSignals(False)
        self._update_calculated_display()

    def _on_hub_active_toggled(self, active: bool) -> None:
        if active:
            self.btn_master.setText("🟢 ESTABILIZADOR LAB: ATIVO")
            self.btn_master.setStyleSheet(
                "QPushButton { background-color: #10b981; color: #ffffff; font-weight: bold; border-radius: 4px; font-size: 11px; }"
                "QPushButton:hover { background-color: #059669; }"
            )
        else:
            self.btn_master.setText("🔴 ESTABILIZADOR LAB: DESATIVADO")
            self.btn_master.setStyleSheet(
                "QPushButton { background-color: #ef4444; color: #ffffff; font-weight: bold; border-radius: 4px; font-size: 11px; }"
                "QPushButton:hover { background-color: #dc2626; }"
            )

    def _on_toggle_master(self) -> None:
        new_state = not self.hub.is_active
        self.hub.set_active(new_state)
        self.masterToggled.emit(new_state)

    def _on_pressure_toggled(self, checked: bool) -> None:
        pid = self.hub.current_profile
        if pid in self.hub.PROFILES:
            self.hub.PROFILES[pid]["smooth_pressure"] = checked
            self.hub.parametersChanged.emit()

    def _on_flush_speed_changed(self, val: int) -> None:
        self.hub.set_flush_speed(val / 100.0)

    def _on_engine_mode_changed(self, idx: int) -> None:
        mode = self.combo_engine.currentData()
        self._engine_mode = mode
        self.modeChanged.emit(mode)
        if self.plugin and hasattr(self.plugin, "set_engine_mode"):
            self.plugin.set_engine_mode(mode)

    def _on_reset_profile_defaults(self) -> None:
        self.slider_fine_tuning.setValue(50)
        self.slider_flush_speed.setValue(100)
        self.chk_smooth_pressure.setChecked(True)

    def update_telemetry(self, status: str, details: str) -> None:
        self.lbl_telem_status.setText(status)
        self.lbl_telem_details.setText(details)

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_panel", "#1e1e24")
        self.setStyleSheet(f"#StabilizerLabPanel {{ background-color: {bg}; }}")
