"""
ui.core.state — Estado de aplicação compartilhado entre componentes (fonte única).

Porta de entrada pública da pasta. Tudo que outro módulo precisa daqui é
importado deste arquivo; os módulos internos podem mudar sem aviso.

Quem cria: a casca (`ui/boundary/orchestrator/main_window.py`) chama
`install_app_state(...)` antes de descobrir os plugins.
Quem usa: plugins pedem ao `ServiceRegistry` do seu PluginContext
(`context.service_registry.get(BrushState)`) e injetam nos widgets pelo
construtor. Nenhum widget busca o estado sozinho.

Ver ui/core/state/README.md.
"""
from __future__ import annotations

from dataclasses import dataclass

from ui.core.plugins.registry import ServiceRegistry

from .brush_engine_sync import BackendProvider, BrushEngineSync
from .brush_params import BRUSH_PARAM_DEFAULTS, BrushParam, quick_params_from_preset
from .brush_state import BrushState


@dataclass(frozen=True)
class AppState:
    brush: BrushState
    brush_sync: BrushEngineSync


def install_app_state(registry: ServiceRegistry, backend_provider: BackendProvider) -> AppState:
    """Cria (uma vez por registry) e registra o estado compartilhado da aplicação.

    Idempotente: se já houver estado registrado, devolve o existente — várias
    MainWindow no mesmo processo (testes) compartilham o mesmo estado, como
    compartilham o mesmo ServiceRegistry.
    """
    brush = registry.get(BrushState)
    sync = registry.get(BrushEngineSync)
    if brush is None:
        brush = BrushState()
        registry.register(BrushState, brush)
    if sync is None:
        sync = BrushEngineSync(brush, backend_provider)
        registry.register(BrushEngineSync, sync)
    return AppState(brush=brush, brush_sync=sync)


def require(registry: ServiceRegistry, service: type):
    """Busca um serviço obrigatório; falha com mensagem clara se a casca não o instalou."""
    impl = registry.get(service)
    if impl is None:
        raise RuntimeError(
            f"{service.__name__} não está no ServiceRegistry. A casca deve chamar "
            "ui.core.state.install_app_state(...) antes de ativar os plugins."
        )
    return impl


__all__ = [
    "AppState",
    "BRUSH_PARAM_DEFAULTS",
    "BackendProvider",
    "BrushEngineSync",
    "BrushParam",
    "BrushState",
    "install_app_state",
    "quick_params_from_preset",
    "require",
]
