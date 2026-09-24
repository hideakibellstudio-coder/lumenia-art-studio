import logging


class PluginContext:
    """
    Contexto injetado nos plugins durante sua ativação.
    Centraliza o acesso seguro a recursos do núcleo sem imports globais.

    Propriedades disponíveis:
        bridge_client    — BridgeClient singleton (operações síncronas no renderer)
        main_window      — QMainWindow principal (injetado via PluginManager.set_main_window)
        service_registry — ServiceRegistry singleton (registro/consulta de serviços entre plugins)
    """

    def __init__(self, bridge_client):
        self._bridge_client    = bridge_client
        self._main_window      = None  # Injetado por PluginManager.set_main_window()
        self._service_registry = None  # Injetado por PluginManager após criação do ServiceRegistry
        self._loggers          = {}

    # ── Serviços de infraestrutura ─────────────────────────────────────────

    @property
    def bridge_client(self):
        """Retorna o BridgeClient unificado para operações síncronas/diretas no renderizador."""
        return self._bridge_client

    @property
    def backend(self):
        """Retorna o backend de motor ativo via EngineRegistry."""
        from ui.core.engine.registry import EngineRegistry
        return EngineRegistry.instance().get_backend()

    # ── Referências de UI e serviços de workspace ──────────────────────────

    @property
    def main_window(self):
        """
        Referência segura à QMainWindow principal do aplicativo.
        Injetada pelo PluginManager logo após a janela ser criada, antes de
        qualquer plugin ser ativado. O WorkspaceCore usa isso para chamar
        main_window.setCentralWidget(workspace_container).
        """
        return self._main_window

    @property
    def service_registry(self):
        """
        ServiceRegistry singleton — permite que plugins registrem e consultem
        serviços tipados entre si sem acoplamento direto.
        Exemplo: ServiceRegistry.get_service(WorkspaceService)
        """
        return self._service_registry

    # ── Logging ───────────────────────────────────────────────────────────

    def get_logger(self, plugin_id: str) -> logging.Logger:
        """Gera um logger isolado e pré-configurado para o plugin especificado."""
        if plugin_id not in self._loggers:
            self._loggers[plugin_id] = logging.getLogger(f"plugin.{plugin_id}")
        return self._loggers[plugin_id]

