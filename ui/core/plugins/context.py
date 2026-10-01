class PluginContext:
    """
    Contexto injetado nos plugins durante sua ativação.

    Propriedades disponíveis:
        main_window      — QMainWindow principal (entregue por PluginManager.attach_main_window);
                           só o WorkspaceCore a usa, para `setCentralWidget`
        service_registry — ServiceRegistry (registro/consulta de serviços entre plugins)

    O motor não está aqui: um plugin que precisa dele recebe um serviço que o expõe pelo contrato
    que ele usa (a casca instala), em vez de um `EngineBackend` inteiro. Até 2026-10-01 o contexto
    também trazia `backend` (o motor inteiro, para todo plugin, inclusive os de terceiros que a
    instalação de pacotes permite) e `get_logger`; nenhum plugin usava os dois (medido: os 21 usos
    do contexto em `ui/plugins/` são `service_registry` e um `main_window`), e o contexto já tinha
    perdido `bridge_client` pelo mesmo motivo em 2026-09-24. `tests/test_plugin_context_contract.py`
    trava a superfície.
    """

    def __init__(self, service_registry):
        self._main_window      = None  # Entregue por PluginManager.attach_main_window()
        self._service_registry = service_registry

    def attach_main_window(self, main_window) -> None:
        """A janela principal nasce depois do contexto; o PluginManager a entrega aqui."""
        self._main_window = main_window

    @property
    def main_window(self):
        """
        Referência à QMainWindow principal do aplicativo.
        Entregue pelo PluginManager logo após a janela ser criada, antes de qualquer plugin ser
        ativado. O WorkspaceCore usa isso para chamar main_window.setCentralWidget(workspace_container).
        """
        return self._main_window

    @property
    def service_registry(self):
        """
        ServiceRegistry singleton — permite que plugins registrem e consultem serviços tipados
        entre si sem acoplamento direto.
        Exemplo: ServiceRegistry.get_service(WorkspaceService)
        """
        return self._service_registry
