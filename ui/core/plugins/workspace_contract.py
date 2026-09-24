from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
    from PySide6.QtGui import QPainter


class WorkspaceService(ABC):
    """
    Contrato público exposto pelo WorkspaceCore para outros plugins.

    Outros plugins NÃO devem importar WorkspaceContainer ou WorkspaceCore
    diretamente. Em vez disso, consultam este serviço via ServiceRegistry:

        from ui.core.plugins.service_registry import ServiceRegistry
        from ui.core.plugins.workspace_contract import WorkspaceService

        ws = ServiceRegistry.instance().get(WorkspaceService)
        ws.add_panel("layers", "Camadas", LayersPanel(), area="right")

    Isso garante que os plugins de UI não tenham acoplamento estático ao
    WorkspaceCore, podendo ser carregados/descarregados de forma independente.
    """

    # ── Gestão de Painéis ─────────────────────────────────────────────────

    @abstractmethod
    def add_panel(
        self,
        panel_id:  str,
        title:     str,
        widget:    "QWidget",
        area:      str = "right",
        icon_path: str | None = None,
    ) -> None:
        """
        Registra e monta um painel na doca dinâmica especificada.

        Args:
            panel_id:   Identificador único do painel (ex.: "brush", "layers").
            title:      Título exibido no cabeçalho da doca.
            widget:     Widget do painel a ser inserido.
            area:       Área de destino — "left" ou "right".
            icon_path:  Caminho opcional para o ícone exibido na sidebar de ícones.
        """
        ...

    @abstractmethod
    def remove_panel(self, panel_id: str) -> None:
        """
        Remove e destrói o painel com o ID especificado.
        Não levanta exceção se o painel não existir.

        Args:
            panel_id: Identificador do painel a remover.
        """
        ...

    # ── Acesso ao Canvas ──────────────────────────────────────────────────

    @property
    @abstractmethod
    def canvas(self) -> "QWidget":
        """
        Referência read-only ao CanvasWidget ativo.
        Plugins que precisam conectar sinais ao canvas devem usar esta
        propriedade em vez de acessar MainWindow diretamente.
        """
        ...

    @property
    @abstractmethod
    def workspace_container(self) -> "QWidget":
        """
        Referência read-only ao WorkspaceContainer — o widget central que
        hospeda canvas, docas e elementos flutuantes.
        Plugins avançados podem usar isso para acessar métodos de wiring
        como connect_brush_dock() e connect_properties_dock().
        """
        ...

    def request_canvas_repaint(self) -> None:
        """
        Agenda o repaint do canvas ativo. Caminho canônico para painéis e para o
        modelo de documento pedirem atualização visual sem varrer a árvore de
        widgets (ver ui/core/plugins/canvas_access.py).
        """
        canvas = self.canvas
        if canvas is not None:
            canvas.update()

    # ── Renderização Compartilhada de Overlays ────────────────────────────

    def render_geometry_overlay(
        self,
        painter: "QPainter",
        sym_data: dict | None = None,
        guide_data: dict | None = None,
        zoom: float = 1.0,
    ) -> None:
        """
        Renderiza eixos de simetria e guias de perspectiva sobre um QPainter externo.
        Permite que plugins clientes (como o Timelapse) renderizem overlays sem
        acoplamento estático a módulos internos do workspace_core.
        """
        pass

