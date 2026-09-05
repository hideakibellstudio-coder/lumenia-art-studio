"""
ui.core.engine.registry — EngineRegistry
=========================================
Registro singleton do EngineBackend ativo da aplicação.

Plugins de sistema (ex.: o futuro workspace_core) chamam
`EngineRegistry.instance().setup(create_backends())` durante o boot para
plugarem o motor disponível (Rust/WGPU, software, etc.). A casca consome
apenas `get_backend()` / `dispatch()`.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional

from ui.core.engine.backend import EngineBackend

logger = logging.getLogger(__name__)


class EngineRegistry:
    """Singleton que detém o backend de motor ativo da casca."""

    _instance: "EngineRegistry | None" = None

    @classmethod
    def instance(cls) -> "EngineRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._backend: Optional[EngineBackend] = None

    # ── Configuração ─────────────────────────────────────────────────────

    def setup(self, backends: List[EngineBackend]) -> Optional[EngineBackend]:
        """
        Recebe a lista de backends disponíveis (criados pelas factories de
        `ui/engine_backends`) e ativa o primeiro cujo `available` for True.

        Retorna o backend ativo (ou None se nenhum motor estiver presente).
        """
        for backend in backends:
            try:
                if backend.available:
                    self._backend = backend
                    logger.info(
                        f"[EngineRegistry] Backend de motor ativo: '{backend.name}'."
                    )
                    return backend
            except Exception as e:  # pragma: no cover
                logger.warning(
                    f"[EngineRegistry] Backend '{getattr(backend, 'name', '?')}' "
                    f"indisponível: {e}"
                )
        self._backend = None
        logger.info(
            "[EngineRegistry] Nenhum backend de motor disponível. "
            "A interface roda em modo casca (canvas vazio)."
        )
        return None

    def set_backend(self, backend: Optional[EngineBackend]) -> None:
        """Define (ou remove) o backend ativo manualmente."""
        self._backend = backend

    # ── Consulta ─────────────────────────────────────────────────────────

    def get_backend(self) -> Optional[EngineBackend]:
        """Retorna o backend ativo, ou None se a casca estiver sem motor."""
        return self._backend

    # ── Atalhos de despacho ──────────────────────────────────────────────

    def dispatch(self, command: Any) -> None:
        """Despacha um comando para o backend ativo (no-op se não houver motor)."""
        backend = self._backend
        if backend is None:
            logger.debug("[EngineRegistry] Comando descartado — sem backend de motor.")
            return
        backend.dispatch(command)

    def clear(self) -> None:
        """Remove o backend ativo (usado em testes/boot limp)."""
        self._backend = None

    # ── Telemetria da Viewport (Qt Blit & Taxa da Tela) ───────────────────

    _viewport_telemetry_provider: Optional[Any] = None

    @classmethod
    def register_viewport_telemetry_provider(cls, provider: Any) -> None:
        """Registra o provedor de métricas da Viewport (ex: RenderWidget)."""
        cls._viewport_telemetry_provider = provider

    @classmethod
    def get_viewport_telemetry(cls) -> dict[str, Any]:
        """Retorna as métricas da Viewport ativa sem acoplamento direto de plugin."""
        if cls._viewport_telemetry_provider is not None:
            try:
                return cls._viewport_telemetry_provider()
            except Exception:
                return {}
        return {}