"""
ui.core.engine.registry — EngineRegistry
=========================================
Registro singleton do EngineBackend ativo da aplicação.

Plugins de sistema (ex.: o futuro workspace_core) chamam
`EngineRegistry.instance().setup(create_backends())` durante o boot para
plugarem o motor disponível (Rust/WGPU, software, etc.). A casca consome
apenas `get_backend()`.

Motor → documento: o backend avisa "documento X modificado (motivo)" por
`notify_document_modified`; quem guarda os documentos (`DocumentManager`)
escuta com `add_document_modified_listener`. Até 2026-09-24 o backend
importava o `DocumentManager` para marcar o documento sujo.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

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
        self._document_modified_listeners: list[Callable[[str, str], None]] = []

    # ── Configuração ─────────────────────────────────────────────────────

    def setup(self, backends: List[EngineBackend]) -> Optional[EngineBackend]:
        """
        Recebe a lista de backends disponíveis (criados pelas factories de
        `ui/infrastructure/bridge_client`) e ativa o primeiro cujo `available` for True.

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

    # ── Motor → documento ────────────────────────────────────────────────

    def add_document_modified_listener(self, listener: Callable[[str, str], None]) -> None:
        """`listener(uid_do_documento, motivo)` a cada mudança feita pelo motor."""
        if listener not in self._document_modified_listeners:
            self._document_modified_listeners.append(listener)

    def remove_document_modified_listener(self, listener: Callable[[str, str], None]) -> None:
        if listener in self._document_modified_listeners:
            self._document_modified_listeners.remove(listener)

    def notify_document_modified(self, uid: Optional[str], reason: str) -> None:
        """Chamado pelo backend quando o conteúdo de um documento muda."""
        if uid is None:
            return
        for listener in list(self._document_modified_listeners):
            listener(uid, reason)

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