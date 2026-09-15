"""
TelemetryPanel — Painel Visual de Telemetria e Diagnóstico do ALADYN ENGINE
===========================================================================
Exibe métricas de desempenho em tempo real com decomposição granular nativa:
- Botão Mestre de Ativação/Desativação (Zero Overhead quando inativo)
- Barra Empilhada do Pipeline (Kinematics, Interpolação, Raster Dab, Undo, Compositor, Qt Blit)
- Banner Inteligente de Detecção de Gargalos em Tempo Real
- Cards Comparativos: C++ Motor vs Qt Blit, Mesa (Hz) vs Tela (FPS), Dabs vs Região Suja
- Indicadores de Pressão, Velocidade e RAM (Canvas / Undo)
- Acesso rápido ao Diálogo Avançado de Diagnóstico (TelemetryDiagnosticsDialog)
"""

from __future__ import annotations

from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.widgets.card_box import PanelCardBox
from ui.core.theme.manager import ThemeManager
from ui.core.engine.registry import EngineRegistry
from ui.core.dialogs.telemetry_diagnostics_dialog import TelemetryDiagnosticsDialog
from ui.core.widgets.pipeline_bar import PipelineBar


class TelemetryPanel(QtWidgets.QWidget):
    """Painel de telemetria acoplável em docas com switch limpo de ciclo de vida."""

    def __init__(self, parent: QtWidgets.QWidget | None = None, auto_start: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("TelemetryPanel")
        self._is_capturing = auto_start

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS polling desacoplado
        self._timer.timeout.connect(self._update_telemetry)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        self._apply_theme()

        if self._is_capturing:
            backend = EngineRegistry.instance().get_backend()
            if backend and hasattr(backend, "set_telemetry_enabled"):
                backend.set_telemetry_enabled(True)
            self._timer.start()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        content = QtWidgets.QWidget()
        lo = QtWidgets.QVBoxLayout(content)
        lo.setContentsMargins(8, 8, 8, 8)
        lo.setSpacing(6)

        from ui.core.i18n import tr, I18nManager

        # Botão Destaque: Cockpit em Grid (Janela Flutuante)
        self.btn_open_grid = QtWidgets.QPushButton("🪟 Cockpit em Grid (F12)")
        self.btn_open_grid.setObjectName("BtnOpenGrid")
        self.btn_open_grid.setFixedHeight(32)
        self.btn_open_grid.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_open_grid.setToolTip("Abre o cockpit flutuante com todos os 20 medidores em tempo real (F12)")
        self.btn_open_grid.clicked.connect(self._open_grid_window)
        lo.addWidget(self.btn_open_grid)

        # 1. Botão Mestre de Ativação / Desativação
        btn_text = f"🟢 {tr('telemetry.disable_capture', 'Captura Ativa (Desativar)')}" if self._is_capturing else f"⚪ {tr('telemetry.enable_capture', 'Ativar Captura de Telemetria')}"
        self.btn_toggle_telemetry = QtWidgets.QPushButton(btn_text)
        self.btn_toggle_telemetry.setObjectName("BtnToggleTelemetry")
        self.btn_toggle_telemetry.setFixedHeight(30)
        self.btn_toggle_telemetry.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_toggle_telemetry.setToolTip(tr("telemetry.tooltip", "Ativa ou desativa a captura de métricas no motor C++ com liberação limpa de memória."))
        self.btn_toggle_telemetry.clicked.connect(self._on_toggle_capture)
        lo.addWidget(self.btn_toggle_telemetry)

        status_text = f"{tr('telemetry.status', 'Status')}: {tr('telemetry.capturing', 'Capturando métricas (30 FPS)')}" if self._is_capturing else f"{tr('telemetry.status', 'Status')}: {tr('telemetry.idle', 'Em Espera')} (0% Sobrecarga)"
        self.lbl_status = QtWidgets.QLabel(status_text)
        self.lbl_status.setObjectName("TelemStatus")
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        if self._is_capturing:
            self.lbl_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 10px;")
        lo.addWidget(self.lbl_status)

        # 2. Banner de Diagnóstico de Gargalos (Bottleneck Alert)
        self.lbl_bottleneck = QtWidgets.QLabel("✅ PIPELINE EQUILIBRADO")
        self.lbl_bottleneck.setObjectName("BottleneckBanner")
        self.lbl_bottleneck.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_bottleneck.setFixedHeight(22)
        lo.addWidget(self.lbl_bottleneck)

        lo.addSpacing(2)

        # 3. Barra Empilhada de Decomposição do Pipeline
        self.lbl_hdr_pipeline = self._make_label("ESTÁGIOS DO PIPELINE (TEMPO RELATIVO)")
        lo.addWidget(self.lbl_hdr_pipeline)

        self.pipeline_bar = PipelineBar(self)
        lo.addWidget(self.pipeline_bar)

        # Legenda compacta com cores dos estágios
        self.lbl_pipeline_legend = QtWidgets.QLabel(
            "<span style='color:#38bdf8'>■</span>Kin "
            "<span style='color:#facc15'>■</span>Int "
            "<span style='color:#f97316'>■</span>Dab "
            "<span style='color:#a855f7'>■</span>Und "
            "<span style='color:#22c55e'>■</span>Cmp "
            "<span style='color:#ec4899'>■</span>Blt"
        )
        self.lbl_pipeline_legend.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_pipeline_legend.setStyleSheet("font-size: 9px; font-weight: bold;")
        lo.addWidget(self.lbl_pipeline_legend)

        lo.addSpacing(4)

        # 4. Linha Comparativa: C++ Motor vs Qt Blit
        self.lbl_hdr_motor_vs_blit = self._make_label("MOTOR C++ vs APRESENTAÇÃO QT")
        lo.addWidget(self.lbl_hdr_motor_vs_blit)
        self.lbl_motor_vs_blit = QtWidgets.QLabel("Motor: 0.00 µs | Blit Qt: 0.00 ms")
        self.lbl_motor_vs_blit.setStyleSheet("font-size: 11px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_motor_vs_blit)

        # 5. Linha de Frequências: Mesa (Hz) vs Tela (FPS)
        self.lbl_hdr_rates = self._make_label("FREQUÊNCIAS (ENTRADA / TELA)")
        lo.addWidget(self.lbl_hdr_rates)
        self.lbl_rates_val = QtWidgets.QLabel("Mesa: 0 Hz | Viewport: 0.0 FPS")
        self.lbl_rates_val.setStyleSheet("font-size: 11px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_rates_val)

        # 6. Linha de Pegada Geométrica: Dabs / Região Suja
        self.lbl_hdr_geom = self._make_label("DENSIDADE & REGIÃO SUJA")
        lo.addWidget(self.lbl_hdr_geom)
        self.lbl_geom_val = QtWidgets.QLabel("0 dabs | 0 × 0 px (0 tiles)")
        self.lbl_geom_val.setStyleSheet("font-size: 10px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_geom_val)

        lo.addSpacing(4)

        # 7. Indicador de Pressão
        self.lbl_hdr_pressure = self._make_label(tr("telemetry.pen_pressure", "PRESSÃO DA CANETA"))
        lo.addWidget(self.lbl_hdr_pressure)
        self.bar_pressure = QtWidgets.QProgressBar()
        self.bar_pressure.setRange(0, 100)
        self.bar_pressure.setValue(0)
        self.bar_pressure.setFixedHeight(10)
        self.bar_pressure.setTextVisible(False)
        self.lbl_pressure_val = QtWidgets.QLabel("0 %")
        self.lbl_pressure_val.setStyleSheet("font-size: 10px; font-weight: bold;")
        
        row_press = QtWidgets.QHBoxLayout()
        row_press.addWidget(self.bar_pressure, 1)
        row_press.addWidget(self.lbl_pressure_val)
        lo.addLayout(row_press)

        # 8. Indicador de Velocidade
        self.lbl_hdr_velocity = self._make_label(tr("telemetry.stroke_velocity", "VELOCIDADE DO TRAÇO"))
        lo.addWidget(self.lbl_hdr_velocity)
        self.bar_velocity = QtWidgets.QProgressBar()
        self.bar_velocity.setRange(0, 1000)
        self.bar_velocity.setValue(0)
        self.bar_velocity.setFixedHeight(10)
        self.bar_velocity.setTextVisible(False)
        self.lbl_velocity_val = QtWidgets.QLabel("0 px/s")
        self.lbl_velocity_val.setStyleSheet("font-size: 10px; font-weight: bold;")

        row_vel = QtWidgets.QHBoxLayout()
        row_vel.addWidget(self.bar_velocity, 1)
        row_vel.addWidget(self.lbl_velocity_val)
        lo.addLayout(row_vel)

        # 9. Memória (Canvas / Undo)
        self.lbl_hdr_ram = self._make_label(tr("telemetry.memory", "MEMÓRIA (CANVAS / UNDO)"))
        lo.addWidget(self.lbl_hdr_ram)
        self.lbl_ram_val = QtWidgets.QLabel("0.00 MB / 0.00 MB")
        self.lbl_ram_val.setStyleSheet("font-size: 11px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_ram_val)

        lo.addSpacing(6)

        # 10. Botões de Ação: Diagnóstico Avançado & Copiar Relatório
        btn_action_row = QtWidgets.QHBoxLayout()
        btn_action_row.setSpacing(6)

        self.btn_open_dialog = QtWidgets.QPushButton(f"⚙️ {tr('telemetry.advanced_dialog', 'Avançado...')}")
        self.btn_open_dialog.setObjectName("BtnOpenDialog")
        self.btn_open_dialog.setFixedHeight(28)
        self.btn_open_dialog.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_open_dialog.clicked.connect(self._open_diagnostics_dialog)
        btn_action_row.addWidget(self.btn_open_dialog)

        self.btn_copy_report = QtWidgets.QPushButton("📋 Copiar Relatório")
        self.btn_copy_report.setObjectName("BtnCopyReport")
        self.btn_copy_report.setFixedHeight(28)
        self.btn_copy_report.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_copy_report.setToolTip("Copia o relatório completo com 20 medidores do grid e histórico de alterações de estado")
        self.btn_copy_report.clicked.connect(self._on_copy_report)
        btn_action_row.addWidget(self.btn_copy_report)

        lo.addLayout(btn_action_row)

        lo.addStretch()

        card_box = PanelCardBox("", content, self)
        main_layout.addWidget(card_box)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self) -> None:
        from ui.core.i18n import tr
        if hasattr(self, "btn_toggle_telemetry"):
            if self._is_capturing:
                self.btn_toggle_telemetry.setText(f"🟢 {tr('telemetry.disable_capture', 'Desativar Captura')}")
            else:
                self.btn_toggle_telemetry.setText(f"⚪ {tr('telemetry.enable_capture', 'Ativar Captura de Telemetria')}")
            self.btn_toggle_telemetry.setToolTip(tr("telemetry.tooltip", "Ativa ou desativa a captura de métricas no motor C++ com liberação limpa de memória."))
        if hasattr(self, "lbl_status"):
            if self._is_capturing:
                self.lbl_status.setText(f"{tr('telemetry.status', 'Status')}: {tr('telemetry.capturing', 'Capturando métricas (30 FPS)')}")
            else:
                self.lbl_status.setText(f"{tr('telemetry.status', 'Status')}: {tr('telemetry.idle', 'Em Espera')} (0% {tr('telemetry.overhead', 'Sobrecarga')})")
        if hasattr(self, "lbl_hdr_pressure"):
            self.lbl_hdr_pressure.setText(tr("telemetry.pen_pressure", "PRESSÃO DA CANETA"))
        if hasattr(self, "lbl_hdr_velocity"):
            self.lbl_hdr_velocity.setText(tr("telemetry.stroke_velocity", "VELOCIDADE DO TRAÇO"))
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
            self.retranslate_ui()
            tm = ThemeManager.instance()
            self.lbl_status.setStyleSheet(f"color: {tm.get_color('success')}; font-weight: bold; font-size: 10px;")
            self._timer.start()
        else:
            if backend and hasattr(backend, "set_telemetry_enabled"):
                backend.set_telemetry_enabled(False)
            self._timer.stop()
            self.retranslate_ui()
            tm = ThemeManager.instance()
            self.lbl_status.setStyleSheet(f"color: {tm.get_color('text_sec')}; font-size: 10px;")
            # Reseta os medidores para estado de repouso
            self.bar_pressure.setValue(0)
            self.lbl_pressure_val.setText("0 %")
            self.bar_velocity.setValue(0)
            self.lbl_velocity_val.setText("0 px/s")
            self.lbl_motor_vs_blit.setText("Motor: 0.00 µs | Blit Qt: 0.00 ms")
            self.lbl_rates_val.setText("Mesa: 0 Hz | Viewport: 0.0 FPS")
            self.lbl_geom_val.setText("0 dabs | 0 × 0 px (0 tiles)")
            self.lbl_ram_val.setText("0.00 MB / 0.00 MB")
            self.pipeline_bar.set_values_us(0, 0, 0, 0, 0, 0)
            self._update_bottleneck_banner(0, 0, 0, 0)

    def _update_telemetry(self) -> None:
        if not self._is_capturing:
            return

        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return

        # Snapshot da Viewport Qt
        vp = EngineRegistry.get_viewport_telemetry()
        blit_ms = vp.get("qt_draw_image_ms", 0.0)
        vp_fps = vp.get("qt_fps", 0.0)
        blit_us = blit_ms * 1000.0

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

                kin_us = getattr(snap, "time_kinematics_us", 0.0)
                int_us = getattr(snap, "time_interpolation_us", 0.0)
                dab_us = getattr(snap, "time_raster_dab_us", 0.0)
                und_us = getattr(snap, "time_undo_record_us", 0.0)
                cmp_us = getattr(snap, "time_composite_us", 0.0)

                # Atualiza a barra de estágios
                self.pipeline_bar.set_values_us(kin_us, int_us, dab_us, und_us, cmp_us, blit_us)

                # Motor vs Blit
                self.lbl_motor_vs_blit.setText(f"Motor: {snap.last_segment_latency_us:.1f} µs | Blit Qt: {blit_ms:.2f} ms")

                # Frequências
                self.lbl_rates_val.setText(f"Mesa: {snap.input_event_rate_hz} Hz | Viewport: {vp_fps:.1f} FPS")

                # Densidade e pegada
                dabs_rendered = getattr(snap, "last_dabs_rendered", 0)
                dw = int(getattr(snap, "last_dirty_width", 0.0))
                dh = int(getattr(snap, "last_dirty_height", 0.0))
                tiles_rec = getattr(snap, "last_tiles_recorded", 0)
                self.lbl_geom_val.setText(f"{dabs_rendered} dabs | {dw}×{dh} px ({tiles_rec} tiles)")

                # Memória
                self.lbl_ram_val.setText(f"{snap.tile_grid_memory_mb:.2f} MB / {snap.undo_stack_memory_mb:.2f} MB")

                # Banner de diagnóstico de gargalos
                self._update_bottleneck_banner(dab_us, und_us, cmp_us, blit_ms)

                # Atualiza o TelemetryTracker global com o snapshot
                from ui.core.engine.telemetry_tracker import TelemetryTracker
                TelemetryTracker.instance().update(snap, vp)
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

    def _update_bottleneck_banner(self, dab_us: float, und_us: float, cmp_us: float, blit_ms: float) -> None:
        """Atualiza a cor e o diagnóstico do banner conforme o estágio mais custoso."""
        if not self._is_capturing:
            self.lbl_bottleneck.setText("⚪ TELEMETRIA PAUSADA")
            self.lbl_bottleneck.setStyleSheet("background-color: rgba(255,255,255,0.05); color: #9ca3af; border: 1px solid #4b5563; border-radius: 4px; font-size: 9px; font-weight: bold;")
            return

        from ui.core.engine.telemetry_tracker import TelemetryTracker
        tracker = TelemetryTracker.instance()
        state_key = tracker._current_state_key
        state_str = tracker._current_state_str

        if state_key == "GARGALO_BLIT":
            self.lbl_bottleneck.setText("⚠️ GARGALO: BLIT QT LENTO (>16ms)")
            self.lbl_bottleneck.setStyleSheet("background-color: rgba(239,68,68,0.2); color: #f87171; border: 1px solid #ef4444; border-radius: 4px; font-size: 9px; font-weight: bold;")
        elif state_key == "GARGALO_RASTER":
            self.lbl_bottleneck.setText("⚠️ GARGALO: RASTER DAB (>15ms)")
            self.lbl_bottleneck.setStyleSheet("background-color: rgba(249,115,22,0.2); color: #fb923c; border: 1px solid #f97316; border-radius: 4px; font-size: 9px; font-weight: bold;")
        elif state_key == "GARGALO_UNDO":
            self.lbl_bottleneck.setText("⚠️ GARGALO: GRAVAÇÃO UNDO (>10ms)")
            self.lbl_bottleneck.setStyleSheet("background-color: rgba(168,85,247,0.2); color: #c084fc; border: 1px solid #a855f7; border-radius: 4px; font-size: 9px; font-weight: bold;")
        elif state_key == "GARGALO_COMPOSITOR":
            self.lbl_bottleneck.setText("⚠️ GARGALO: COMPOSITOR (>10ms)")
            self.lbl_bottleneck.setStyleSheet("background-color: rgba(34,197,94,0.2); color: #4ade80; border: 1px solid #22c55e; border-radius: 4px; font-size: 9px; font-weight: bold;")
        else:
            self.lbl_bottleneck.setText("✅ PIPELINE EQUILIBRADO (< 2ms)")
            self.lbl_bottleneck.setStyleSheet("background-color: rgba(16,185,129,0.15); color: #34d399; border: 1px solid #10b981; border-radius: 4px; font-size: 9px; font-weight: bold;")

        self.lbl_bottleneck.setToolTip(f"Estado Atual: {state_str}\nClique para ver o histórico no Cockpit (F12).")

    def _on_copy_report(self) -> None:
        """Copia o relatório completo com 20 medidores e histórico de transições."""
        from ui.core.engine.telemetry_tracker import TelemetryTracker
        report = TelemetryTracker.instance().generate_full_report()
        QtWidgets.QApplication.clipboard().setText(report)
        QtWidgets.QMessageBox.information(
            self,
            "Relatório de Telemetria Copiado",
            "Relatório completo de telemetria (incluindo todos os 20 medidores do Grid, "
            "diagnóstico do pipeline, picos de estresse e histórico de alterações de estado) "
            "foi copiado para a Área de Transferência com sucesso!"
        )

    def _open_grid_window(self) -> None:
        from ui.core.dialogs.telemetry_grid_window import TelemetryGridWindow
        if not hasattr(self, "_grid_window") or self._grid_window is None or not self._grid_window.isVisible():
            self._grid_window = TelemetryGridWindow(self.window())
        self._grid_window.show()
        self._grid_window.raise_()
        self._grid_window.activateWindow()

    def _open_diagnostics_dialog(self) -> None:
        dlg = TelemetryDiagnosticsDialog(self.window())
        dlg.exec()
    def _apply_theme(self, *args) -> None:
        from .panel_theme import apply_telemetry_panel_theme
        apply_telemetry_panel_theme(self)

