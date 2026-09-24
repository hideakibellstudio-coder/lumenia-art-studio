"""
TelemetryTracker — estado único da sessão de telemetria.
========================================================
Fonte única (singleton) para as três telas de telemetria (cockpit em grade,
painel de telemetria e diálogo de diagnóstico):
- diagnóstico do pipeline (equilibrado ou gargalo em raster, tela, undo ou compositor);
- linha do tempo das transições de estado, com carimbo em ms e motivo;
- contagem de ocorrências e picos de estresse da sessão;
- última atividade da caneta (pressão, velocidade, lag) para mostrar depois de soltar.

O texto do relatório está em `telemetry_report.py`. Até 2026-09-24 o cockpit
em grade tinha uma segunda cópia inteira deste estado (e do relatório).
"""

from __future__ import annotations

import time
from typing import Optional

from .telemetry_dto import TelemetrySnapshot

# Chave canônica do estado -> texto do banner.
STATE_TEXTS = {
    "PIPELINE_EQUILIBRADO": "PIPELINE EQUILIBRADO (< 2ms)",
    "GARGALO_BLIT": "GARGALO EM TELA: APRESENTAÇÃO QT BLIT LENTO (> 16ms / < 60 FPS)",
    "GARGALO_RASTER": "GARGALO EM RASTER: PINCEL GRANDE (> 15ms / CPU SATURADA)",
    "GARGALO_UNDO": "GARGALO EM UNDO: MUITOS TILES GRAVADOS (> 10ms CÓPIA RAM)",
    "GARGALO_COMPOSITOR": "GARGALO EM COMPOSIÇÃO DE CAMADAS (> 10ms)",
}
_HISTORY_LIMIT = 200


def diagnose(dab_us: float, und_us: float, cmp_us: float, blit_ms: float) -> tuple[str, str, str]:
    """(texto do banner, chave do estado, motivo) para os tempos de um micro-evento."""
    if blit_ms > 16.6:
        return (STATE_TEXTS["GARGALO_BLIT"], "GARGALO_BLIT",
                f"Apresentação Viewport Qt ({blit_ms:.2f} ms > 16.6 ms / fluidez abaixo de 60 FPS)")
    if dab_us > 15000.0:
        return (STATE_TEXTS["GARGALO_RASTER"], "GARGALO_RASTER",
                f"Rasterização de Dabs ({dab_us:.1f} µs | {dab_us/1000.0:.2f} ms > 15 ms / pincel largo)")
    if und_us > 10000.0:
        return (STATE_TEXTS["GARGALO_UNDO"], "GARGALO_UNDO",
                f"Cópia de Tiles para Histórico Undo ({und_us:.1f} µs | {und_us/1000.0:.2f} ms > 10 ms)")
    if cmp_us > 10000.0:
        return (STATE_TEXTS["GARGALO_COMPOSITOR"], "GARGALO_COMPOSITOR",
                f"Mesclagem de Camadas no Compositor ({cmp_us:.1f} µs | {cmp_us/1000.0:.2f} ms > 10 ms)")
    return (STATE_TEXTS["PIPELINE_EQUILIBRADO"], "PIPELINE_EQUILIBRADO",
            "Todos os estágios operando com alta fluidez (< 2ms / 60 FPS)")


def _empty_peaks() -> dict[str, float]:
    return {
        "motor_latency_us": 0.0, "raster_dab_us": 0.0, "undo_record_us": 0.0, "composite_us": 0.0,
        "kinematics_us": 0.0, "interpolation_us": 0.0, "blit_ms": 0.0, "stroke_velocity": 0.0,
        "stabilizer_lag_px": 0.0, "dabs_per_second": 0.0, "dirty_area_px": 0.0, "tiles_recorded": 0,
        "min_fps": 60.0,
    }


def _empty_pen() -> dict[str, float]:
    return {"raw_pressure": 0.0, "dynamic_pressure": 0.0, "velocity": 0.0, "stabilizer_lag": 0.0}


class TelemetryTracker:
    """Singleton de rastreamento e auditoria de telemetria em tempo real."""

    _instance: Optional[TelemetryTracker] = None

    @classmethod
    def instance(cls) -> TelemetryTracker:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._last_snap = TelemetrySnapshot()
        self._last_vp: dict = {}
        self._start("Inicialização do Sistema de Telemetria")

    def _start(self, cause: str) -> None:
        self._current_state_key = "PIPELINE_EQUILIBRADO"
        self._current_state_str = STATE_TEXTS["PIPELINE_EQUILIBRADO"]
        self._state_history: list[dict[str, str]] = []
        self._state_counts = {key: 0 for key in STATE_TEXTS}
        self._peaks = _empty_peaks()
        self._last_active_pen = _empty_pen()
        self.record_state_transition(STATE_TEXTS["PIPELINE_EQUILIBRADO"], "PIPELINE_EQUILIBRADO", cause)

    # ── Leitura (cópias: quem lê não altera o estado) ─────────────────────

    @property
    def current_state_key(self) -> str:
        return self._current_state_key

    @property
    def current_state_str(self) -> str:
        return self._current_state_str

    @property
    def state_history(self) -> list[dict[str, str]]:
        return list(self._state_history)

    @property
    def state_cause(self) -> str:
        """Motivo da última transição de estado."""
        return self._state_history[-1]["cause"] if self._state_history else ""

    @property
    def transition_count(self) -> int:
        return len(self._state_history)

    @property
    def state_counts(self) -> dict[str, int]:
        return dict(self._state_counts)

    @property
    def peaks(self) -> dict[str, float]:
        return dict(self._peaks)

    @property
    def last_active_pen(self) -> dict[str, float]:
        return dict(self._last_active_pen)

    # ── Escrita ───────────────────────────────────────────────────────────

    def reset(self) -> None:
        """Limpa contadores, picos e reinicia o histórico de transições."""
        self._start("Métricas e contadores resetados pelo usuário")

    def record_state_transition(self, new_state: str, state_key: str, cause: str) -> None:
        """Registra uma transição de estado com carimbo em milissegundos."""
        stamp = f"{time.strftime('%H:%M:%S')}.{int((time.time() % 1) * 1000):03d}"
        self._state_history.append({
            "time": stamp,
            "from_state": self._current_state_str,
            "to_state": new_state,
            "state_key": state_key,
            "cause": cause,
        })
        if len(self._state_history) > _HISTORY_LIMIT:
            self._state_history.pop(0)
        self._state_counts[state_key] = self._state_counts.get(state_key, 0) + 1
        self._current_state_key = state_key
        self._current_state_str = new_state

    def update(self, snap: Optional[TelemetrySnapshot], vp: Optional[dict]) -> tuple[str, str, str]:
        """Atualiza picos, caneta e estado a partir do motor e da viewport.

        Retorna (texto do banner, chave do estado, motivo).
        """
        snap = snap if snap is not None else TelemetrySnapshot()
        vp = vp or {}
        self._last_snap, self._last_vp = snap, vp
        blit_ms = vp.get("qt_draw_image_ms", 0.0)
        vp_fps = vp.get("qt_fps", 0.0)

        if snap.raw_pressure > 0.0 or snap.stroke_velocity > 0.0:
            self._last_active_pen = {
                "raw_pressure": snap.raw_pressure * 100.0,
                "dynamic_pressure": snap.dynamic_pressure * 100.0,
                "velocity": snap.stroke_velocity,
                "stabilizer_lag": snap.stabilizer_lag_px,
            }

        peaks = self._peaks
        for key, value in (
            ("motor_latency_us", snap.last_segment_latency_us),
            ("raster_dab_us", snap.time_raster_dab_us),
            ("undo_record_us", snap.time_undo_record_us),
            ("composite_us", snap.time_composite_us),
            ("kinematics_us", snap.time_kinematics_us),
            ("interpolation_us", snap.time_interpolation_us),
            ("blit_ms", blit_ms),
            ("stroke_velocity", snap.stroke_velocity),
            ("stabilizer_lag_px", snap.stabilizer_lag_px),
            ("dabs_per_second", snap.total_dabs_per_second),
            ("dirty_area_px", snap.last_dirty_area_px),
            ("tiles_recorded", snap.last_tiles_recorded),
        ):
            peaks[key] = max(peaks[key], value)
        if vp_fps > 0:
            peaks["min_fps"] = min(peaks["min_fps"], vp_fps)

        new_state, state_key, cause = diagnose(
            snap.time_raster_dab_us, snap.time_undo_record_us, snap.time_composite_us, blit_ms)
        if state_key != self._current_state_key:
            self.record_state_transition(new_state, state_key, cause)
        return new_state, state_key, cause

    def generate_full_report(self, stay_on_top: Optional[bool] = None) -> str:
        """Relatório completo com a leitura mais recente do motor e da viewport."""
        from ui.core.engine.registry import EngineRegistry
        from .telemetry_report import build_report

        backend = EngineRegistry.instance().get_backend()
        snap = backend.get_telemetry_snapshot() if backend is not None else self._last_snap
        vp = EngineRegistry.get_viewport_telemetry() or self._last_vp
        return build_report(self, snap, vp, stay_on_top)
