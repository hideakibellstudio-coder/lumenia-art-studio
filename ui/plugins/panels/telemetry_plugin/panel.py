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
from ui.infrastructure.theme.manager import ThemeManager
from ui.infrastructure.icons import get_icon
from ui.core.engine.registry import EngineRegistry
from ui.core.engine.telemetry_meters import presentation_ms
from ui.core.engine.telemetry_tracker import TelemetryTracker
from ui.core.dialogs.telemetry_common import banner_style, copy_report
from ui.core.dialogs.telemetry_diagnostics_dialog import TelemetryDiagnosticsDialog
from ui.core.dialogs.telemetry_grid_window import TelemetryGridWindow
from ui.infrastructure.i18n import I18nManager, tr
from ui.core.widgets.pipeline_bar import PipelineBar

# Texto curto do banner (a doca é estreita) por estado do TelemetryTracker.
_BANNER_TEXTS = {
    "PIPELINE_EQUILIBRADO": "PIPELINE EQUILIBRADO (< 2ms)",
    "GARGALO_BLIT": "GARGALO: BLIT QT (>16ms)",
    "GARGALO_RASTER": "GARGALO: RASTER DAB (>15ms)",
    "GARGALO_UNDO": "GARGALO: GRAVAÇÃO UNDO (>10ms)",
    "GARGALO_COMPOSITOR": "GARGALO: COMPOSITOR (>10ms)",
}


class TelemetryPanel(QtWidgets.QWidget):
    """Painel de telemetria acoplável em docas com switch limpo de ciclo de vida."""

    def __init__(self, parent: QtWidgets.QWidget | None = None, auto_start: bool = False) -> None:
        super().__init__(parent)
        self.setObjectName("TelemetryPanel")
        self.setMaximumWidth(int(280 * ThemeManager.instance().ui_scale))
        self._is_capturing = auto_start
        self._grid_window: Optional[TelemetryGridWindow] = None

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS polling desacoplado
        self._timer.timeout.connect(self._update_telemetry)

        self._build_ui()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)
        ThemeManager.instance().scaleChanged.connect(self._apply_theme)
        self._apply_theme()
        self._show_state()

        if self._is_capturing:
            TelemetryTracker.instance().enable_capture()
            self._timer.start()

    def _build_ui(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)

        content = QtWidgets.QWidget()
        lo = QtWidgets.QVBoxLayout(content)
        lo.setContentsMargins(8, 8, 8, 8)
        lo.setSpacing(6)

        # Botão Destaque: Cockpit em Grid (Janela Flutuante)
        self.btn_open_grid = QtWidgets.QPushButton("Cockpit em Grid (F12)")
        self.btn_open_grid.setObjectName("BtnOpenGrid")
        self.btn_open_grid.setIcon(get_icon("grid", ThemeManager.instance().get_color("text_main")))
        self.btn_open_grid.setFixedHeight(32)
        self.btn_open_grid.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_open_grid.setToolTip("Abre o cockpit flutuante com todos os 20 medidores em tempo real (F12)")
        self.btn_open_grid.clicked.connect(self._open_grid_window)
        lo.addWidget(self.btn_open_grid)

        # 1. Botão Mestre de Ativação / Desativação
        btn_text = tr('telemetry.disable_capture', 'Desativar Telemetria') if self._is_capturing else tr('telemetry.enable_capture', 'Ativar Telemetria')
        self.btn_toggle_telemetry = QtWidgets.QPushButton(btn_text)
        self.btn_toggle_telemetry.setObjectName("BtnToggleTelemetry")
        self.btn_toggle_telemetry.setIcon(get_icon(
            "check_circle" if self._is_capturing else "zap",
            ThemeManager.instance().get_color("success") if self._is_capturing else ThemeManager.instance().get_color("text_sec"),
        ))
        self.btn_toggle_telemetry.setFixedHeight(30)
        self.btn_toggle_telemetry.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_toggle_telemetry.setToolTip(tr("telemetry.tooltip", "Ativa ou desativa a captura de métricas no motor C++ com liberação limpa de memória."))
        self.btn_toggle_telemetry.clicked.connect(self._on_toggle_capture)
        lo.addWidget(self.btn_toggle_telemetry)

        status_text = f"{tr('telemetry.status', 'Status')}: {tr('telemetry.capturing', 'Capturando (30 FPS)')}" if self._is_capturing else f"{tr('telemetry.status', 'Status')}: {tr('telemetry.idle', 'Em Espera')} (0% Carga)"
        self.lbl_status = QtWidgets.QLabel(status_text)
        self.lbl_status.setObjectName("TelemStatus")
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        if self._is_capturing:
            _success_c = ThemeManager.instance().get_color("SUCCESS", "#10b981")
            self.lbl_status.setStyleSheet(f"color: {_success_c}; font-weight: bold; font-size: 10px;")
        lo.addWidget(self.lbl_status)

        # 2. Banner de Diagnóstico de Gargalos (Bottleneck Alert)
        self.lbl_bottleneck = QtWidgets.QLabel()
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
        tm_legend = ThemeManager.instance()
        c_stage_kin = tm_legend.get_color("TELEMETRY_STAGE_KINEMATICS", "#38bdf8")
        c_stage_int = tm_legend.get_color("TELEMETRY_STAGE_INTERPOLATION", "#facc15")
        c_stage_dab = tm_legend.get_color("TELEMETRY_STAGE_RASTER", "#f97316")
        c_stage_und = tm_legend.get_color("TELEMETRY_STAGE_UNDO", "#a855f7")
        c_stage_cmp = tm_legend.get_color("TELEMETRY_STAGE_COMPOSITOR", "#22c55e")
        c_stage_blt = tm_legend.get_color("TELEMETRY_STAGE_BLIT", "#ec4899")
        self.lbl_pipeline_legend = QtWidgets.QLabel(
            f"<span style='color:{c_stage_kin}'>■</span>Kin "
            f"<span style='color:{c_stage_int}'>■</span>Int "
            f"<span style='color:{c_stage_dab}'>■</span>Dab "
            f"<span style='color:{c_stage_und}'>■</span>Und "
            f"<span style='color:{c_stage_cmp}'>■</span>Cmp "
            f"<span style='color:{c_stage_blt}'>■</span>Blt"
        )
        self.lbl_pipeline_legend.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_pipeline_legend.setStyleSheet("font-size: 9px; font-weight: bold;")
        lo.addWidget(self.lbl_pipeline_legend)

        lo.addSpacing(4)

        # 4. Linha Comparativa: C++ Motor vs Qt Blit
        self.lbl_hdr_motor_vs_blit = self._make_label("MOTOR C++ vs APRESENTAÇÃO QT")
        lo.addWidget(self.lbl_hdr_motor_vs_blit)
        self.lbl_motor_vs_blit = QtWidgets.QLabel("C++: 0.0 µs • Qt: 0.00 ms")
        self.lbl_motor_vs_blit.setStyleSheet("font-size: 10px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_motor_vs_blit)

        # 5. Linha de Frequências: Mesa (Hz) vs Tela (FPS)
        self.lbl_hdr_rates = self._make_label("FREQUÊNCIAS (ENTRADA / TELA)")
        lo.addWidget(self.lbl_hdr_rates)
        self.lbl_rates_val = QtWidgets.QLabel("Mesa: 0 Hz • Tela: 0 FPS")
        self.lbl_rates_val.setStyleSheet("font-size: 10px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_rates_val)

        # 6. Linha de Pegada Geométrica: Dabs / Região Suja
        self.lbl_hdr_geom = self._make_label("DENSIDADE & REGIÃO SUJA")
        lo.addWidget(self.lbl_hdr_geom)
        self.lbl_geom_val = QtWidgets.QLabel("0 dabs • 0×0 px (0 t)")
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
        self.lbl_ram_val = QtWidgets.QLabel("Canvas: 0.0 MB • Undo: 0.0 MB")
        self.lbl_ram_val.setStyleSheet("font-size: 10px; font-weight: bold; font-family: monospace;")
        lo.addWidget(self.lbl_ram_val)

        lo.addSpacing(6)

        # 10. Botões de Ação: Diagnóstico Avançado & Copiar Relatório
        btn_action_row = QtWidgets.QHBoxLayout()
        btn_action_row.setSpacing(6)

        self.btn_open_dialog = QtWidgets.QPushButton(tr('telemetry.advanced_dialog', 'Avançado'))
        self.btn_open_dialog.setObjectName("BtnOpenDialog")
        self.btn_open_dialog.setIcon(get_icon("settings", ThemeManager.instance().get_color("text_main")))
        self.btn_open_dialog.setFixedHeight(28)
        self.btn_open_dialog.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn_open_dialog.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_open_dialog.clicked.connect(self._open_diagnostics_dialog)
        btn_action_row.addWidget(self.btn_open_dialog)

        self.btn_copy_report = QtWidgets.QPushButton("Copiar")
        self.btn_copy_report.setObjectName("BtnCopyReport")
        self.btn_copy_report.setIcon(get_icon("copy", ThemeManager.instance().get_color("text_main")))
        self.btn_copy_report.setFixedHeight(28)
        self.btn_copy_report.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        self.btn_copy_report.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_copy_report.setToolTip("Copia o relatório completo com 20 medidores do grid e histórico de alterações de estado")
        self.btn_copy_report.clicked.connect(lambda: copy_report(self))
        btn_action_row.addWidget(self.btn_copy_report)

        lo.addLayout(btn_action_row)

        lo.addStretch()

        card_box = PanelCardBox("", content, self)
        main_layout.addWidget(card_box)

        I18nManager.instance().languageChanged.connect(self.retranslate_ui)

    def retranslate_ui(self) -> None:
        tm_rt = ThemeManager.instance()
        if self._is_capturing:
            self.btn_toggle_telemetry.setText(tr('telemetry.disable_capture', 'Desativar Telemetria'))
            self.btn_toggle_telemetry.setIcon(get_icon("check_circle", tm_rt.get_color("success")))
            self.lbl_status.setText(f"{tr('telemetry.status', 'Status')}: {tr('telemetry.capturing', 'Capturando (30 FPS)')}")
        else:
            self.btn_toggle_telemetry.setText(tr('telemetry.enable_capture', 'Ativar Telemetria'))
            self.btn_toggle_telemetry.setIcon(get_icon("zap", tm_rt.get_color("text_sec")))
            self.lbl_status.setText(f"{tr('telemetry.status', 'Status')}: {tr('telemetry.idle', 'Em Espera')} (0% {tr('telemetry.overhead', 'Carga')})")
        self.btn_toggle_telemetry.setToolTip(tr("telemetry.tooltip", "Ativa ou desativa a captura de métricas no motor C++ com liberação limpa de memória."))
        self.lbl_hdr_pressure.setText(tr("telemetry.pen_pressure", "PRESSÃO DA CANETA"))
        self.lbl_hdr_velocity.setText(tr("telemetry.stroke_velocity", "VELOCIDADE DO TRAÇO"))
        self.lbl_hdr_ram.setText(tr("telemetry.memory", "MEMÓRIA (CANVAS / UNDO)"))
        self.btn_open_dialog.setText(tr('telemetry.advanced_dialog', 'Avançado'))

    def _make_label(self, text: str) -> QtWidgets.QLabel:
        lbl = QtWidgets.QLabel(text)
        lbl.setObjectName("TelemLabel")
        return lbl

    def _on_toggle_capture(self) -> None:
        self._is_capturing = not self._is_capturing
        tracker = TelemetryTracker.instance()

        if self._is_capturing:
            tracker.enable_capture()
            self.retranslate_ui()
            tm = ThemeManager.instance()
            self.lbl_status.setStyleSheet(f"color: {tm.get_color('success')}; font-weight: bold; font-size: 10px;")
            self._timer.start()
        else:
            tracker.enable_capture(False)
            self._timer.stop()
            self.retranslate_ui()
            tm = ThemeManager.instance()
            self.lbl_status.setStyleSheet(f"color: {tm.get_color('text_sec')}; font-size: 10px;")
            # Reseta os medidores para estado de repouso
            self.bar_pressure.setValue(0)
            self.lbl_pressure_val.setText("0 %")
            self.bar_velocity.setValue(0)
            self.lbl_velocity_val.setText("0 px/s")
            self.lbl_motor_vs_blit.setText("C++: 0.0 µs • Qt: 0.00 ms")
            self.lbl_rates_val.setText("Mesa: 0 Hz • Tela: 0 FPS")
            self.lbl_geom_val.setText("0 dabs • 0×0 px (0 t)")
            self.lbl_ram_val.setText("Canvas: 0.0 MB • Undo: 0.0 MB")
            self.pipeline_bar.set_values_us(0, 0, 0, 0, 0, 0)
            self._show_state()

    def _update_telemetry(self) -> None:
        if not self._is_capturing:
            return
        snap = TelemetryTracker.instance().read_snapshot()
        if snap is None:
            return

        vp = EngineRegistry.get_viewport_telemetry()
        blit_ms = presentation_ms(vp)
        # O tracker primeiro: o banner mostra o estado desta leitura, não o da anterior.
        TelemetryTracker.instance().update(snap, vp)

        press_pct = int(snap.raw_pressure * 100)
        self.bar_pressure.setValue(min(100, max(0, press_pct)))
        self.lbl_pressure_val.setText(f"{press_pct} %")
        vel_val = int(snap.stroke_velocity)
        self.bar_velocity.setValue(min(1000, max(0, vel_val)))
        self.lbl_velocity_val.setText(f"{vel_val} px/s")

        self.pipeline_bar.set_values_us(
            snap.time_kinematics_us, snap.time_interpolation_us, snap.time_raster_dab_us,
            snap.time_undo_record_us, snap.time_composite_us, blit_ms * 1000.0)
        self.lbl_motor_vs_blit.setText(f"C++: {snap.last_segment_latency_us:.1f} µs • Qt: {blit_ms:.2f} ms")
        self.lbl_rates_val.setText(f"Mesa: {snap.input_event_rate_hz} Hz • Tela: {vp.get('qt_fps', 0.0):.0f} FPS")
        self.lbl_geom_val.setText(
            f"{snap.last_dabs_rendered} dabs • {int(snap.last_dirty_width)}×{int(snap.last_dirty_height)} px "
            f"({snap.last_tiles_recorded} t)")
        self.lbl_ram_val.setText(
            f"Canvas: {snap.tile_grid_memory_mb:.1f} MB • Undo: {snap.undo_stack_memory_mb:.1f} MB")
        self._show_state()

    def _show_state(self) -> None:
        """Banner de diagnóstico: estado do TelemetryTracker (ou pausado)."""
        if not self._is_capturing:
            tm = ThemeManager.instance()
            self.lbl_bottleneck.setText("TELEMETRIA PAUSADA")
            idle_c = tm.get_color("FG_SECONDARY", "#9ca3af")
            idle_border = tm.get_color("BORDER", "#4b5563")
            idle_qc = QtGui.QColor(idle_c)
            idle_bg = f"rgba({idle_qc.red()},{idle_qc.green()},{idle_qc.blue()},0.08)"
            self.lbl_bottleneck.setStyleSheet(f"background-color: {idle_bg}; color: {idle_c}; border: 1px solid {idle_border}; border-radius: 4px; font-size: 9px; font-weight: bold;")
            return
        tracker = TelemetryTracker.instance()
        self.lbl_bottleneck.setText(_BANNER_TEXTS.get(tracker.current_state_key, tracker.current_state_str))
        self.lbl_bottleneck.setStyleSheet(banner_style(tracker.current_state_key, font_px=9))
        self.lbl_bottleneck.setToolTip(
            f"Estado Atual: {tracker.current_state_str}\nClique para ver o histórico no Cockpit (F12).")

    def _open_grid_window(self) -> None:
        if self._grid_window is None or not self._grid_window.isVisible():
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

