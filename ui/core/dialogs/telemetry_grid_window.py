"""
TelemetryGridWindow — Cockpit de Telemetria e Diagnóstico em Grid do ALADYN ENGINE
==================================================================================
Janela flutuante não-modal (modeless) para auditoria e diagnóstico em tempo real:
- Permite desenhar livremente no canvas enquanto os medidores atualizam a 60 FPS
- Suporte a fixação no topo (Stay on Top) para monitoramento simultâneo
- Grid responsivo de 20 medidores cobrindo todos os estágios do pipeline nativo C++
- Banner inteligente de detecção de gargalos e barra empilhada proporcional
"""

from __future__ import annotations

import time
from typing import Optional
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.engine.registry import EngineRegistry
from ui.core.theme.manager import ThemeManager
from ui.core.widgets.pipeline_bar import PipelineBar
from ui.core.widgets.metric_card import GridMetricCard
from ui.core.engine.telemetry_dto import TelemetrySnapshot
from ui.core.dialogs.telemetry_grid_report import (
    TelemetryStateHistoryDialog,
    TelemetryReportGenerator,
)
from ui.core.icons import get_icon

__all__ = ["GridMetricCard", "TelemetryGridWindow"]


class TelemetryGridWindow(BaseFramelessDialog):
    """Cockpit não-modal de telemetria com medidores distribuídos em grid e suporte a Stay-on-Top."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(
            title="Cockpit de Telemetria & Diagnóstico em Grid",
            icon_name="chart",
            parent=parent,
            modal=False,  # Não-modal: permite desenhar e inspecionar simultaneamente
        )
        self.setObjectName("TelemetryGridWindow")
        self.resize(960, 640)
        self.setMinimumSize(820, 520)

        self._stay_on_top = True
        self._apply_stay_on_top(True)
        self._init_state_tracking()
        self._record_state_transition(
            new_state="PIPELINE EQUILIBRADO (< 2ms)",
            state_key="PIPELINE_EQUILIBRADO",
            cause="Inicialização do Cockpit de Telemetria",
        )

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS para monitoramento fluido
        self._timer.timeout.connect(self._refresh_metrics)

        self._build_content()
        self._timer.start()
        self._ensure_telemetry_enabled()

    def _init_state_tracking(self) -> None:
        self._current_state_key = "PIPELINE_EQUILIBRADO"
        self._current_state_str = "PIPELINE EQUILIBRADO (< 2ms)"
        self._state_history: list[dict[str, str]] = []
        self._state_counts: dict[str, int] = {
            "PIPELINE_EQUILIBRADO": 1, "GARGALO_RASTER": 0, "GARGALO_BLIT": 0,
            "GARGALO_UNDO": 0, "GARGALO_COMPOSITOR": 0,
        }
        self._peaks: dict[str, float] = {
            "motor_latency_us": 0.0, "raster_dab_us": 0.0, "undo_record_us": 0.0,
            "composite_us": 0.0, "kinematics_us": 0.0, "interpolation_us": 0.0,
            "blit_ms": 0.0, "stroke_velocity": 0.0, "stabilizer_lag_px": 0.0,
            "dabs_per_second": 0.0, "dirty_area_px": 0.0, "tiles_recorded": 0, "min_fps": 60.0,
        }
        self._last_active_pen: dict[str, float] = {
            "raw_pressure": 0.0, "dynamic_pressure": 0.0, "velocity": 0.0, "stabilizer_lag": 0.0,
        }

    @property
    def current_state_key(self) -> str:
        """Identificador textual canônico do estado do pipeline."""
        return self._current_state_key

    @property
    def current_state_str(self) -> str:
        """Descrição formatada do estado do pipeline."""
        return self._current_state_str

    def _ensure_telemetry_enabled(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "set_telemetry_enabled"):
            backend.set_telemetry_enabled(True)

    def _apply_stay_on_top(self, stay: bool) -> None:
        flags = self.windowFlags()
        if stay:
            flags |= QtCore.Qt.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _build_content(self) -> None:
        lo = self.content_layout
        lo.setContentsMargins(14, 8, 14, 12)
        lo.setSpacing(8)
        tm = ThemeManager.instance()
        c_success = tm.get_color("SUCCESS", "#34d399")

        # Barra de Controles do Topo
        ctrl_bar = QtWidgets.QHBoxLayout()
        ctrl_bar.setSpacing(8)

        self.lbl_status_pill = QtWidgets.QLabel(f"<span style='color:{c_success}'>\u25CF</span> CAPTURA ATIVA (60 FPS)")
        self.lbl_status_pill.setStyleSheet(f"""
            background-color: rgba(16, 185, 129, 0.15); color: {c_success};
            font-size: 10px; font-weight: bold; padding: 4px 8px;
            border-radius: 4px; border: 1px solid rgba(16, 185, 129, 0.3);
        """)
        ctrl_bar.addWidget(self.lbl_status_pill)
        ctrl_bar.addStretch()

        text_main = tm.get_color("text_main")
        btns = [
            ("btn_pin", "pin", "Sempre no Topo: SIM", self._on_toggle_pin, True),
            ("btn_reset", "reset", "Resetar Métricas", self._on_reset_metrics, False),
            ("btn_copy", "copy", "Copiar Relatório", self._on_copy_report, False),
            ("btn_clear_undo", "trash", "Limpar Undo", self._on_clear_undo, False),
        ]
        for attr, icon_name, text, slot, is_bold in btns:
            b = QtWidgets.QPushButton(text)
            b.setIcon(get_icon(icon_name, text_main))
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setFixedHeight(26)
            b.setStyleSheet(f"font-size: 10px; {'font-weight: bold; ' if is_bold else ''}padding: 2px 10px;")
            b.clicked.connect(slot)
            setattr(self, attr, b)
            ctrl_bar.addWidget(b)
        lo.addLayout(ctrl_bar)

        # Banner de Diagnóstico
        self.lbl_bottleneck = QtWidgets.QLabel("PIPELINE EQUILIBRADO (< 2ms)")
        self.lbl_bottleneck.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_bottleneck.setFixedHeight(24)
        self.lbl_bottleneck.setCursor(QtCore.Qt.PointingHandCursor)
        self.lbl_bottleneck.setToolTip("Clique para visualizar o Histórico de Alterações de Estado.")
        self.lbl_bottleneck.mousePressEvent = lambda e: self._show_state_history_dialog()
        self.lbl_bottleneck.setStyleSheet(f"""
            background-color: rgba(16, 185, 129, 0.15); color: {c_success};
            border: 1px solid {c_success}; border-radius: 4px; font-size: 10px;
            font-weight: bold; letter-spacing: 0.5px;
        """)
        lo.addWidget(self.lbl_bottleneck)

        # Barra Proporcional de Estágios
        self.pipeline_bar = PipelineBar(self)
        self.pipeline_bar.setFixedHeight(14)
        lo.addWidget(self.pipeline_bar)

        c_stage_kin = tm.get_color("TELEMETRY_STAGE_KINEMATICS", "#38bdf8")
        c_stage_int = tm.get_color("TELEMETRY_STAGE_INTERPOLATION", "#facc15")
        c_stage_dab = tm.get_color("TELEMETRY_STAGE_RASTER", "#f97316")
        c_stage_und = tm.get_color("TELEMETRY_STAGE_UNDO", "#a855f7")
        c_stage_cmp = tm.get_color("TELEMETRY_STAGE_COMPOSITOR", "#22c55e")
        c_stage_blt = tm.get_color("TELEMETRY_STAGE_BLIT", "#ec4899")

        self.lbl_legend = QtWidgets.QLabel(
            f"<span style='color:{c_stage_kin}'>■</span> Cinemática &nbsp;&nbsp;"
            f"<span style='color:{c_stage_int}'>■</span> Interpolação &nbsp;&nbsp;"
            f"<span style='color:{c_stage_dab}'>■</span> RasterDab &nbsp;&nbsp;"
            f"<span style='color:{c_stage_und}'>■</span> Gravação Undo &nbsp;&nbsp;"
            f"<span style='color:{c_stage_cmp}'>■</span> Compositor &nbsp;&nbsp;"
            f"<span style='color:{c_stage_blt}'>■</span> Apresentação Blit Qt"
        )
        self.lbl_legend.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_legend.setStyleSheet("font-size: 9px; font-weight: bold;")
        lo.addWidget(self.lbl_legend)

        # Grid Principal de 20 Medidores (4 Colunas x 5 Linhas)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        grid_container = QtWidgets.QWidget()
        grid_lo = QtWidgets.QGridLayout(grid_container)
        grid_lo.setContentsMargins(0, 4, 0, 4)
        grid_lo.setSpacing(8)

        cards_spec = [
            ("c_kin", "1. Cinemática / Dinâmica", "Filtro de caneta e velocidade", c_stage_kin, 0, 0, False, 100),
            ("c_int", "2. Interpolação Dabs", "Espaçamento e resíduo", c_stage_int, 0, 1, False, 100),
            ("c_dab", "3. RasterDab (Shaders)", "SIMD AVX2 de ponta e papel", c_stage_dab, 0, 2, False, 100),
            ("c_und", "4. Gravação de Undo", "Cópia de blocos 128x128", c_stage_und, 0, 3, False, 100),
            ("c_cmp", "5. Compositor de Camadas", "Mesclagem SSE2 na região", c_stage_cmp, 1, 0, False, 100),
            ("c_blt", "6. Apresentação Blit Qt", "QPainter.drawImage na tela", c_stage_blt, 1, 1, False, 100),
            ("c_lat", "7. Latência Total Motor", "Tempo de micro-evento C++", c_stage_kin, 1, 2, False, 100),
            ("c_fps", "8. Taxa Real da Viewport", "Taxa efetiva de redesenho", c_success, 1, 3, False, 100),
            ("c_hz", "9. Frequência da Mesa", "Taxa de eventos do hardware", "#06b6d4", 2, 0, False, 100),
            ("c_dabs_sec", "10. Taxa de Carimbos", "Rendimento do rasterizador", "#f59e0b", 2, 1, False, 100),
            ("c_dabs", "11. Dabs Emitidos", "Último micro-evento", "#eab308", 2, 2, False, 100),
            ("c_dirty", "12. Região Suja Repintada", "Bounding box atual", c_stage_blt, 2, 3, False, 100),
            ("c_area", "13. Área Suja do Evento", "Superfície de pixels repintada", "#8b5cf6", 3, 0, False, 100),
            ("c_tiles", "14. Blocos Gravados / Total", "Blocos 128x128 em RAM", "#6366f1", 3, 1, False, 100),
            ("c_ram_canvas", "15. RAM do Canvas", "Memória dos tiles do documento", "#14b8a6", 3, 2, False, 100),
            ("c_ram_undo", "16. RAM do Histórico Undo", "0 passos de desfazer", c_stage_blt, 3, 3, False, 100),
            ("c_press", "17. Pressão Física vs Curva", "Modulada: 0 %", "#3b82f6", 4, 0, True, 100),
            ("c_vel", "18. Velocidade do Traço", "Velocidade vetorial", c_stage_dab, 4, 1, True, 1500),
            ("c_lag", "19. Lag do Estabilizador", "Distância do filtro inercial", c_stage_und, 4, 2, False, 100),
            ("c_hw", "20. Aceleração & Mini-Motor", "Mini-motor C++ ativo", c_success, 4, 3, False, 100),
        ]
        self._cards = []
        for attr, title, sub, col, r, c, bar, bmax in cards_spec:
            card = GridMetricCard(title, "0.0 µs" if ("µs" in sub or "ms" in sub) else "0", sub, col, show_bar=bar, bar_max=bmax)
            setattr(self, attr, card)
            self._cards.append(card)
            grid_lo.addWidget(card, r, c)

        scroll.setWidget(grid_container)
        lo.addWidget(scroll, 1)

    def _on_toggle_pin(self) -> None:
        self._stay_on_top = not self._stay_on_top
        self.btn_pin.setText(f"Sempre no Topo: {'SIM' if self._stay_on_top else 'NÃO'}")
        self.btn_pin.setIcon(get_icon("pin" if self._stay_on_top else "pin_off", ThemeManager.instance().get_color("text_main")))
        pos = self.pos()
        self._apply_stay_on_top(self._stay_on_top)
        self.move(pos)
        self.show()

    def _record_state_transition(self, new_state: str, state_key: str, cause: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        ms_part = int((time.time() % 1) * 1000)
        transition = {
            "time": f"{timestamp}.{ms_part:03d}",
            "from_state": getattr(self, "_current_state_str", "INDEFINIDO"),
            "to_state": new_state,
            "state_key": state_key,
            "cause": cause,
        }
        self._state_history.append(transition)
        if len(self._state_history) > 200:
            self._state_history.pop(0)

        self._state_counts[state_key] = self._state_counts.get(state_key, 0) + 1
        self._current_state_key = state_key
        self._current_state_str = new_state

    def _show_state_history_dialog(self) -> None:
        dlg = TelemetryStateHistoryDialog(self._state_counts, self._state_history, parent=self)
        dlg.exec()

    def _on_reset_metrics(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "reset_telemetry"):
            backend.reset_telemetry()
        self._init_state_tracking()
        self._record_state_transition(
            new_state="PIPELINE EQUILIBRADO (< 2ms)",
            state_key="PIPELINE_EQUILIBRADO",
            cause="Métricas e contadores resetados pelo usuário",
        )
        self._refresh_metrics()

    def _on_clear_undo(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "_redo_stack") and hasattr(backend, "_action_stack"):
            backend._action_stack.clear()
            backend._redo_stack.clear()
        QtWidgets.QMessageBox.information(self, "Memória", "Pilha de histórico e desfazer limpa com sucesso.")

    def _refresh_metrics(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return
        tm = ThemeManager.instance()

        vp = EngineRegistry.get_viewport_telemetry()
        blit_ms = vp.get("qt_draw_image_ms", 0.0)
        vp_fps = vp.get("qt_fps", 0.0)
        blit_us = blit_ms * 1000.0

        if not hasattr(backend, "get_telemetry_snapshot"):
            return
        snap: TelemetrySnapshot = backend.get_telemetry_snapshot()
        if not snap:
            return

        kin_us = getattr(snap, "time_kinematics_us", 0.0)
        int_us = getattr(snap, "time_interpolation_us", 0.0)
        dab_us = getattr(snap, "time_raster_dab_us", 0.0)
        und_us = getattr(snap, "time_undo_record_us", 0.0)
        cmp_us = getattr(snap, "time_composite_us", 0.0)
        lat_us = getattr(snap, "last_segment_latency_us", 0.0)
        vel = getattr(snap, "stroke_velocity", 0.0)
        lag = getattr(snap, "stabilizer_lag_px", 0.0)
        p_raw = getattr(snap, "raw_pressure", 0.0)
        p_dyn = getattr(snap, "dynamic_pressure", 0.0)
        dabs_sec = getattr(snap, "total_dabs_per_second", 0)
        dirty_area = getattr(snap, "last_dirty_area_px", 0.0)
        tiles_rec = getattr(snap, "last_tiles_recorded", 0)

        if p_raw > 0.0 or vel > 0.0:
            self._last_active_pen["raw_pressure"] = p_raw * 100.0
            self._last_active_pen["dynamic_pressure"] = p_dyn * 100.0
            self._last_active_pen["velocity"] = vel
            self._last_active_pen["stabilizer_lag"] = lag

        pks = self._peaks
        pks["motor_latency_us"] = max(pks.get("motor_latency_us", 0.0), lat_us)
        pks["raster_dab_us"] = max(pks.get("raster_dab_us", 0.0), dab_us)
        pks["undo_record_us"] = max(pks.get("undo_record_us", 0.0), und_us)
        pks["composite_us"] = max(pks.get("composite_us", 0.0), cmp_us)
        pks["kinematics_us"] = max(pks.get("kinematics_us", 0.0), kin_us)
        pks["interpolation_us"] = max(pks.get("interpolation_us", 0.0), int_us)
        pks["blit_ms"] = max(pks.get("blit_ms", 0.0), blit_ms)
        pks["stroke_velocity"] = max(pks.get("stroke_velocity", 0.0), vel)
        pks["stabilizer_lag_px"] = max(pks.get("stabilizer_lag_px", 0.0), lag)
        pks["dabs_per_second"] = max(pks.get("dabs_per_second", 0), dabs_sec)
        pks["dirty_area_px"] = max(pks.get("dirty_area_px", 0.0), dirty_area)
        pks["tiles_recorded"] = max(pks.get("tiles_recorded", 0), tiles_rec)
        if vp_fps > 0:
            pks["min_fps"] = min(pks.get("min_fps", 60.0), vp_fps)

        self.pipeline_bar.set_values_us(kin_us, int_us, dab_us, und_us, cmp_us, blit_us)

        # Atualiza Cards
        self.c_kin.set_value(f"{kin_us:.1f} µs", f"{kin_us/1000.0:.3f} ms")
        self.c_int.set_value(f"{int_us:.1f} µs", f"{int_us/1000.0:.3f} ms")
        self.c_dab.set_value(f"{dab_us:.1f} µs", f"{dab_us/1000.0:.2f} ms", color=tm.get_color("TELEMETRY_STAGE_RASTER", "#fb923c") if dab_us > 15000 else None)
        self.c_und.set_value(f"{und_us:.1f} µs", f"{und_us/1000.0:.2f} ms", color=tm.get_color("TELEMETRY_STAGE_UNDO", "#c084fc") if und_us > 10000 else None)
        self.c_cmp.set_value(f"{cmp_us:.1f} µs", f"{cmp_us/1000.0:.2f} ms")
        blit_col = tm.get_color("DANGER_HOVER", "#f87171") if blit_ms > 16.6 else (tm.get_color("WARNING", "#fbbf24") if blit_ms > 10.0 else None)
        self.c_blt.set_value(f"{blit_ms:.2f} ms", f"{blit_us:.0f} µs na viewport", color=blit_col)
        self.c_lat.set_value(f"{lat_us:.1f} µs", f"{lat_us/1000.0:.2f} ms")
        fps_col = tm.get_color("SUCCESS", "#34d399") if vp_fps >= 55 else (tm.get_color("WARNING", "#fbbf24") if vp_fps >= 30 else tm.get_color("DANGER_HOVER", "#f87171"))
        self.c_fps.set_value(f"{vp_fps:.1f} FPS", "Fluidez da tela", color=fps_col)

        self.c_hz.set_value(f"{snap.input_event_rate_hz} Hz", "Taxa do sensor")
        self.c_dabs_sec.set_value(f"{snap.total_dabs_per_second:,} dabs/s", f"{snap.total_dabs_in_stroke:,} acumulados")
        self.c_dabs.set_value(f"{getattr(snap, 'last_dabs_rendered', 0)} dabs", f"Total traço: {snap.total_dabs_in_stroke}")
        dw = int(getattr(snap, "last_dirty_width", 0.0))
        dh = int(getattr(snap, "last_dirty_height", 0.0))
        self.c_dirty.set_value(f"{dw} × {dh} px", "Largura × Altura")

        self.c_area.set_value(f"{int(getattr(snap, 'last_dirty_area_px', 0.0)):,} px²", "Superfície afetada")
        self.c_tiles.set_value(f"{tiles_rec} gravados", f"Total alocados: {snap.active_tile_count}")
        self.c_ram_canvas.set_value(f"{snap.tile_grid_memory_mb:.2f} MB", f"{snap.active_tile_count} tiles de 128x128")
        self.c_ram_undo.set_value(f"{snap.undo_stack_memory_mb:.2f} MB", f"{snap.undo_steps_count} passos de desfazer")

        p_phys = int(p_raw * 100)
        p_dyn_int = int(p_dyn * 100)
        vel_px = int(vel)
        if p_phys > 0 or vel_px > 0:
            self.c_press.set_value(f"{p_phys} %", f"Modulada: {p_dyn_int} %", bar_val=p_phys)
            self.c_vel.set_value(f"{vel_px} px/s", "Velocidade vetorial", bar_val=vel_px)
            self.c_lag.set_value(f"{lag:.1f} px", "Lag do estabilizador")
        elif self._last_active_pen["raw_pressure"] > 0:
            last_p = int(self._last_active_pen["raw_pressure"])
            last_dyn = int(self._last_active_pen["dynamic_pressure"])
            last_v = int(self._last_active_pen["velocity"])
            last_l = self._last_active_pen["stabilizer_lag"]
            self.c_press.set_value(f"{last_p} %", f"Modulada: {last_dyn} % (Último traço)", bar_val=last_p)
            self.c_vel.set_value(f"{last_v} px/s", "Velocidade (Último traço)", bar_val=last_v)
            self.c_lag.set_value(f"{last_l:.1f} px", "Lag (Último traço)")
        else:
            self.c_press.set_value("0 %", "Modulada: 0 %", bar_val=0)
            self.c_vel.set_value("0 px/s", "Velocidade vetorial", bar_val=0)
            self.c_lag.set_value("0.0 px", "Lag do estabilizador")

        engine_names = {0: "BrushEngine", 1: "PencilEngine", 2: "InkerEngine", 3: "EraserEngine"}
        self.c_hw.set_value("AVX2 / SSE2", engine_names.get(getattr(snap, "active_engine_id", 0), "Motor Nativo C++"))

        self._update_bottleneck_banner(dab_us, und_us, cmp_us, blit_ms)

    def _update_bottleneck_banner(self, dab_us: float, und_us: float, cmp_us: float, blit_ms: float) -> None:
        new_state, state_key, style, cause = TelemetryReportGenerator.diagnose_pipeline(dab_us, und_us, cmp_us, blit_ms)
        if state_key != getattr(self, "_current_state_key", None):
            self._record_state_transition(new_state, state_key, cause)

        self.lbl_bottleneck.setText(new_state)
        self.lbl_bottleneck.setStyleSheet(style)
        self.lbl_bottleneck.setToolTip(
            f"Estado Atual: {new_state}\nCausa: {cause}\n"
            f"Total de alterações registradas: {len(self._state_history)}\nClique para histórico."
        )

    def generate_full_report(self) -> str:
        """Gera o relatório completo de telemetria cobrindo os 20 medidores do Grid."""
        return TelemetryReportGenerator.generate(self)

    def _on_copy_report(self) -> None:
        QtWidgets.QApplication.clipboard().setText(self.generate_full_report())
        QtWidgets.QMessageBox.information(
            self,
            "Relatório Copiado",
            "Relatório completo de telemetria foi copiado para a Área de Transferência com sucesso!",
        )

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self._ensure_telemetry_enabled()
        self._timer.start()
        super().showEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._timer.stop()
        super().closeEvent(event)
