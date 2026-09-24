import logging


class PluginContext:
    """
    Contexto injetado nos plugins durante sua ativação.
    Centraliza o acesso seguro a recursos do núcleo sem imports globais.

    Propriedades disponíveis:
        backend          — EngineBackend ativo (EngineRegistry), ou None sem motor
        main_window      — QMainWindow principal (entregue por PluginManager.set_main_window)
        service_registry — ServiceRegistry (registro/consulta de serviços entre plugins)

    Até 2026-09-24 havia também `bridge_client` (fachada antiga do motor, sem
    nenhum plugin usando) e o PluginManager escrevia nos atributos privados
    deste objeto.
    """

    def __init__(self, service_registry):
        self._main_window      = None  # Entregue por PluginManager.set_main_window()
        self._service_registry = service_registry
        self._loggers          = {}

    def attach_main_window(self, main_window) -> None:
        """A janela principal nasce depois do contexto; o PluginManager a entrega aqui."""
        self._main_window = main_window

    # ── Serviços de infraestrutura ─────────────────────────────────────────

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

