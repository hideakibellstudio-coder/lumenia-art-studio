"""
TelemetryPanel — Painel Visual de Telemetria e Diagnóstico do ALADYN ENGINE
===========================================================================
Exibe métricas de desempenho em tempo real com controle de ciclo de vida limpo:
- Botão Mestre de Ativação/Desativação (Zero Overhead quando inativo)
- Indicadores compactos de Pressão, Velocidade, Latência do Motor (µs) e RAM
- Acesso rápido ao Diálogo Avançado de Diagnóstico (TelemetryDiagnosticsDialog)
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.widgets.card_box import PanelCardBox
from ui.core.theme.manager import ThemeManager
from ui.core.engine.registry import EngineRegistry
from ui.core.dialogs.telemetry_diagnostics_dialog import TelemetryDiagnosticsDialog


class TelemetryPanel(QtWidgets.QWidget):
    """Painel de telemetria acoplável em docas com switch limpo de ciclo de vida."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TelemetryPanel")
        self._is_capturing = False

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS polling desacoplado
        self._timer.timeout.connect(self._update_telemetry)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        content = QtWidgets.QWidget()
        lo = QtWidgets.QVBoxLayout(content)
        lo.setContentsMargins(8, 8, 8, 8)
        lo.setSpacing(8)

        from ui.core.i18n import tr, I18nManager

        # 1. Botão Mestre de Ativação / Desativação
        self.btn_toggle_telemetry = QtWidgets.QPushButton(f"⚪ {tr('telemetry.enable_capture', 'Ativar Captura de Telemetria')}")
        self.btn_toggle_telemetry.setObjectName("BtnToggleTelemetry")
        self.btn_toggle_telemetry.setFixedHeight(30)
        self.btn_toggle_telemetry.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_toggle_telemetry.setToolTip(tr("telemetry.tooltip", "Ativa ou desativa a captura de métricas no motor C++ com liberação limpa de memória."))
        self.btn_toggle_telemetry.clicked.connect(self._on_toggle_capture)
        lo.addWidget(self.btn_toggle_telemetry)

        self.lbl_status = QtWidgets.QLabel(f"{tr('telemetry.status', 'Status')}: {tr('telemetry.idle', 'Em Espera')} (0% Sobrecarga)")
        self.lbl_status.setObjectName("TelemStatus")
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        lo.addWidget(self.lbl_status)

        lo.addSpacing(4)

        # 2. Indicador de Pressão
        self.lbl_hdr_pressure = self._make_label(tr("telemetry.pen_pressure", "PRESSÃO DA CANETA"))
        lo.addWidget(self.lbl_hdr_pressure)
        self.bar_pressure = QtWidgets.QProgressBar()
        self.bar_pressure.setRange(0, 100)
        self.bar_pressure.setValue(0)
        self.bar_pressure.setFixedHeight(12)
        self.bar_pressure.setTextVisible(False)
        self.lbl_pressure_val = QtWidgets.QLabel("0 %")
        self.lbl_pressure_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        
        row_press = QtWidgets.QHBoxLayout()
        row_press.addWidget(self.bar_pressure, 1)
        row_press.addWidget(self.lbl_pressure_val)
        lo.addLayout(row_press)

        # 3. Indicador de Velocidade
        self.lbl_hdr_velocity = self._make_label(tr("telemetry.stroke_velocity", "VELOCIDADE DO TRAÇO"))
        lo.addWidget(self.lbl_hdr_velocity)
        self.bar_velocity = QtWidgets.QProgressBar()
        self.bar_velocity.setRange(0, 1000)
        self.bar_velocity.setValue(0)
        self.bar_velocity.setFixedHeight(12)
        self.bar_velocity.setTextVisible(False)
        self.lbl_velocity_val = QtWidgets.QLabel("0 px/s")
        self.lbl_velocity_val.setStyleSheet("font-size: 10px; font-weight: bold;")

        row_vel = QtWidgets.QHBoxLayout()
        row_vel.addWidget(self.bar_velocity, 1)
        row_vel.addWidget(self.lbl_velocity_val)
        lo.addLayout(row_vel)

        # 4. Indicador de Latência do Motor (C++)
        self.lbl_hdr_latency = self._make_label(tr("telemetry.dab_latency", "LATÊNCIA POR DAB (C++)"))
        lo.addWidget(self.lbl_hdr_latency)
        self.lbl_latency_val = QtWidgets.QLabel("0.00 µs")
        self.lbl_latency_val.setStyleSheet("font-size: 11px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_latency_val)

        # 5. Indicador de Consumo de RAM do Canvas & Undo
        self.lbl_hdr_ram = self._make_label(tr("telemetry.memory", "MEMÓRIA (CANVAS / UNDO)"))
        lo.addWidget(self.lbl_hdr_ram)
        self.lbl_ram_val = QtWidgets.QLabel("0.00 MB / 0.00 MB")
        self.lbl_ram_val.setStyleSheet("font-size: 11px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_ram_val)

        lo.addSpacing(6)

        # 6. Botão para Abrir o Diálogo Avançado
        self.btn_open_dialog = QtWidgets.QPushButton(f"⚙️ {tr('telemetry.advanced_dialog', 'Diagnósticos Avançados...')}")
        self.btn_open_dialog.setObjectName("BtnOpenDialog")
        self.btn_open_dialog.setFixedHeight(28)
        self.btn_open_dialog.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_open_dialog.clicked.connect(self._open_diagnostics_dialog)
        lo.addWidget(self.btn_open_dialog)

        lo.addStretch()

        card_box = PanelCardBox("", content, self)
        main_layout.addWidget(card_box)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self):
        from ui.core.i18n import tr
        if hasattr(self, "btn_toggle_telemetry"):
            if self._is_capturing:
                self.btn_toggle_telemetry.setText(f"🟢 {tr('telemetry.disable_capture', 'Desativar Captura')}")
            else:
                self.btn_toggle_telemetry.setText(f"⚪ {tr('telemetry.enable_capture', 'Ativar Captura de Telemetria')}")
        if hasattr(self, "lbl_hdr_pressure"):
            self.lbl_hdr_pressure.setText(tr("telemetry.pen_pressure", "PRESSÃO DA CANETA"))
        if hasattr(self, "lbl_hdr_velocity"):
            self.lbl_hdr_velocity.setText(tr("telemetry.stroke_velocity", "VELOCIDADE DO TRAÇO"))
        if hasattr(self, "lbl_hdr_latency"):
            self.lbl_hdr_latency.setText(tr("telemetry.dab_latency", "LATÊNCIA POR DAB (C++)"))
        if hasattr(self, "lbl_hdr_ram"):
            self.lbl_hdr_ram.setText(tr("telemetry.memory", "MEMÓRIA (CANVAS / UNDO)"))
        if hasattr(self, "btn_open_dialog"):
            self.btn_open_dialog.setText(f"⚙️ {tr('telemetry.advanced_dialog', 'Diagnósticos Avançados...')}")

    def _make_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName("TelemLabel")
        return lbl

    def _on_toggle_capture(self) -> None:
        self._is_capturing = not self._is_capturing
        backend = EngineRegistry.instance().get_backend()

        if self._is_capturing:
            if backend and hasattr(backend, "set_telemetry_enabled"):
                backend.set_telemetry_enabled(True)
            self.btn_toggle_telemetry.setText("🟢 Telemetria Ativa (Pausar)")
            self.lbl_status.setText("Status: Capturando métricas (30 FPS)")
            self.lbl_status.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 10px;")
            self._timer.start()
        else:
            if backend and hasattr(backend, "set_telemetry_enabled"):
                backend.set_telemetry_enabled(False)
            self._timer.stop()
            self.btn_toggle_telemetry.setText("⚪ Ativar Captura de Telemetria")
            self.lbl_status.setText("Status: Em Espera (0% Sobrecarga)")
            self.lbl_status.setStyleSheet("color: #888888; font-size: 10px;")
            # Reseta os medidores para estado de repouso
            self.bar_pressure.setValue(0)
            self.lbl_pressure_val.setText("0 %")
            self.bar_velocity.setValue(0)
            self.lbl_velocity_val.setText("0 px/s")
            self.lbl_latency_val.setText("0.00 µs")
            self.lbl_ram_val.setText("0.00 MB / 0.00 MB")

    def _update_telemetry(self) -> None:
        if not self._is_capturing:
            return

        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return

        # Snapshot completo da estrutura do C++
        if hasattr(backend, "get_telemetry_snapshot"):
            snap = backend.get_telemetry_snapshot()
            if snap:
                press_pct = int(snap.raw_pressure * 100)
                self.bar_pressure.setValue(min(100, max(0, press_pct)))
                self.lbl_pressure_val.setText(f"{press_pct} %")

                vel_val = int(snap.stroke_velocity)
                self.bar_velocity.setValue(min(1000, max(0, vel_val)))
                self.lbl_velocity_val.setText(f"{vel_val} px/s")

                self.lbl_latency_val.setText(f"{snap.last_segment_latency_us:.2f} µs")
                self.lbl_ram_val.setText(f"{snap.tile_grid_memory_mb:.2f} MB / {snap.undo_stack_memory_mb:.2f} MB")
                return

        # Fallback para tupla antiga
        if hasattr(backend, "last_telemetry"):
            p, v, f = backend.last_telemetry
            press_pct = int(p * 100)
            self.bar_pressure.setValue(min(100, max(0, press_pct)))
            self.lbl_pressure_val.setText(f"{press_pct} %")

            vel_val = int(v)
            self.bar_velocity.setValue(min(1000, max(0, vel_val)))
            self.lbl_velocity_val.setText(f"{vel_val} px/s")

    def _open_diagnostics_dialog(self) -> None:
        # Abre a janela de diagnóstico padronizada
        dlg = TelemetryDiagnosticsDialog(self.window())
        dlg.exec()

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        border = tm.get_color("border")
        muted = tm.get_color("text_sec")
        accent = tm.get_color("accent")
        text = tm.get_color("text_main")
        bg_panel = tm.get_color("bg_panel")
        bg_card = tm.get_color("bg_card")

        self.setStyleSheet(f"""
            QLabel#TelemLabel {{
                color: {muted};
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QLabel#TelemStatus {{
                font-size: 10px;
                color: {muted};
            }}
            QProgressBar {{
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid {border};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 2px;
            }}
            QPushButton#BtnToggleTelemetry {{
                background-color: {bg_card};
                border: 1px solid {border};
                border-radius: 4px;
                color: {text};
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton#BtnToggleTelemetry:hover {{
                border-color: {accent};
            }}
            QPushButton#BtnOpenDialog {{
                background-color: transparent;
                border: 1px solid {border};
                border-radius: 4px;
                color: {text};
                font-size: 10px;
            }}
            QPushButton#BtnOpenDialog:hover {{
                background-color: {bg_card};
                border-color: {accent};
            }}
            QLabel {{
                color: {text};
            }}
        """)
