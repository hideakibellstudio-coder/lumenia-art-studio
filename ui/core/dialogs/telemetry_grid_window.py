"""
TelemetryGridWindow — Cockpit de Telemetria e Diagnóstico em Grid do ALADYN ENGINE
==================================================================================
Janela flutuante não-modal (modeless) para auditoria e diagnóstico em tempo real:
- Permite desenhar livremente no canvas enquanto os medidores atualizam a 60 FPS
- Suporte a fixação no topo (Stay on Top) para monitoramento simultâneo
- Grid de 20 medidores (`telemetry_meters.METERS`) cobrindo o pipeline nativo C++
- Banner de gargalos e barra empilhada proporcional

É uma view do `TelemetryTracker` (estado, picos, histórico e relatório). Até
2026-09-24 a janela tinha a própria cópia de tudo isso e um segundo gerador de
relatório que lia os atributos privados dela.
"""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.dialogs.base_dialog import BaseFramelessDialog
from ui.core.dialogs.telemetry_common import banner_style, clear_undo_history, copy_report, enable_capture
from ui.core.dialogs.telemetry_state_history_dialog import TelemetryStateHistoryDialog
from ui.core.engine.registry import EngineRegistry
from ui.core.engine.telemetry_dto import TelemetrySnapshot
from ui.core.engine.telemetry_meters import METERS, read_meters
from ui.core.engine.telemetry_tracker import TelemetryTracker
from ui.core.icons import get_icon
from ui.core.theme.manager import ThemeManager
from ui.core.widgets.metric_card import GridMetricCard
from ui.core.widgets.pipeline_bar import PipelineBar

__all__ = ["GridMetricCard", "TelemetryGridWindow"]

# Medidor -> token do tema da marca colorida do card (todos os temas têm os tokens).
_CARD_COLORS = {
    "kin": "TELEMETRY_STAGE_KINEMATICS",
    "int": "TELEMETRY_STAGE_INTERPOLATION",
    "dab": "TELEMETRY_STAGE_RASTER",
    "und": "TELEMETRY_STAGE_UNDO",
    "cmp": "TELEMETRY_STAGE_COMPOSITOR",
    "blt": "TELEMETRY_STAGE_BLIT",
    "lat": "TELEMETRY_STAGE_KINEMATICS",
    "fps": "SUCCESS",
    "hz": "ACCENT",
    "dabs_sec": "WARNING",
    "dabs": "TELEMETRY_STAGE_INTERPOLATION",
    "dirty": "TELEMETRY_STAGE_BLIT",
    "area": "TELEMETRY_STAGE_UNDO",
    "tiles": "ACCENT",
    "ram_canvas": "TELEMETRY_STAGE_COMPOSITOR",
    "ram_undo": "TELEMETRY_STAGE_BLIT",
    "press": "ACCENT",
    "vel": "TELEMETRY_STAGE_RASTER",
    "lag": "TELEMETRY_STAGE_UNDO",
    "hw": "SUCCESS",
}
_BARS = {"press": 100, "vel": 1500}
# Nível da leitura -> token do tema do valor.
_LEVEL_COLORS = {
    "good": "SUCCESS",
    "warning": "WARNING",
    "critical": "DANGER_HOVER",
}


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

        self._tracker = TelemetryTracker.instance()
        self._stay_on_top = True
        self._apply_stay_on_top(True)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)  # ~60 FPS para monitoramento fluido
        self._timer.timeout.connect(self.refresh)

        self._build_content()
        self._show_state()
        self._timer.start()
        enable_capture()

    @property
    def stay_on_top(self) -> bool:
        return self._stay_on_top

    def _apply_stay_on_top(self, stay: bool) -> None:
        flags = self.windowFlags()
        if stay:
            flags |= QtCore.Qt.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    # ── Construção ────────────────────────────────────────────────────────

    def _button(self, icon_name: str, text: str, slot, bold: bool = False) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(text)
        button.setIcon(get_icon(icon_name, ThemeManager.instance().get_color("text_main")))
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.setFixedHeight(26)
        button.setStyleSheet(f"font-size: 10px; {'font-weight: bold; ' if bold else ''}padding: 2px 10px;")
        button.clicked.connect(slot)
        return button

    def _build_content(self) -> None:
        lo = self.content_layout
        lo.setContentsMargins(14, 8, 14, 12)
        lo.setSpacing(8)
        tm = ThemeManager.instance()
        success = QtGui.QColor(tm.get_color("SUCCESS", "#34d399"))
        success_rgb = f"{success.red()}, {success.green()}, {success.blue()}"

        # Barra de Controles do Topo
        ctrl_bar = QtWidgets.QHBoxLayout()
        ctrl_bar.setSpacing(8)
        self.lbl_status_pill = QtWidgets.QLabel(
            f"<span style='color:{success.name()}'>●</span> CAPTURA ATIVA (60 FPS)")
        self.lbl_status_pill.setStyleSheet(f"""
            background-color: rgba({success_rgb}, 0.15); color: {success.name()};
            font-size: 10px; font-weight: bold; padding: 4px 8px;
            border-radius: 4px; border: 1px solid rgba({success_rgb}, 0.3);
        """)
        ctrl_bar.addWidget(self.lbl_status_pill)
        ctrl_bar.addStretch()
        self.btn_pin = self._button("pin", "Sempre no Topo: SIM", self.toggle_pin, bold=True)
        self.btn_reset = self._button("reset", "Resetar Métricas", self.reset_metrics)
        self.btn_copy = self._button("copy", "Copiar Relatório", lambda: copy_report(self, self._stay_on_top))
        self.btn_clear_undo = self._button("trash", "Limpar Undo", lambda: clear_undo_history(self))
        for button in (self.btn_pin, self.btn_reset, self.btn_copy, self.btn_clear_undo):
            ctrl_bar.addWidget(button)
        lo.addLayout(ctrl_bar)

        # Banner de Diagnóstico (clique: histórico de transições)
        self.lbl_bottleneck = QtWidgets.QLabel()
        self.lbl_bottleneck.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_bottleneck.setFixedHeight(24)
        self.lbl_bottleneck.setCursor(QtCore.Qt.PointingHandCursor)
        self.lbl_bottleneck.mousePressEvent = lambda e: self.show_state_history()
        lo.addWidget(self.lbl_bottleneck)

        # Barra Proporcional de Estágios
        self.pipeline_bar = PipelineBar(self)
        self.pipeline_bar.setFixedHeight(14)
        lo.addWidget(self.pipeline_bar)

        stages = [("kin", "Cinemática"), ("int", "Interpolação"), ("dab", "RasterDab"),
                  ("und", "Gravação Undo"), ("cmp", "Compositor"), ("blt", "Apresentação Blit Qt")]
        self.lbl_legend = QtWidgets.QLabel(" &nbsp;&nbsp;".join(
            f"<span style='color:{tm.get_color(_CARD_COLORS[key])}'>■</span> {name}" for key, name in stages))
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
        self.cards: dict[str, GridMetricCard] = {}
        for index, (key, title, detail) in enumerate(METERS):
            card = GridMetricCard(title, "0", detail, tm.get_color(_CARD_COLORS[key]),
                                  show_bar=key in _BARS, bar_max=_BARS.get(key, 100))
            self.cards[key] = card
            grid_lo.addWidget(card, index // 4, index % 4)
        scroll.setWidget(grid_container)
        lo.addWidget(scroll, 1)

    # ── Ações ─────────────────────────────────────────────────────────────

    def toggle_pin(self) -> None:
        self._stay_on_top = not self._stay_on_top
        self.btn_pin.setText(f"Sempre no Topo: {'SIM' if self._stay_on_top else 'NÃO'}")
        self.btn_pin.setIcon(get_icon("pin" if self._stay_on_top else "pin_off",
                                      ThemeManager.instance().get_color("text_main")))
        pos = self.pos()
        self._apply_stay_on_top(self._stay_on_top)
        self.move(pos)
        self.show()

    def show_state_history(self) -> None:
        TelemetryStateHistoryDialog(self._tracker.state_counts, self._tracker.state_history, parent=self).exec()

    def reset_metrics(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend is not None:
            backend.reset_telemetry()
        self._tracker.reset()
        self.refresh()

    def generate_full_report(self) -> str:
        """O relatório único do tracker, com a fixação no topo desta janela."""
        return self._tracker.generate_full_report(self._stay_on_top)

    # ── Motor → tela ──────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Lê o motor e a viewport, atualiza o tracker e mostra."""
        backend = EngineRegistry.instance().get_backend()
        if backend is None:
            return
        snap = backend.get_telemetry_snapshot()
        vp = EngineRegistry.get_viewport_telemetry()
        self._tracker.update(snap, vp)
        self.show_readings(snap, vp)

    def show_readings(self, snap: TelemetrySnapshot, vp: dict) -> None:
        tm = ThemeManager.instance()
        blit_us = vp.get("qt_draw_image_ms", 0.0) * 1000.0
        self.pipeline_bar.set_values_us(
            snap.time_kinematics_us, snap.time_interpolation_us, snap.time_raster_dab_us,
            snap.time_undo_record_us, snap.time_composite_us, blit_us)
        for reading in read_meters(snap, vp, self._tracker.last_active_pen):
            level = _LEVEL_COLORS.get(reading.level)
            self.cards[reading.key].set_value(
                reading.value, reading.detail, bar_val=reading.bar,
                color=tm.get_color(level) if level else None)
        self._show_state()

    def _show_state(self) -> None:
        tracker = self._tracker
        self.lbl_bottleneck.setText(tracker.current_state_str)
        self.lbl_bottleneck.setStyleSheet(banner_style(tracker.current_state_key))
        self.lbl_bottleneck.setToolTip(
            f"Estado Atual: {tracker.current_state_str}\nCausa: {tracker.state_cause}\n"
            f"Total de alterações registradas: {tracker.transition_count}\nClique para histórico."
        )

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        enable_capture()
        self._timer.start()
        super().showEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._timer.stop()
        super().closeEvent(event)
