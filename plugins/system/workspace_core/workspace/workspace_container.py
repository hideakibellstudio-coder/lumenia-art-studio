"""
WorkspaceContainer
==================
Widget central autônomo que encapsula:
  - CanvasWidget (RenderWidget, raster CPU entregue pelo motor Aladyn C++)
  - TabbedViewportContainer (abas de documento)
  - Todo o wiring de sinais brush ↔ renderer
  - Todo o wiring de câmera canvas ↔ navigator
  - Gestão de troca de documento ativo

CONVENÇÃO DE JANELAS FLUTUANTES:
  Elementos que precisam flutuar SOBRE o canvas (barra de ferramentas,
  barra de opções secundária, painéis avançados de pincel/geometria) são
  janelas Qt.Tool independentes -- ver FloatingToolWindow em
  ui/core/dialogs/floating_tool_window.py. Isso é herdado de uma geração
  anterior do motor (Rust/WGPU, quando o CanvasWidget realmente escrevia
  direto num HWND nativo via WA_PaintOnScreen); não foi revalidado após a
  migração para o motor Aladyn C++ atual, que pinta o canvas por
  QPainter.drawImage() normal dentro de paintEvent (ver
  RenderWidget/ViewportRenderer). Na prática isso deixou de importar como
  causa do problema que motivou essa investigação: até menus QMenu padrão
  do Qt (que não têm nada a ver com essa regra) somem em captura de tela
  "por janela específica" (OBS Window Capture, Win+G) -- é uma limitação
  documentada do Windows/OBS com qualquer app, não do Lumenia. Ver
  claude/panorama-ui-global-subjanelas-captura-tela.md no projeto para o
  diagnóstico completo antes de tentar remover essa convenção.

Este módulo será injetado na MainWindow pelo WorkspaceCore system plugin na Fase 3.
Por enquanto (Fase 2), é instanciável diretamente para validação visual.
"""

from __future__ import annotations

import logging
from functools import partial

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.core.plugins.panel_ids import PanelId
from ui.core.state import BrushEngineSync, BrushState, GeometryState, ToolState

from .canvas.render_widget import CanvasWidget
from .canvas_brush_binding import CanvasBrushBinding
from .canvas_tool_binding import CanvasToolBinding
from .document_view_sync import DocumentViewSync
from .dock_system import AdvancedDockSystem
from .floating_toolbar import FloatingToolbar
from .panel_connections import PanelConnections
from .pill_handle import PillHandle
from .secondary_tool_bar import SecondaryToolBar
from .stroke_preview_sync import StrokePreviewSync
from .viewport_container import TabbedViewportContainer
from .workspace_layout import WorkspaceLayout

logger = logging.getLogger("Workspace.Container")

_HISTORY_ERROR_MESSAGES = {
    "scratch_read_failed": "scratch disk do histórico indisponível",
    "scratch_write_failed": "scratch disk do histórico não aceitou a gravação",
    "history_corrupt_snapshot": "snapshot do histórico corrompido",
    "history_invalid_snapshot": "snapshot do histórico inválido",
    "history_busy": "histórico ocupado por outra operação",
    "history_restore_failed": "falha ao restaurar o snapshot",
}


def history_failure_message(action: str, error: str) -> str:
    detail = _HISTORY_ERROR_MESSAGES.get(error, error)
    return f"Falha ao {action}: {detail}. Documento preservado."


class WorkspaceContainer(QtWidgets.QWidget):
    """
    Widget central do Lumenia: monta canvas, abas, docas e barras e liga as
    peças. Cada assunto tem um colaborador com estado próprio:

      layout_ctrl (WorkspaceLayout) ...... gavetas, pílulas, barras flutuantes
      _view_sync (DocumentViewSync) ...... documento ativo no canvas; câmera ↔ navegador
      _panels (PanelConnections) ......... painéis de plugins e suas conexões
      _canvas_tools / _canvas_brush ...... estado de ferramenta e pincel → canvas
      _preview_sync (StrokePreviewSync) .. miniaturas depois de cada traço

    Até 2026-09-24 era composto por quatro mixins que leem e escrevem
    atributos uns dos outros por `self`.

    Sinais emitidos:
        newDocumentRequested()  — usuário clicou "+" na tab bar
        documentCloseRequested(uid: str) — usuário fechou uma aba
        zoomChanged(zoom: float) — zoom do canvas mudou (para StatusBar)
        statusMessage(texto: str, ms: int) — mensagem para a barra de status
            (a janela principal liga; antes o workspace procurava
            `self.window().statusBar()` com hasattr)
        panelVisibilityChanged(id: str, visível: bool) — painel apareceu ou
            sumiu numa gaveta (o menu Janela marca o item)
    """

    newDocumentRequested  = QtCore.Signal()
    documentCloseRequested = QtCore.Signal(str)
    zoomChanged           = QtCore.Signal(float)
    statusMessage         = QtCore.Signal(str, int)
    panelVisibilityChanged = QtCore.Signal(str, bool)

    def __init__(
        self,
        brush_state: BrushState,
        brush_sync: BrushEngineSync,
        tool_state: ToolState,
        geometry_state: GeometryState,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tool_state = tool_state
        self._dm = DocumentManager.instance()
        backend = EngineRegistry.instance().get_backend
        self._panels = PanelConnections()

        # ── Abas no topo; embaixo: doca esquerda | canvas | doca direita ──
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.canvas_widget = CanvasWidget(self, geometry_state)
        self.viewport_container = TabbedViewportContainer(self.canvas_widget, self)
        main_layout.addWidget(self.viewport_container.header_widget)
        self.workspace_area = QtWidgets.QWidget(self)
        area_layout = QtWidgets.QHBoxLayout(self.workspace_area)
        area_layout.setContentsMargins(0, 0, 0, 0)
        area_layout.setSpacing(0)
        main_layout.addWidget(self.workspace_area, 1)

        self.left_dock = AdvancedDockSystem("left", self.workspace_area, self)
        self.right_dock = AdvancedDockSystem("right", self.workspace_area, self)
        area_layout.addWidget(self.left_dock)
        area_layout.addWidget(self.viewport_container, 1)
        area_layout.addWidget(self.right_dock)
        self.left_dock.panel_visibility_changed.connect(self.panelVisibilityChanged)
        self.right_dock.panel_visibility_changed.connect(self.panelVisibilityChanged)
        # Pílulas: filhas do workspace_area, nunca do canvas.
        left_pill = PillHandle("left", self.workspace_area)
        right_pill = PillHandle("right", self.workspace_area)
        self.left_dock.inject_pill(left_pill)
        self.right_dock.inject_pill(right_pill)

        # ── Barras flutuantes (janelas Qt.Tool) ────────────────────────────
        self.floating_toolbar = FloatingToolbar(tool_state, parent=self)
        self.secondary_toolbar = SecondaryToolBar(tool_state, brush_state, parent=self)
        self.secondary_toolbar.commandRequested.connect(self.canvas_widget.run_tool_command)
        self.layout_ctrl = WorkspaceLayout(
            self.workspace_area, self.left_dock, self.right_dock, left_pill, right_pill,
            self.floating_toolbar, self.secondary_toolbar, self,
        )
        # A barra flutuante muda de tamanho com a ferramenta: reposiciona depois
        # (conexão feita depois da dela, então roda depois).
        tool_state.activeToolChanged.connect(self._on_active_tool_changed)
        from ui.core.screens.dock_settings_dialog import load_dock_settings
        from ui.core.screens.floating_toolbar_settings_dialog import load_floating_toolbar_settings
        QtCore.QTimer.singleShot(0, self, lambda: self.apply_dock_settings(load_dock_settings()))
        QtCore.QTimer.singleShot(0, self, lambda: self.apply_floating_toolbar_settings(load_floating_toolbar_settings()))

        # ── Sinais públicos ────────────────────────────────────────────────
        self.viewport_container.newDocumentRequested.connect(self.newDocumentRequested)
        self.viewport_container.documentCloseRequested.connect(self.documentCloseRequested)
        self.canvas_widget.zoomChanged.connect(self.zoomChanged)

        # ── Colaboradores ──────────────────────────────────────────────────
        self._canvas_tools = CanvasToolBinding(tool_state, self.canvas_widget, self.show_status, self)
        self._canvas_brush = CanvasBrushBinding(brush_state, self.canvas_widget, self)
        self._preview_sync = StrokePreviewSync(backend, self._dm.active_document, self)
        self._view_sync = DocumentViewSync(
            self.canvas_widget, self.viewport_container.sync_active_tab, self._dm,
            brush_state, brush_sync, backend, self,
        )

        # ── Durante o traço: gavetas quietas; depois, miniaturas ────────────
        canvas = self.canvas_widget
        canvas.strokeStarted.connect(lambda: self.layout_ctrl.set_painting(True))
        canvas.strokeStarted.connect(self.layout_ctrl.close_unpinned_drawers)
        canvas.strokeFinished.connect(lambda: self.layout_ctrl.set_painting(False))
        canvas.strokeFinished.connect(self._preview_sync.schedule)
        # Clique no canvas fecha gavetas despinadas (filtro de eventos).
        canvas.installEventFilter(self)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (watched is self.canvas_widget and event.type() == QtCore.QEvent.MouseButtonPress
                and self.layout_ctrl.has_unpinned_open):
            self.layout_ctrl.close_unpinned_drawers()
            return True  # o clique que fecha a gaveta não começa um traço
        return super().eventFilter(watched, event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.layout_ctrl.refresh()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(50, self, self.layout_ctrl.update_toolbar_position)

    def retranslate_ui(self) -> None:
        """Docas e barra flutuante; a barra secundária se traduz sozinha."""
        self.layout_ctrl.retranslate()

    def _on_active_tool_changed(self, _tool: str, _previous: str) -> None:
        self.layout_ctrl.update_toolbar_position()

    # ── Engine ────────────────────────────────────────────────────────────

    def initialize_engine(self) -> None:
        """
        Inicializa o backend ativo (EngineRegistry). Chamado depois de o widget
        entrar na hierarquia de janelas (setCentralWidget). Sem backend (ou com
        falha de inicialização) a casca segue com o canvas vazio.
        """
        try:
            self.canvas_widget.init_engine()
        except BaseException as e:  # noqa: BLE001 — motores nativos podem levantar exceções fora da hierarquia padrão
            logger.error(f"[WorkspaceContainer] Falha ao inicializar motor: {type(e).__name__}: {e}")

    # ── Painéis de plugins (contrato WorkspaceService) ────────────────────

    def add_panel(
        self,
        panel_id:  str,
        title:     str,
        widget:    QtWidgets.QWidget,
        area:      str = "right",
        icon_path: str | None = None,
    ) -> None:
        """Registra e monta um painel na doca `area` ("left" ou "right")."""
        previous = self._panels.widget(panel_id)
        if previous is widget:
            return
        if previous is not None:
            self.remove_panel(panel_id)
        self._panels.register(panel_id, widget)
        self._bind_known_panel(panel_id, widget)
        dock = self.left_dock if area == "left" else self.right_dock
        try:
            dock.add_panel(panel_id, title, widget, icon_path)
        except Exception:
            self._panels.release(panel_id)
            raise

    def _bind_known_panel(self, panel_id: str, widget) -> None:
        """Painéis cujo id faz parte do contrato WorkspaceService.

        As conexões ficam no `PanelConnections` e caem com `remove_panel`.
        """
        bind = partial(self._panels.bind, panel_id)
        sync = self._view_sync
        doc = self._dm.active_document()
        if panel_id == PanelId.NAVIGATOR:
            bind(widget.camera_changed_by_user, sync.set_camera_from_navigator)
            bind(widget.flip_changed_by_user, sync.set_flip_from_navigator)
            bind(widget.request_global_fit_view, self.reset_view)
            bind(sync.hasDocumentChanged, widget.set_has_document)
            bind(sync.canvasSizeChanged, widget.set_canvas_size)
            bind(sync.viewportChanged, widget.update_viewport)
            bind(self._preview_sync.navigatorArtwork, widget.set_artwork)
            if doc is not None:
                widget.set_canvas_size(doc.width, doc.height)
                widget.set_has_document(True)
                sync.sync_navigator()
        elif panel_id == PanelId.LAYERS:
            bind(sync.layerManagerChanged, widget.set_layer_manager)
            if doc is not None:
                widget.set_layer_manager(doc.layer_manager)

    def remove_panel(self, panel_id: str) -> None:
        """Desfaz as conexões do painel e o tira das duas docas."""
        self._panels.release(panel_id)
        self.left_dock.remove_panel(panel_id)
        self.right_dock.remove_panel(panel_id)

    def panel(self, panel_id: str):
        """Widget registrado por `add_panel` (None se não houver)."""
        return self._panels.widget(panel_id)

    # ── Contrato com a janela principal (ui/boundary/orchestrator/workspace_port.py) ──

    def canvas_area_rect(self) -> QtCore.QRect:
        """Área do canvas entre as docas (gavetas abertas incluídas), em coordenadas globais."""
        top = self.workspace_area.mapToGlobal(QtCore.QPoint(0, 0)).y()
        left = self.left_dock.effective_right_x
        right = self.right_dock.effective_left_x
        return QtCore.QRect(left, top, max(0, right - left), self.workspace_area.height())

    def show_status(self, message: str, timeout_ms: int = 3500) -> None:
        """Mensagem curta para a barra de status (ver sinal `statusMessage`)."""
        self.statusMessage.emit(message, timeout_ms)

    def refresh_previews(self) -> None:
        """Refaz as miniaturas (navegador e camadas) a partir do motor.

        Para mudanças que alteram a imagem mostrada sem ser traço, como trocar
        o perfil de cor.
        """
        self._preview_sync.schedule()

    def refresh_document_state(self, doc) -> None:
        """Documento aberto de arquivo: mostra o estado dele sem capturar o anterior."""
        self._view_sync.show_document(doc, capture_previous=False)

    def undo(self) -> None:
        self._run_history("desfazer", "Desfazer executado com sucesso.", "Nada a desfazer.", redo=False)

    def redo(self) -> None:
        self._run_history("refazer", "Refazer executado com sucesso.", "Nada a refazer.", redo=True)

    def _run_history(self, action: str, done: str, nothing: str, *, redo: bool) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend is None:
            return
        document = self._dm.active_document()
        if document is not None:
            ok = document.history.redo(backend) if redo else document.history.undo(backend)
        else:
            ok = backend.redo() if redo else backend.undo()
        if ok:
            self.canvas_widget.update()
            self.show_status(done)
            self._preview_sync.schedule()
        else:
            error = backend.get_history_error()
            self.show_status(history_failure_message(action, error) if error else nothing)

    def reset_view(self) -> None:
        """Centraliza o canvas (publica a câmera: zoom na barra de status e navegador)."""
        if self._dm.active_document():
            self.canvas_widget.center_canvas()

    def zoom_in(self) -> None:
        self.canvas_widget.zoom = min(50.0, self.canvas_widget.zoom * 1.2)
        self.canvas_widget.publish_view(zoom_changed=True)

    def zoom_out(self) -> None:
        self.canvas_widget.zoom = max(0.05, self.canvas_widget.zoom / 1.2)
        self.canvas_widget.publish_view(zoom_changed=True)

    def toggle_panel_from_menu(self, panel_id: str, side: str) -> None:
        self.layout_ctrl.toggle_panel(panel_id, side)

    def collapse_all_sidebars(self) -> None:
        self.layout_ctrl.collapse_all()

    def expand_all_sidebars(self) -> None:
        self.layout_ctrl.expand_all()

    def apply_dock_settings(self, cfg: dict) -> None:
        self.layout_ctrl.apply_dock_settings(cfg)

    def dock_panels(self) -> dict:
        return self.layout_ctrl.dock_panels()

    def apply_floating_toolbar_settings(self, cfg: dict) -> None:
        self.layout_ctrl.apply_floating_toolbar_settings(cfg)

    # ── Propriedades de acesso público ────────────────────────────────────

    @property
    def active_document(self):
        return self._dm.active_document()

    @property
    def canvas(self) -> CanvasWidget:
        return self.canvas_widget

    @property
    def current_tool(self) -> str:
        return self._tool_state.active_tool
