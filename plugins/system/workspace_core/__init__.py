"""
WorkspaceCore — Plugin de Sistema do Lumenia
=============================================
Plugin de sistema com prioridade máxima (100) que:
  1. Cria e injeta o WorkspaceContainer como widget central da MainWindow
  2. Registra a implementação de WorkspaceService no ServiceRegistry
  3. Expõe a API pública add_panel/remove_panel para plugins de UI

Carregado ANTES de todos os outros plugins (get_priority = 100).
Se falhar, o boot do app é interrompido (is_system_plugin = True).

Plugins de UI (BrushPlugin, PropertiesPlugin) declaram:
    dependencies=["lumenia.workspace_core"]
para garantir que este plugin esteja ativo antes deles.
"""

from __future__ import annotations

import logging

from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.workspace_contract import WorkspaceService

logger = logging.getLogger(__name__)


class WorkspaceCore(BasePlugin, WorkspaceService):
    """
    Plugin de sistema central do Lumenia.
    Implementa WorkspaceService e o registra no ServiceRegistry
    para que outros plugins possam usar add_panel / remove_panel
    sem acoplamento estático ao WorkspaceContainer.
    """

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="lumenia.workspace_core",
            name="Workspace Core",
            version="2.0.0",
            author="Lumenia Team",
            description=(
                "Plugin de sistema que inicializa o WorkspaceContainer (canvas WGPU, "
                "docas dinâmicas e elementos flutuantes) e expõe o WorkspaceService."
            ),
            plugin_type=PluginType.SYSTEM,
            dependencies=[],
        )

    def is_system_plugin(self) -> bool:
        """
        Verdadeiro: se este plugin falhar, o app não pode abrir.
        O PluginManager lança RuntimeError e interrompe o boot.
        """
        return True

    def get_priority(self) -> int:
        """
        Prioridade 100 — carregado antes de todos os outros plugins.
        Plugins de UI ficam com prioridade < 100 (default = 0).
        """
        return 100

    # ── Ciclo de vida ─────────────────────────────────────────────────────

    def initialize(self, context) -> None:
        """
        Cria o WorkspaceContainer mas NÃO o injeta ainda na MainWindow.
        (O widget não pode ser parented antes de setCentralWidget.)
        """
        super().initialize(context)
        from .workspace.workspace_container import WorkspaceContainer
        # Sem parent aqui — será passado via setCentralWidget abaixo
        self._container = WorkspaceContainer()
        logger.info("[WorkspaceCore] WorkspaceContainer criado.")

    def activate(self) -> None:
        """
        Injeta o WorkspaceContainer na MainWindow e registra o serviço.
        Chamado após initialize() com a garantia de que main_window já foi injetado.
        """
        mw = self.context.main_window
        if mw is None:
            raise RuntimeError(
                "[WorkspaceCore] main_window não está disponível no PluginContext. "
                "Certifique-se de chamar PluginManager.set_main_window(self) antes de "
                "discover_plugins() na MainWindow."
            )

        # Injeta o container como widget central da janela principal
        mw.setCentralWidget(self._container)
        logger.info("[WorkspaceCore] WorkspaceContainer injetado como widget central.")

        # Inicializa o motor (ou segue em modo casca, canvas vazio, se não houver backend)
        self._container.initialize_engine()
        logger.info("[WorkspaceCore] Motor inicializado (ou casca pura).")

        # Registra o serviço para que outros plugins possam consultar
        registry = self.context.service_registry
        registry.register(WorkspaceService, self)
        logger.info("[WorkspaceCore] WorkspaceService registrado no ServiceRegistry.")

    def deactivate(self) -> None:
        """Remove o serviço do registry ao desativar (não chamado em produção para plugins de sistema)."""
        registry = self.context.service_registry
        registry.unregister(WorkspaceService, self)

    # ── WorkspaceService API ──────────────────────────────────────────────

    def add_panel(self, panel_id, title, widget, area="right", icon_path=None) -> None:
        """Delega ao WorkspaceContainer."""
        self._container.add_panel(panel_id, title, widget, area, icon_path)
        logger.debug(f"[WorkspaceCore] Painel '{panel_id}' adicionado na área '{area}'.")

    def remove_panel(self, panel_id) -> None:
        """Delega ao WorkspaceContainer."""
        self._container.remove_panel(panel_id)
        logger.debug(f"[WorkspaceCore] Painel '{panel_id}' removido.")

    @property
    def canvas(self):
        """Referência read-only ao CanvasWidget ativo."""
        return self._container.canvas_widget

    @property
    def workspace_container(self):
        """Referência read-only ao WorkspaceContainer."""
        return self._container
