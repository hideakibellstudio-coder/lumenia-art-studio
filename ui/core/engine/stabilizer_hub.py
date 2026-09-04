"""
StabilizerHub — Gerenciador Central de Perfis e Estado de Estabilização.
========================================================================
Sincroniza globalmente o estado do estabilizador entre:
1. Barra Superior de Ferramentas (ToolSidebar - ao lado de Limpar Tela)
2. Painel Avançado de Pincéis (slider_stabilizer) e Brush Dock (stabilizer_slider)
3. Painel de Controle na Doca (StabilizerLabPanel)
4. Motor C++ Nativo (PaintEngineFacade -> DynamicStabilizer)

Padrão de Ícones: 100% vetorial SVG dinâmico via ui.core.icons (sem emojis).
"""

from __future__ import annotations
import math
import logging
from typing import Any, Dict, Optional
from PySide6 import QtCore

logger = logging.getLogger(__name__)


class StabilizerHub(QtCore.QObject):
    """Singleton reativo de estado de estabilização do Lumenia (Single Source of Truth)."""

    _instance: Optional[StabilizerHub] = None

    profileChanged = QtCore.Signal(str)       # "off", "fluid", "painting", "lineart", "sculpted", "silk"
    fineTuningChanged = QtCore.Signal(int)    # 0 a 100%
    activeToggled = QtCore.Signal(bool)       # True / False
    parametersChanged = QtCore.Signal()       # Notificação geral

    PROFILES: dict[str, dict[str, Any]] = {
        "off": {
            "name": "Direto (Sem Amortecimento)",
            "icon_name": "stabilizer_off",
            "default_pct": 0,
            "min_buffer": 1,
            "max_buffer": 1,
            "min_alpha": 1.0,
            "max_alpha": 1.0,
            "gamma": 1.0,
            "smooth_pressure": False,
            "description": "Zero latência, resposta crua do sensor da mesa."
        },
        "fluid": {
            "name": "Fluido (Rascunho Rápido)",
            "icon_name": "stabilizer_fluid",
            "default_pct": 20,
            "min_buffer": 3,
            "max_buffer": 8,
            "min_alpha": 0.45,
            "max_alpha": 0.85,
            "gamma": 1.20,
            "smooth_pressure": True,
            "description": "Remove micro-tremores do digitalizador sem sensação de arrasto."
        },
        "painting": {
            "name": "Pintura & Ilustração",
            "icon_name": "stabilizer_paint",
            "default_pct": 40,
            "min_buffer": 8,
            "max_buffer": 16,
            "min_alpha": 0.28,
            "max_alpha": 0.50,
            "gamma": 1.35,
            "smooth_pressure": True,
            "description": "Equilíbrio orgânico ideal para hachuras, sombras e arte digital."
        },
        "lineart": {
            "name": "Lineart & Mangá",
            "icon_name": "stabilizer_lineart",
            "default_pct": 65,
            "min_buffer": 16,
            "max_buffer": 32,
            "min_alpha": 0.16,
            "max_alpha": 0.32,
            "gamma": 1.45,
            "smooth_pressure": True,
            "description": "Linha limpa clássica com pontas vivas e firmeza de contorno."
        },
        "sculpted": {
            "name": "Contorno Esculpido (Super 1)",
            "icon_name": "stabilizer_sculpted",
            "default_pct": 85,
            "min_buffer": 36,
            "max_buffer": 75,
            "min_alpha": 0.08,
            "max_alpha": 0.18,
            "gamma": 1.55,
            "smooth_pressure": True,
            "description": "Inércia pesada para arcos longos, mechas de cabelo e curvas amplas."
        },
        "silk": {
            "name": "Fita de Seda / Cirúrgico (Super 2)",
            "icon_name": "stabilizer_silk",
            "default_pct": 100,
            "min_buffer": 75,
            "max_buffer": 140,
            "min_alpha": 0.028,
            "max_alpha": 0.09,
            "gamma": 1.65,
            "smooth_pressure": True,
            "description": "Amortecimento máximo absoluto; matematicamente impossível tremer."
        },
    }

    @classmethod
    def instance(cls) -> StabilizerHub:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._current_profile: str = "lineart"
        self._fine_tuning_pct: int = 65
        self._is_active: bool = True
        self._flush_speed: float = 1.0
        self._is_updating: bool = False

    # ── Getters / Setters com Sincronização Bidirecional ──

    @property
    def current_profile(self) -> str:
        return self._current_profile

    def set_profile(self, profile_id: str, source: str | None = None) -> None:
        if profile_id not in self.PROFILES:
            return

        if self._is_updating:
            return
        self._is_updating = True
        try:
            profile_changed = (self._current_profile != profile_id)
            self._current_profile = profile_id

            # Ao selecionar um perfil, posiciona o slider na porcentagem canônica daquele perfil
            def_pct = self.PROFILES[profile_id]["default_pct"]
            pct_changed = (self._fine_tuning_pct != def_pct)
            self._fine_tuning_pct = def_pct

            # Notifica backend C++ imediatamente
            self._sync_backend(def_pct)

            if profile_changed:
                self.profileChanged.emit(profile_id)
            if pct_changed:
                self.fineTuningChanged.emit(def_pct)
            self.parametersChanged.emit()

        finally:
            self._is_updating = False

    @property
    def fine_tuning_pct(self) -> int:
        return self._fine_tuning_pct

    def set_fine_tuning_pct(self, val: int, source: str | None = None) -> None:
        val = max(0, min(100, int(val)))
        if self._is_updating:
            return
        self._is_updating = True
        try:
            pct_changed = (self._fine_tuning_pct != val)
            self._fine_tuning_pct = val

            # Mapeia dinamicamente para o perfil correspondente na barra do topo
            new_profile = self._infer_profile_from_pct(val)
            profile_changed = (self._current_profile != new_profile)
            self._current_profile = new_profile

            # Atualiza backend C++
            self._sync_backend(val)

            if pct_changed:
                self.fineTuningChanged.emit(val)
            if profile_changed:
                self.profileChanged.emit(new_profile)
            self.parametersChanged.emit()

        finally:
            self._is_updating = False

    def _infer_profile_from_pct(self, pct: int) -> str:
        if pct <= 0:
            return "off"
        elif pct <= 25:
            return "fluid"
        elif pct <= 50:
            return "painting"
        elif pct <= 75:
            return "lineart"
        elif pct <= 90:
            return "sculpted"
        else:
            return "silk"

    def _sync_backend(self, pct: int) -> None:
        try:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            if backend and hasattr(backend, "set_stabilizer_weight"):
                backend.set_stabilizer_weight(pct / 100.0)
        except Exception as e:
            logger.debug("[StabilizerHub] Backend sync erro ignorado: %s", e)

    @property
    def is_active(self) -> bool:
        return self._is_active

    def set_active(self, active: bool) -> None:
        if self._is_active != active:
            self._is_active = active
            self.activeToggled.emit(active)
            self.parametersChanged.emit()

    @property
    def flush_speed(self) -> float:
        return self._flush_speed

    def set_flush_speed(self, speed: float) -> None:
        self._flush_speed = max(0.2, min(2.5, float(speed)))
        self.parametersChanged.emit()

    # ── Parâmetros Calculados com Base no SAI Ver.2 ──

    def get_calculated_params(self) -> dict[str, Any]:
        p_info = self.PROFILES.get(self._current_profile, self.PROFILES["lineart"])
        s = self._fine_tuning_pct / 100.0  # 0.0 a 1.0

        min_buf = p_info["min_buffer"]
        max_buf = p_info["max_buffer"]
        min_a = p_info["min_alpha"]
        max_a = p_info["max_alpha"]
        gamma = p_info["gamma"]
        smooth_p = p_info["smooth_pressure"]

        if not self._is_active or self._current_profile == "off":
            return {
                "profile_id": "off",
                "buffer_capacity": 1,
                "alpha": 1.0,
                "gamma": 1.0,
                "smooth_pressure": False,
                "flush_speed": 1.0,
            }

        capacity = max(1, int(round(min_buf + (max_buf - min_buf) * s)))

        if max_a > 0.0 and min_a > 0.0:
            alpha = max_a * math.pow(min_a / max_a, s)
        else:
            alpha = max_a

        return {
            "profile_id": self._current_profile,
            "buffer_capacity": capacity,
            "alpha": alpha,
            "gamma": gamma,
            "smooth_pressure": smooth_p,
            "flush_speed": self._flush_speed,
        }
