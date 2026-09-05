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
from ui.core.theme.manager import ThemeManager
from ui.core.engine.registry import EngineRegistry
from ui.core.widgets.pipeline_bar import PipelineBar


class GridMetricCard(QtWidgets.QFrame):
    """Card métrico compacto para exibição em grid com título, valor principal, subtítulo e barra opcional."""

    def __init__(
        self,
        title: str,
        initial_val: str = "0",
        subtitle: str = "",
        tag_color: str = "#38bdf8",
        show_bar: bool = False,
        bar_max: int = 100,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("GridMetricCard")
        self._tag_color = tag_color
        self._show_bar = show_bar
        self._bar_max = bar_max

        lo = QtWidgets.QVBoxLayout(self)
        lo.setContentsMargins(10, 8, 10, 8)
        lo.setSpacing(3)

        # Cabeçalho: Dot colorido + Título
        hdr_lo = QtWidgets.QHBoxLayout()
        hdr_lo.setSpacing(5)
        self.dot = QtWidgets.QLabel("■")
        self.dot.setStyleSheet(f"color: {tag_color}; font-size: 8px;")
        self.lbl_title = QtWidgets.QLabel(title.upper())
        self.lbl_title.setObjectName("CardTitle")
        hdr_lo.addWidget(self.dot)
        hdr_lo.addWidget(self.lbl_title, 1)
        lo.addLayout(hdr_lo)

        # Valor Principal
        self.lbl_val = QtWidgets.QLabel(initial_val)
        self.lbl_val.setObjectName("CardValue")
        lo.addWidget(self.lbl_val)

        # Subtítulo explicativo
        self.lbl_sub = QtWidgets.QLabel(subtitle)
        self.lbl_sub.setObjectName("CardSubtitle")
        lo.addWidget(self.lbl_sub)

        # Barra visual opcional (ex: pressão, velocidade)
        if show_bar:
            self.bar = QtWidgets.QProgressBar()
            self.bar.setRange(0, bar_max)
            self.bar.setValue(0)
            self.bar.setFixedHeight(6)
            self.bar.setTextVisible(False)
            lo.addWidget(self.bar)
        else:
            self.bar = None

        self._apply_theme()
        ThemeManager.instance().themeChanged.connect(self._apply_theme)

    @property
    def title(self) -> str:
        return self.lbl_title.text()

    @property
    def value(self) -> str:
        return self.lbl_val.text()

    @property
    def subtitle(self) -> str:
        return self.lbl_sub.text()

    def get_info(self) -> tuple[str, str, str]:
        """Retorna (título, valor_principal, subtítulo) do card."""
        return (self.lbl_title.text(), self.lbl_val.text(), self.lbl_sub.text())

    def set_value(self, val_str: str, sub_str: str | None = None, bar_val: int | None = None, color: str | None = None) -> None:
        self.lbl_val.setText(val_str)
        if sub_str is not None:
            self.lbl_sub.setText(sub_str)
        if self.bar and bar_val is not None:
            self.bar.setValue(min(self._bar_max, max(0, bar_val)))
        if color:
            self.lbl_val.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold; font-family: monospace;")
        else:
            self.lbl_val.setStyleSheet("")

    def _apply_theme(self, *args) -> None:
        tm = ThemeManager.instance()
        bg = tm.get_color("bg_panel", "#181a20")
        border = tm.get_color("border", "#2a2d36")
        muted = tm.get_color("text_sec", "#9ca3af")
        text = tm.get_color("text_main", "#f3f4f6")
        accent = self._tag_color

        self.setStyleSheet(f"""
            QFrame#GridMetricCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            QFrame#GridMetricCard:hover {{
                border-color: {accent};
            }}
            QLabel#CardTitle {{
                color: {muted};
                font-size: 9px;
                font-weight: bold;
                letter-spacing: 0.5px;
            }}
            QLabel#CardValue {{
                color: {text};
                font-size: 15px;
                font-weight: bold;
                font-family: monospace;
            }}
            QLabel#CardSubtitle {{
                color: {muted};
                font-size: 9px;
            }}
            QProgressBar {{
                background-color: rgba(0, 0, 0, 0.4);
                border: 1px solid {border};
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 2px;
            }}
        """)


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

        # ── Rastreamento de Estado do Pipeline & Transições ──────────────────
        self._current_state_key = "PIPELINE_EQUILIBRADO"
        self._current_state_str = "✅ PIPELINE EQUILIBRADO (< 2ms)"
        self._state_history: list[dict[str, str]] = []
        self._state_counts: dict[str, int] = {
            "PIPELINE_EQUILIBRADO": 1,
            "GARGALO_RASTER": 0,
            "GARGALO_BLIT": 0,
            "GARGALO_UNDO": 0,
            "GARGALO_COMPOSITOR": 0,
        }
        self._peaks: dict[str, float] = {
            "motor_latency_us": 0.0,
            "raster_dab_us": 0.0,
            "undo_record_us": 0.0,
            "composite_us": 0.0,
            "kinematics_us": 0.0,
            "interpolation_us": 0.0,
            "blit_ms": 0.0,
            "stroke_velocity": 0.0,
            "stabilizer_lag_px": 0.0,
            "dabs_per_second": 0.0,
            "dirty_area_px": 0.0,
            "tiles_recorded": 0,
            "min_fps": 60.0,
        }
        self._last_active_pen: dict[str, float] = {
            "raw_pressure": 0.0,
            "dynamic_pressure": 0.0,
            "velocity": 0.0,
            "stabilizer_lag": 0.0,
        }
        self._record_state_transition(
            new_state="✅ PIPELINE EQUILIBRADO (< 2ms)",
            state_key="PIPELINE_EQUILIBRADO",
            cause="Inicialização do Cockpit de Telemetria",
        )

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS para monitoramento fluido e instantâneo
        self._timer.timeout.connect(self._refresh_metrics)

        self._build_content()
        self._timer.start()

        # Garante que o motor nativo comece capturando
        self._ensure_telemetry_enabled()

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

        # ── Barra de Controles do Topo ────────────────────────────────────────
        ctrl_bar = QtWidgets.QHBoxLayout()
        ctrl_bar.setSpacing(8)

        self.lbl_status_pill = QtWidgets.QLabel("🟢 CAPTURA ATIVA (60 FPS)")
        self.lbl_status_pill.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.15);
            color: #34d399;
            font-size: 10px;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid rgba(16, 185, 129, 0.3);
        """)
        ctrl_bar.addWidget(self.lbl_status_pill)

        ctrl_bar.addStretch()

        self.btn_pin = QtWidgets.QPushButton("📌 Sempre no Topo: SIM")
        self.btn_pin.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_pin.setFixedHeight(26)
        self.btn_pin.setStyleSheet("font-size: 10px; font-weight: bold; padding: 2px 10px;")
        self.btn_pin.clicked.connect(self._on_toggle_pin)
        ctrl_bar.addWidget(self.btn_pin)

        self.btn_reset = QtWidgets.QPushButton("🔄 Resetar Métricas")
        self.btn_reset.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_reset.setFixedHeight(26)
        self.btn_reset.setStyleSheet("font-size: 10px; padding: 2px 10px;")
        self.btn_reset.clicked.connect(self._on_reset_metrics)
        ctrl_bar.addWidget(self.btn_reset)

        self.btn_copy = QtWidgets.QPushButton("📋 Copiar Relatório")
        self.btn_copy.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_copy.setFixedHeight(26)
        self.btn_copy.setStyleSheet("font-size: 10px; padding: 2px 10px;")
        self.btn_copy.clicked.connect(self._on_copy_report)
        ctrl_bar.addWidget(self.btn_copy)

        self.btn_clear_undo = QtWidgets.QPushButton("🧹 Limpar Undo")
        self.btn_clear_undo.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_clear_undo.setFixedHeight(26)
        self.btn_clear_undo.setStyleSheet("font-size: 10px; padding: 2px 10px;")
        self.btn_clear_undo.clicked.connect(self._on_clear_undo)
        ctrl_bar.addWidget(self.btn_clear_undo)

        lo.addLayout(ctrl_bar)

        # ── Banner de Diagnóstico de Gargalos ──────────────────────────────────
        self.lbl_bottleneck = QtWidgets.QLabel("✅ PIPELINE EQUILIBRADO (< 2ms)")
        self.lbl_bottleneck.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_bottleneck.setFixedHeight(24)
        self.lbl_bottleneck.setCursor(QtCore.Qt.PointingHandCursor)
        self.lbl_bottleneck.setToolTip("Clique para visualizar o Histórico de Alterações de Estado e Transições do Pipeline.")
        self.lbl_bottleneck.mousePressEvent = lambda e: self._show_state_history_dialog()
        self.lbl_bottleneck.setStyleSheet("""
            background-color: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid #10b981;
            border-radius: 4px;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 0.5px;
        """)
        lo.addWidget(self.lbl_bottleneck)

        # ── Barra Proporcional de Estágios ─────────────────────────────────────
        self.pipeline_bar = PipelineBar(self)
        self.pipeline_bar.setFixedHeight(14)
        lo.addWidget(self.pipeline_bar)

        self.lbl_legend = QtWidgets.QLabel(
            "<span style='color:#38bdf8'>■</span> Cinemática &nbsp;&nbsp;"
            "<span style='color:#facc15'>■</span> Interpolação &nbsp;&nbsp;"
            "<span style='color:#f97316'>■</span> RasterDab &nbsp;&nbsp;"
            "<span style='color:#a855f7'>■</span> Gravação Undo &nbsp;&nbsp;"
            "<span style='color:#22c55e'>■</span> Compositor &nbsp;&nbsp;"
            "<span style='color:#ec4899'>■</span> Apresentação Blit Qt"
        )
        self.lbl_legend.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_legend.setStyleSheet("font-size: 9px; font-weight: bold;")
        lo.addWidget(self.lbl_legend)

        # ── Grid Principal de Medidores (4 Colunas x 5 Linhas) ─────────────────
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)

        grid_container = QtWidgets.QWidget()
        grid_lo = QtWidgets.QGridLayout(grid_container)
        grid_lo.setContentsMargins(0, 4, 0, 4)
        grid_lo.setSpacing(8)

        # LINHA 1: Estágios Granulares C++
        self.c_kin = GridMetricCard("1. Cinemática / Dinâmica", "0.0 µs", "Filtro de caneta e velocidade", "#38bdf8")
        self.c_int = GridMetricCard("2. Interpolação Dabs", "0.0 µs", "Espaçamento e resíduo", "#facc15")
        self.c_dab = GridMetricCard("3. RasterDab (Shaders)", "0.0 µs", "SIMD AVX2 de ponta e papel", "#f97316")
        self.c_und = GridMetricCard("4. Gravação de Undo", "0.0 µs", "Cópia de blocos 128x128", "#a855f7")

        grid_lo.addWidget(self.c_kin, 0, 0)
        grid_lo.addWidget(self.c_int, 0, 1)
        grid_lo.addWidget(self.c_dab, 0, 2)
        grid_lo.addWidget(self.c_und, 0, 3)

        # LINHA 2: Composição, Blit e Frequências
        self.c_cmp = GridMetricCard("5. Compositor de Camadas", "0.0 µs", "Mesclagem SSE2 na região", "#22c55e")
        self.c_blt = GridMetricCard("6. Apresentação Blit Qt", "0.00 ms", "QPainter.drawImage na tela", "#ec4899")
        self.c_lat = GridMetricCard("7. Latência Total Motor", "0.00 µs", "Tempo de micro-evento C++", "#38bdf8")
        self.c_fps = GridMetricCard("8. Taxa Real da Viewport", "0.0 FPS", "Taxa efetiva de redesenho", "#10b981")

        grid_lo.addWidget(self.c_cmp, 1, 0)
        grid_lo.addWidget(self.c_blt, 1, 1)
        grid_lo.addWidget(self.c_lat, 1, 2)
        grid_lo.addWidget(self.c_fps, 1, 3)

        # LINHA 3: Frequências & Pegada Geométrica
        self.c_hz = GridMetricCard("9. Frequência da Mesa", "0 Hz", "Taxa de eventos do hardware", "#06b6d4")
        self.c_dabs_sec = GridMetricCard("10. Taxa de Carimbos", "0 dabs/s", "Rendimento do rasterizador", "#f59e0b")
        self.c_dabs = GridMetricCard("11. Dabs Emitidos", "0 dabs", "Último micro-evento", "#eab308")
        self.c_dirty = GridMetricCard("12. Região Suja Repintada", "0 × 0 px", "Bounding box atual", "#ec4899")

        grid_lo.addWidget(self.c_hz, 2, 0)
        grid_lo.addWidget(self.c_dabs_sec, 2, 1)
        grid_lo.addWidget(self.c_dabs, 2, 2)
        grid_lo.addWidget(self.c_dirty, 2, 3)

        # LINHA 4: Área, Blocos (Tiles) & Memória
        self.c_area = GridMetricCard("13. Área Suja do Evento", "0 px²", "Superfície de pixels repintada", "#8b5cf6")
        self.c_tiles = GridMetricCard("14. Blocos Gravados / Total", "0 / 0 tiles", "Blocos 128x128 em RAM", "#6366f1")
        self.c_ram_canvas = GridMetricCard("15. RAM do Canvas", "0.00 MB", "Memória dos tiles do documento", "#14b8a6")
        self.c_ram_undo = GridMetricCard("16. RAM do Histórico Undo", "0.00 MB", "0 passos de desfazer", "#ec4899")

        grid_lo.addWidget(self.c_area, 3, 0)
        grid_lo.addWidget(self.c_tiles, 3, 1)
        grid_lo.addWidget(self.c_ram_canvas, 3, 2)
        grid_lo.addWidget(self.c_ram_undo, 3, 3)

        # LINHA 5: Sensores da Caneta & Hardware
        self.c_press = GridMetricCard("17. Pressão Física vs Curva", "0 %", "Modulada: 0 %", "#3b82f6", show_bar=True, bar_max=100)
        self.c_vel = GridMetricCard("18. Velocidade do Traço", "0 px/s", "Velocidade vetorial", "#f97316", show_bar=True, bar_max=1500)
        self.c_lag = GridMetricCard("19. Lag do Estabilizador", "0.0 px", "Distância do filtro inercial", "#a855f7")
        self.c_hw = GridMetricCard("20. Aceleração & Mini-Motor", "AVX2 / SSE2", "Mini-motor C++ ativo", "#10b981")

        grid_lo.addWidget(self.c_press, 4, 0)
        grid_lo.addWidget(self.c_vel, 4, 1)
        grid_lo.addWidget(self.c_lag, 4, 2)
        grid_lo.addWidget(self.c_hw, 4, 3)

        self._cards = [
            self.c_kin, self.c_int, self.c_dab, self.c_und,
            self.c_cmp, self.c_blt, self.c_lat, self.c_fps,
            self.c_hz, self.c_dabs_sec, self.c_dabs, self.c_dirty,
            self.c_area, self.c_tiles, self.c_ram_canvas, self.c_ram_undo,
            self.c_press, self.c_vel, self.c_lag, self.c_hw,
        ]

        scroll.setWidget(grid_container)
        lo.addWidget(scroll, 1)

    def _on_toggle_pin(self) -> None:
        self._stay_on_top = not self._stay_on_top
        self.btn_pin.setText(f"📌 Sempre no Topo: {'SIM' if self._stay_on_top else 'NÃO'}")
        pos = self.pos()
        self._apply_stay_on_top(self._stay_on_top)
        self.move(pos)
        self.show()

    def _record_state_transition(self, new_state: str, state_key: str, cause: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        ms_part = int((time.time() % 1) * 1000)
        time_str = f"{timestamp}.{ms_part:03d}"

        transition = {
            "time": time_str,
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
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Histórico de Alterações de Estado do Pipeline")
        dlg.resize(680, 420)
        dlg_lo = QtWidgets.QVBoxLayout(dlg)
        dlg_lo.setContentsMargins(14, 14, 14, 14)
        dlg_lo.setSpacing(10)

        lbl_hdr = QtWidgets.QLabel("<b>Linha do Tempo de Alterações de Estado (Gargalos vs Equilíbrio)</b>")
        lbl_hdr.setStyleSheet("font-size: 13px; color: #38bdf8;")
        dlg_lo.addWidget(lbl_hdr)

        summary_text = (
            f"Equilibrado: {self._state_counts.get('PIPELINE_EQUILIBRADO', 0)}x | "
            f"Raster (>15ms): {self._state_counts.get('GARGALO_RASTER', 0)}x | "
            f"Blit (>16ms): {self._state_counts.get('GARGALO_BLIT', 0)}x | "
            f"Undo (>10ms): {self._state_counts.get('GARGALO_UNDO', 0)}x | "
            f"Compositor (>10ms): {self._state_counts.get('GARGALO_COMPOSITOR', 0)}x"
        )
        lbl_sum = QtWidgets.QLabel(summary_text)
        lbl_sum.setStyleSheet("font-size: 11px; color: #9ca3af;")
        dlg_lo.addWidget(lbl_sum)

        txt_history = QtWidgets.QPlainTextEdit()
        txt_history.setReadOnly(True)
        txt_history.setStyleSheet("font-family: monospace; font-size: 11px; background-color: #111827; color: #f3f4f6; border: 1px solid #374151;")

        hist_lines = []
        for t in reversed(self._state_history):
            hist_lines.append(f"[{t['time']}] {t['to_state']}\n  └─ Motivo: {t['cause']}\n")
        txt_history.setPlainText("\n".join(hist_lines) if hist_lines else "Nenhuma alteração registrada.")
        dlg_lo.addWidget(txt_history, 1)

        btn_row = QtWidgets.QHBoxLayout()
        btn_copy_hist = QtWidgets.QPushButton("📋 Copiar Histórico")
        btn_copy_hist.clicked.connect(lambda: QtWidgets.QApplication.clipboard().setText(txt_history.toPlainText()))
        btn_close = QtWidgets.QPushButton("Fechar")
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_copy_hist)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        dlg_lo.addLayout(btn_row)

        dlg.exec()

    def _on_reset_metrics(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "reset_telemetry"):
            backend.reset_telemetry()
        self._peaks = {
            "motor_latency_us": 0.0,
            "raster_dab_us": 0.0,
            "undo_record_us": 0.0,
            "composite_us": 0.0,
            "kinematics_us": 0.0,
            "interpolation_us": 0.0,
            "blit_ms": 0.0,
            "stroke_velocity": 0.0,
            "stabilizer_lag_px": 0.0,
            "dabs_per_second": 0.0,
            "dirty_area_px": 0.0,
            "tiles_recorded": 0,
            "min_fps": 60.0,
        }
        self._last_active_pen = {
            "raw_pressure": 0.0,
            "dynamic_pressure": 0.0,
            "velocity": 0.0,
            "stabilizer_lag": 0.0,
        }
        self._state_history.clear()
        self._state_counts = {
            "PIPELINE_EQUILIBRADO": 1,
            "GARGALO_RASTER": 0,
            "GARGALO_BLIT": 0,
            "GARGALO_UNDO": 0,
            "GARGALO_COMPOSITOR": 0,
        }
        self._record_state_transition(
            new_state="✅ PIPELINE EQUILIBRADO (< 2ms)",
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

        # 1. Viewport Qt
        vp = EngineRegistry.get_viewport_telemetry()
        blit_ms = vp.get("qt_draw_image_ms", 0.0)
        vp_fps = vp.get("qt_fps", 0.0)
        blit_us = blit_ms * 1000.0

        # 2. Engine C++ Snapshot
        if hasattr(backend, "get_telemetry_snapshot"):
            snap = backend.get_telemetry_snapshot()
            if snap:
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

                # Salva última atividade da caneta
                if p_raw > 0.0 or vel > 0.0:
                    self._last_active_pen["raw_pressure"] = p_raw * 100.0
                    self._last_active_pen["dynamic_pressure"] = p_dyn * 100.0
                    self._last_active_pen["velocity"] = vel
                    self._last_active_pen["stabilizer_lag"] = lag

                # Rastreia picos da sessão
                self._peaks["motor_latency_us"] = max(self._peaks.get("motor_latency_us", 0.0), lat_us)
                self._peaks["raster_dab_us"] = max(self._peaks.get("raster_dab_us", 0.0), dab_us)
                self._peaks["undo_record_us"] = max(self._peaks.get("undo_record_us", 0.0), und_us)
                self._peaks["composite_us"] = max(self._peaks.get("composite_us", 0.0), cmp_us)
                self._peaks["kinematics_us"] = max(self._peaks.get("kinematics_us", 0.0), kin_us)
                self._peaks["interpolation_us"] = max(self._peaks.get("interpolation_us", 0.0), int_us)
                self._peaks["blit_ms"] = max(self._peaks.get("blit_ms", 0.0), blit_ms)
                self._peaks["stroke_velocity"] = max(self._peaks.get("stroke_velocity", 0.0), vel)
                self._peaks["stabilizer_lag_px"] = max(self._peaks.get("stabilizer_lag_px", 0.0), lag)
                self._peaks["dabs_per_second"] = max(self._peaks.get("dabs_per_second", 0), dabs_sec)
                self._peaks["dirty_area_px"] = max(self._peaks.get("dirty_area_px", 0.0), dirty_area)
                self._peaks["tiles_recorded"] = max(self._peaks.get("tiles_recorded", 0), tiles_rec)
                if vp_fps > 0:
                    self._peaks["min_fps"] = min(self._peaks.get("min_fps", 60.0), vp_fps)

                # Atualiza barra proporcional
                self.pipeline_bar.set_values_us(kin_us, int_us, dab_us, und_us, cmp_us, blit_us)

                # LINHA 1: Estágios Granulares
                self.c_kin.set_value(f"{kin_us:.1f} µs", f"{kin_us/1000.0:.3f} ms")
                self.c_int.set_value(f"{int_us:.1f} µs", f"{int_us/1000.0:.3f} ms")
                self.c_dab.set_value(f"{dab_us:.1f} µs", f"{dab_us/1000.0:.2f} ms", color="#fb923c" if dab_us > 15000 else None)
                self.c_und.set_value(f"{und_us:.1f} µs", f"{und_us/1000.0:.2f} ms", color="#c084fc" if und_us > 10000 else None)

                # LINHA 2: Composição, Blit e Frequências
                self.c_cmp.set_value(f"{cmp_us:.1f} µs", f"{cmp_us/1000.0:.2f} ms")
                blit_col = "#f87171" if blit_ms > 16.6 else ("#fbbf24" if blit_ms > 10.0 else None)
                self.c_blt.set_value(f"{blit_ms:.2f} ms", f"{blit_us:.0f} µs na viewport", color=blit_col)
                self.c_lat.set_value(f"{lat_us:.1f} µs", f"{lat_us/1000.0:.2f} ms")
                fps_col = "#34d399" if vp_fps >= 55 else ("#fbbf24" if vp_fps >= 30 else "#f87171")
                self.c_fps.set_value(f"{vp_fps:.1f} FPS", "Fluidez da tela", color=fps_col)

                # LINHA 3: Frequências & Pegada Geométrica
                self.c_hz.set_value(f"{snap.input_event_rate_hz} Hz", "Taxa do sensor")
                self.c_dabs_sec.set_value(f"{snap.total_dabs_per_second:,} dabs/s", f"{snap.total_dabs_in_stroke:,} acumulados")
                dabs_rendered = getattr(snap, "last_dabs_rendered", 0)
                self.c_dabs.set_value(f"{dabs_rendered} dabs", f"Total traço: {snap.total_dabs_in_stroke}")
                dw = int(getattr(snap, "last_dirty_width", 0.0))
                dh = int(getattr(snap, "last_dirty_height", 0.0))
                self.c_dirty.set_value(f"{dw} × {dh} px", f"Largura × Altura")

                # LINHA 4: Área, Blocos & Memória
                area_px = getattr(snap, "last_dirty_area_px", 0.0)
                self.c_area.set_value(f"{int(area_px):,} px²", "Superfície afetada")
                tiles_rec = getattr(snap, "last_tiles_recorded", 0)
                self.c_tiles.set_value(f"{tiles_rec} gravados", f"Total alocados: {snap.active_tile_count}")
                self.c_ram_canvas.set_value(f"{snap.tile_grid_memory_mb:.2f} MB", f"{snap.active_tile_count} tiles de 128x128")
                self.c_ram_undo.set_value(f"{snap.undo_stack_memory_mb:.2f} MB", f"{snap.undo_steps_count} passos de desfazer")

                # LINHA 5: Sensores & Hardware (com retenção da última atividade ao soltar a caneta)
                p_phys = int(p_raw * 100)
                p_dyn_int = int(p_dyn * 100)
                vel_px = int(vel)
                lag_px = lag

                if p_phys > 0 or vel_px > 0:
                    self.c_press.set_value(f"{p_phys} %", f"Modulada: {p_dyn_int} %", bar_val=p_phys)
                    self.c_vel.set_value(f"{vel_px} px/s", "Velocidade vetorial", bar_val=vel_px)
                    self.c_lag.set_value(f"{lag_px:.1f} px", "Lag do estabilizador")
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
                eng_str = engine_names.get(getattr(snap, "active_engine_id", 0), "Motor Nativo C++")
                self.c_hw.set_value("AVX2 / SSE2", eng_str)

                # Diagnóstico do Banner & Alterações de Estado
                self._update_bottleneck_banner(dab_us, und_us, cmp_us, blit_ms)

    def _update_bottleneck_banner(self, dab_us: float, und_us: float, cmp_us: float, blit_ms: float) -> None:
        if blit_ms > 16.6:
            new_state = "⚠️ GARGALO EM TELA: APRESENTAÇÃO QT BLIT LENTO (> 16ms / < 60 FPS)"
            state_key = "GARGALO_BLIT"
            style = "background-color: rgba(239,68,68,0.2); color: #f87171; border: 1px solid #ef4444; border-radius: 4px; font-size: 10px; font-weight: bold;"
            cause = f"Apresentação Viewport Qt ({blit_ms:.2f} ms > 16.6 ms / fluidez abaixo de 60 FPS)"
        elif dab_us > 15000.0:
            new_state = "⚠️ GARGALO EM RASTER: PINCEL GRANDE (> 15ms / CPU SATURADA)"
            state_key = "GARGALO_RASTER"
            style = "background-color: rgba(249,115,22,0.2); color: #fb923c; border: 1px solid #f97316; border-radius: 4px; font-size: 10px; font-weight: bold;"
            cause = f"Rasterização de Dabs ({dab_us:.1f} µs | {dab_us/1000.0:.2f} ms > 15 ms / pincel largo)"
        elif und_us > 10000.0:
            new_state = "⚠️ GARGALO EM UNDO: MUITOS TILES GRAVADOS (> 10ms CÓPIA RAM)"
            state_key = "GARGALO_UNDO"
            style = "background-color: rgba(168,85,247,0.2); color: #c084fc; border: 1px solid #a855f7; border-radius: 4px; font-size: 10px; font-weight: bold;"
            cause = f"Cópia de Tiles para Histórico Undo ({und_us:.1f} µs | {und_us/1000.0:.2f} ms > 10 ms)"
        elif cmp_us > 10000.0:
            new_state = "⚠️ GARGALO EM COMPOSIÇÃO DE CAMADAS (> 10ms)"
            state_key = "GARGALO_COMPOSITOR"
            style = "background-color: rgba(34,197,94,0.2); color: #4ade80; border: 1px solid #22c55e; border-radius: 4px; font-size: 10px; font-weight: bold;"
            cause = f"Mesclagem de Camadas no Compositor ({cmp_us:.1f} µs | {cmp_us/1000.0:.2f} ms > 10 ms)"
        else:
            new_state = "✅ PIPELINE EQUILIBRADO (< 2ms)"
            state_key = "PIPELINE_EQUILIBRADO"
            style = "background-color: rgba(16,185,129,0.15); color: #34d399; border: 1px solid #10b981; border-radius: 4px; font-size: 10px; font-weight: bold;"
            cause = "Todos os estágios operando com alta fluidez (< 2ms / 60 FPS)"

        if state_key != getattr(self, "_current_state_key", None):
            self._record_state_transition(new_state, state_key, cause)

        self.lbl_bottleneck.setText(new_state)
        self.lbl_bottleneck.setStyleSheet(style)
        self.lbl_bottleneck.setToolTip(
            f"Estado Atual: {new_state}\n"
            f"Causa: {cause}\n"
            f"Total de alterações de estado registradas: {len(self._state_history)}\n"
            f"Clique para abrir o histórico detalhado."
        )

    def generate_full_report(self) -> str:
        """Gera o relatório completo de telemetria contendo todos os 20 medidores do Grid,

        o diagnóstico do pipeline, picos de estresse e o histórico de alterações de estado.
        """
        backend = EngineRegistry.instance().get_backend()
        snap = backend.get_telemetry_snapshot() if (backend and hasattr(backend, "get_telemetry_snapshot")) else None
        vp = EngineRegistry.get_viewport_telemetry()
        blit_ms = vp.get("qt_draw_image_ms", 0.0)
        vp_fps = vp.get("qt_fps", 0.0)
        blit_us = blit_ms * 1000.0

        kin_us = getattr(snap, "time_kinematics_us", 0.0)
        int_us = getattr(snap, "time_interpolation_us", 0.0)
        dab_us = getattr(snap, "time_raster_dab_us", 0.0)
        und_us = getattr(snap, "time_undo_record_us", 0.0)
        cmp_us = getattr(snap, "time_composite_us", 0.0)
        total_cycle_us = kin_us + int_us + dab_us + und_us + cmp_us + blit_us
        denom = total_cycle_us if total_cycle_us > 0 else 1.0

        pct_kin = (kin_us / denom) * 100.0
        pct_int = (int_us / denom) * 100.0
        pct_dab = (dab_us / denom) * 100.0
        pct_und = (und_us / denom) * 100.0
        pct_cmp = (cmp_us / denom) * 100.0
        pct_blt = (blit_us / denom) * 100.0

        engine_names = {0: "BrushEngine", 1: "PencilEngine", 2: "InkerEngine", 3: "EraserEngine"}
        eng_str = engine_names.get(getattr(snap, "active_engine_id", 0), "Motor Nativo C++")

        lines = [
            "=" * 78,
            " 🏛️ LUMENIA ART STUDIO — COCKPIT DE TELEMETRIA & DIAGNÓSTICO EM GRID",
            "=" * 78,
            f"Data / Hora da Captura  : {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Monitoramento em Tempo  : Captura Ativa (~60 FPS / Timer 16ms)",
            f"Fixação Sempre no Topo  : {'SIM' if self._stay_on_top else 'NÃO'}",
            "",
            "-" * 78,
            " 🚦 DIAGNÓSTICO DO PIPELINE & ALTERAÇÕES DE ESTADO",
            "-" * 78,
            f"Estado Atual do Banner  : {self.lbl_bottleneck.text()}",
            f"Classificação de Estado : {self._current_state_key}",
            f"Condição Atual          : {'Equilibrado (Zero Sobrecarga)' if self._current_state_key == 'PIPELINE_EQUILIBRADO' else 'Presença de Gargalo Operacional'}",
            "",
            "Resumo de Ocorrências na Sessão de Teste:",
            f"  • ✅ PIPELINE EQUILIBRADO (< 2ms) : {self._state_counts.get('PIPELINE_EQUILIBRADO', 0)} vez(es)",
            f"  • ⚠️ GARGALO EM RASTER (> 15ms)   : {self._state_counts.get('GARGALO_RASTER', 0)} vez(es)",
            f"  • ⚠️ GARGALO EM TELA / BLIT (> 16ms): {self._state_counts.get('GARGALO_BLIT', 0)} vez(es)",
            f"  • ⚠️ GARGALO EM UNDO (> 10ms)     : {self._state_counts.get('GARGALO_UNDO', 0)} vez(es)",
            f"  • ⚠️ GARGALO EM COMPOSITOR (> 10ms): {self._state_counts.get('GARGALO_COMPOSITOR', 0)} vez(es)",
            f"  • Total de Transições Registradas : {len(self._state_history)}",
            "",
            "Picos Máximos de Estresse Registrados na Sessão:",
            f"  • Pico Latência do Motor C++ : {self._peaks['motor_latency_us']:.1f} µs ({self._peaks['motor_latency_us']/1000.0:.2f} ms)",
            f"  • Pico em RasterDab (Shaders): {self._peaks['raster_dab_us']:.1f} µs ({self._peaks['raster_dab_us']/1000.0:.2f} ms)",
            f"  • Pico Gravação de Undo      : {self._peaks['undo_record_us']:.1f} µs ({self._peaks['undo_record_us']/1000.0:.2f} ms)",
            f"  • Pico Compositor de Camadas : {self._peaks['composite_us']:.1f} µs ({self._peaks['composite_us']/1000.0:.2f} ms)",
            f"  • Pico Apresentação Blit Qt  : {self._peaks['blit_ms']:.2f} ms ({self._peaks['blit_ms']*1000.0:.0f} µs)",
            f"  • Menor Fluidez da Viewport  : {self._peaks['min_fps']:.1f} FPS",
            f"  • Pico Velocidade do Traço   : {int(self._peaks['stroke_velocity'])} px/s",
            f"  • Pico Lag do Estabilizador  : {self._peaks['stabilizer_lag_px']:.1f} px",
            f"  • Pico Taxa de Carimbos      : {int(self._peaks['dabs_per_second']):,} dabs/s",
            f"  • Pico Área Suja Repintada   : {int(self._peaks['dirty_area_px']):,} px² ({int(self._peaks['tiles_recorded'])} tiles gravados)",
            "",
            "Histórico Cronológico das Últimas Alterações de Estado (Transições):",
        ]

        if self._state_history:
            for trans in self._state_history[-15:]:
                lines.append(f"  [{trans['time']}] {trans['to_state']}\n    └─ Motivo: {trans['cause']}")
        else:
            lines.append("  (Nenhuma transição de estado registrada)")

        lines.extend([
            "",
            "-" * 78,
            " ⏱️ DECOMPOSIÇÃO PROPORCIONAL DO PIPELINE (BARRA DE ESTÁGIOS)",
            "-" * 78,
            f"  ■ 1. Cinemática / Dinâmica : {kin_us:>9.1f} µs ({kin_us/1000.0:>6.3f} ms) [{pct_kin:>5.1f}%]",
            f"  ■ 2. Interpolação Dabs     : {int_us:>9.1f} µs ({int_us/1000.0:>6.3f} ms) [{pct_int:>5.1f}%]",
            f"  ■ 3. RasterDab (Shaders)   : {dab_us:>9.1f} µs ({dab_us/1000.0:>6.2f} ms) [{pct_dab:>5.1f}%] {'⚠️ GARGALO CRÍTICO' if dab_us > 15000 else ''}",
            f"  ■ 4. Gravação de Undo      : {und_us:>9.1f} µs ({und_us/1000.0:>6.2f} ms) [{pct_und:>5.1f}%] {'⚠️ GARGALO' if und_us > 10000 else ''}",
            f"  ■ 5. Compositor de Camadas : {cmp_us:>9.1f} µs ({cmp_us/1000.0:>6.2f} ms) [{pct_cmp:>5.1f}%] {'⚠️ GARGALO' if cmp_us > 10000 else ''}",
            f"  ■ 6. Apresentação Blit Qt  : {blit_us:>9.1f} µs ({blit_ms:>6.2f} ms) [{pct_blt:>5.1f}%] {'⚠️ GARGALO' if blit_ms > 16.6 else ''}",
            "  " + "-" * 66,
            f"  Ciclo Total do Micro-Evento: {total_cycle_us:.1f} µs ({total_cycle_us/1000.0:.2f} ms)",
            "",
            "-" * 78,
            " 🪟 PAINEL COMPLETO EM GRID (TODOS OS 20 MEDIDORES EM TEMPO REAL)",
            "-" * 78,
        ])

        cards_sections = [
            ("LINHA 1: Estágios Granulares C++", [self.c_kin, self.c_int, self.c_dab, self.c_und]),
            ("LINHA 2: Composição, Blit e Frequências", [self.c_cmp, self.c_blt, self.c_lat, self.c_fps]),
            ("LINHA 3: Frequências & Pegada Geométrica", [self.c_hz, self.c_dabs_sec, self.c_dabs, self.c_dirty]),
            ("LINHA 4: Área, Blocos (Tiles) & Memória", [self.c_area, self.c_tiles, self.c_ram_canvas, self.c_ram_undo]),
            ("LINHA 5: Sensores da Caneta & Hardware", [self.c_press, self.c_vel, self.c_lag, self.c_hw]),
        ]

        for sec_name, cards in cards_sections:
            lines.append(f"[{sec_name}]")
            for card in cards:
                t, v, s = card.get_info()
                lines.append(f"  • {t:<28} : {v:<22} | {s}")
            lines.append("")

        lines.extend([
            "-" * 78,
            " ⚙️ AMBIENTE, ARQUITETURA & ACELERAÇÃO",
            "-" * 78,
            "  • Instruções SIMD       : AVX2 / SSE2 Ativo (Vetorizado)",
            f"  • Mini-Motor em Execução : {eng_str}",
            "  • Formato de Bloco      : Tiles 128x128 em BGRA32 / Float32",
            "  • Polling de Viewport   : 60 FPS Desacoplado via QTimer",
            "=" * 78,
        ])

        return "\n".join(lines)

    def _on_copy_report(self) -> None:
        report_text = self.generate_full_report()
        QtWidgets.QApplication.clipboard().setText(report_text)
        QtWidgets.QMessageBox.information(
            self,
            "Relatório de Telemetria Copiado",
            "Relatório completo de telemetria (incluindo todos os 20 medidores do Grid, "
            "diagnóstico do pipeline, picos de estresse e histórico de alterações de estado) "
            "foi copiado para a Área de Transferência com sucesso!"
        )

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self._ensure_telemetry_enabled()
        self._timer.start()
        super().showEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._timer.stop()
        super().closeEvent(event)
