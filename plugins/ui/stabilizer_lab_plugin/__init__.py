"""
StabilizerLabPlugin — Plugin de Laboratório e Perfis de Estabilização.
======================================================================
Gerencia o ciclo de vida do novo motor de perfis diluídos (sem zonas mortas),
sincroniza a barra superior e o painel de doca, e executa a filtragem em tempo real.
"""

from __future__ import annotations
import logging
from typing import List, Tuple

from ui.core.plugins.base import BasePlugin, BrushDynamicsService
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService
from ui.core.plugins.registry import ServiceRegistry
from ui.core.engine.registry import EngineRegistry
from ui.core.engine.stabilizer_hub import StabilizerHub

from .algorithms import (
    AdaptiveProfileStabilizerEngine,
    InfinitePainterKalmanEngine,
    LumeniaBaselineEngine
)
from .panel import StabilizerLabPanel

logger = logging.getLogger(__name__)


class StabilizerLabPlugin(BasePlugin, BrushDynamicsService):
    """Plugin de dinâmica de pincel para experimentação e perfis de traço."""

    def __init__(self) -> None:
        super().__init__()
        self._panel: StabilizerLabPanel | None = None
        self.hub = StabilizerHub.instance()
        self.engine_mode = "profiles"  # "profiles" | "kalman" | "baseline"

        self.adaptive_engine = AdaptiveProfileStabilizerEngine()
        self.kalman_engine = InfinitePainterKalmanEngine()
        self.baseline_engine = LumeniaBaselineEngine()

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.stabilizer_lab",
            name="Estabilizador Lab (Perfis / SAI / Kalman / Lumenia)",
            version="2.0.0",
            author="Aladyn Team",
            description="Motor de perfis dinâmicos de estabilização sem zonas mortas, com controle no topo e na doca.",
            plugin_type=PluginType.UI,
            dependencies=["lumenia.workspace_core"],
        )

    def get_priority(self) -> int:
        return 35

    def initialize(self, context) -> None:
        super().initialize(context)

    def activate(self) -> None:
        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws is None:
            raise RuntimeError("[StabilizerLabPlugin] WorkspaceService não encontrado.")

        self._panel = StabilizerLabPanel(plugin=self)
        self._panel.modeChanged.connect(self.set_engine_mode)

        ws.add_panel(
            panel_id="stabilizer_lab",
            title="Estabilizador Lab",
            widget=self._panel,
            area="right",
            icon_path="brush",
        )

        ServiceRegistry.instance().register_service(BrushDynamicsService, self)

        self.hub.activeToggled.connect(self._on_hub_active_toggled)
        if self.hub.is_active:
            self._set_native_stabilizer(0.0)

        logger.info("[StabilizerLabPlugin] Ativado! Perfil inicial: %s", self.hub.current_profile)

    def deactivate(self) -> None:
        ServiceRegistry.instance().unregister_service(BrushDynamicsService, self)

        ws: WorkspaceService = self.context.service_registry.get(WorkspaceService)
        if ws and self._panel:
            try:
                ws.remove_panel("stabilizer_lab")
            except Exception as e:
                logger.warning("[StabilizerLabPlugin] Erro ao remover painel: %s", e)

        self._set_native_stabilizer(0.40)
        self._panel = None
        logger.info("[StabilizerLabPlugin] Desativado.")

    def set_engine_mode(self, mode: str) -> None:
        self.engine_mode = mode
        if self._panel:
            self._panel.update_telemetry("Modo Alterado", f"Motor: {mode.upper()}")

    def _set_native_stabilizer(self, weight: float) -> None:
        try:
            backend = EngineRegistry.instance().get_backend()
            if backend and hasattr(backend, "set_stabilizer_weight"):
                backend.set_stabilizer_weight(weight)
        except Exception as e:
            logger.debug("[StabilizerLabPlugin] Backend não disponível: %s", e)

    def _on_hub_active_toggled(self, active: bool) -> None:
        if active:
            self._set_native_stabilizer(0.0)
        else:
            self._set_native_stabilizer(0.40)

    # ── Contrato BrushDynamicsService ──

    def on_start_stroke(self, x: float, y: float, pressure: float, timestamp: float) -> tuple[float, float, float]:
        if not self.hub.is_active:
            return x, y, pressure

        if self.engine_mode == "profiles":
            self.adaptive_engine.reset(x, y, pressure)
            return x, y, self.adaptive_engine.current_p
        elif self.engine_mode == "kalman":
            self.kalman_engine.reset(x, y, pressure)
            return x, y, pressure
        elif self.engine_mode == "baseline":
            self.baseline_engine.reset(x, y, pressure)
            return x, y, pressure

        return x, y, pressure

    def process_stroke_point(self, x: float, y: float, pressure: float, timestamp: float) -> tuple[float, float, float]:
        if not self.hub.is_active:
            return x, y, pressure

        if self.engine_mode == "profiles":
            sx, sy, sp = self.adaptive_engine.update(x, y, pressure)
            if self._panel:
                params = self.hub.get_calculated_params()
                self._panel.update_telemetry(
                    f"Desenhando ({params['profile_id'].upper()})",
                    f"Buffer: {len(self.adaptive_engine.history)}/{params['buffer_capacity']} | α: {params['alpha']:.3f}"
                )
            return sx, sy, sp

        elif self.engine_mode == "kalman":
            kx, ky, kp = self.kalman_engine.update(x, y, pressure)
            if self._panel:
                self._panel.update_telemetry(
                    "Desenhando (Kalman 4D)",
                    f"Vel: {self.kalman_engine.last_vel_norm:.1f}px/s | Jerk: {self.kalman_engine.last_jerk_norm:.2f}"
                )
            return kx, ky, kp

        elif self.engine_mode == "baseline":
            lx, ly, lp = self.baseline_engine.update(x, y, pressure)
            if self._panel:
                self._panel.update_telemetry(
                    "Desenhando (Lumenia Antigo)",
                    f"Janela: {len(self.baseline_engine.history)}/{self.baseline_engine.MAX_WINDOW_SIZE}"
                )
            return lx, ly, lp

        return x, y, pressure

    def on_end_stroke(self) -> list[tuple[float, float, float]]:
        if not self.hub.is_active:
            return []

        if self.engine_mode == "profiles":
            flush_pts = self.adaptive_engine.flush()
            if self._panel and flush_pts:
                self._panel.update_telemetry("Pen Up (Flush)", f"{len(flush_pts)} pontos convergidos")
            return flush_pts

        elif self.engine_mode == "baseline":
            return self.baseline_engine.flush()

        elif self.engine_mode == "kalman":
            return self.kalman_engine.flush()

        return []
