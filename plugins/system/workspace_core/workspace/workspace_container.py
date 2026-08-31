"""
WorkspaceContainer
==================
Widget central autônomo que encapsula:
  - CanvasWidget (Surface WGPU)
  - TabbedViewportContainer (abas de documento)
  - Todo o wiring de sinais brush ↔ renderer
  - Todo o wiring de câmera canvas ↔ navigator
  - Gestão de troca de documento ativo

REGRA FUNDAMENTAL:
  Nenhum widget Qt filho pode ser sobreposto ao CanvasWidget (WGPU / WA_PaintOnScreen).
  Elementos que precisam flutuar SOBRE o canvas devem ser janelas Qt.Tool independentes
  (HWNDs separados, compostos pelo DWM do Windows sem flickering).

Este módulo será injetado na MainWindow pelo WorkspaceCore system plugin na Fase 3.
Por enquanto (Fase 2), é instanciável diretamente para validação visual.
"""

from __future__ import annotations

import math
import os
import logging
from typing import TYPE_CHECKING, Any

from PySide6 import QtCore, QtGui, QtWidgets

from .canvas.render_widget import CanvasWidget
from .workspace_layout_manager import WorkspaceLayoutMixin
from .workspace_document_sync import WorkspaceDocSyncMixin
from .workspace_brush_adapter import WorkspaceBrushMixin

logger = logging.getLogger("Workspace.Container")


class WorkspaceContainer(QtWidgets.QWidget, WorkspaceLayoutMixin, WorkspaceDocSyncMixin, WorkspaceBrushMixin):
    """
    Widget central do Lumenia.

    Responsabilidades:
    - Criar e hospedar o CanvasWidget e TabbedViewportContainer
    - Conectar sinais do BrushDock e PropertiesDock ao renderer
    - Sincronizar câmera canvas ↔ navigator
    - Gerenciar troca de documento ativo (salvar/restaurar câmera e cor)
    - Expor add_panel/remove_panel para o WorkspaceService (Fase 3+)

    Sinais emitidos:
        newDocumentRequested()  — usuário clicou "+" na tab bar
        documentCloseRequested(uid: str) — usuário fechou uma aba
        zoomChanged(zoom: float) — zoom do canvas mudou (para StatusBar)
    """

    # ── Sinais ────────────────────────────────────────────────────────────
    newDocumentRequested  = QtCore.Signal()
    documentCloseRequested = QtCore.Signal(str)
    zoomChanged           = QtCore.Signal(float)

    # ── Inicialização ─────────────────────────────────────────────────────

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        # ── Estado interno ────────────────────────────────────────────────
        self.canvas_w: int = 1920
        self.canvas_h: int = 1080

        # Cor ativa salva ao alternar para borracha; restaurada ao voltar para pincel
        self._saved_color: QtGui.QColor = QtGui.QColor("#000000")

        # Ferramenta ativa: "brush" | "eraser"
        self._current_tool: str = "brush"

        # UID do último documento ativo (para salvar câmera ao trocar de aba)
        self._last_active_doc_uid: str | None = None

        # Referências opcionais aos painéis (injetadas via connect_brush_dock / connect_properties_dock)
        self._brush_dock:      "BrushDock | None"      = None
        self._properties_dock: "PropertiesDock | None" = None

        # ── Layout Principal Vertical ─────────────────────────────────────
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Canvas + Viewport Container ───────────────────────────────────
        self.canvas_widget = CanvasWidget(self)

        from .viewport_container import TabbedViewportContainer
        self.viewport_container = TabbedViewportContainer(self.canvas_widget, self)

        # 1. Barra de Abas MDI no TOPO do Workspace (Largura Total abaixo do MenuBar)
        main_layout.addWidget(self.viewport_container.header_widget)

        # 2. Área de Conteúdo do Workspace (Horizontal: Doca Esquerda | Canvas | Doca Direita)
        self.workspace_area = QtWidgets.QWidget(self)
        workspace_layout = QtWidgets.QHBoxLayout(self.workspace_area)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        main_layout.addWidget(self.workspace_area, 1)

        # ── Re-emite sinais do viewport_container para quem escutar o WorkspaceContainer
        self.viewport_container.newDocumentRequested.connect(self.newDocumentRequested)
        self.viewport_container.documentCloseRequested.connect(self.documentCloseRequested)

        # ── Zoom → StatusBar (via sinal público) ──────────────────────────
        self.canvas_widget.zoomChanged.connect(self.zoomChanged)

        # ── DocumentManager ───────────────────────────────────────────────
        from ui.core.document.manager import DocumentManager
        self._dm = DocumentManager.instance()
        self._dm.activeDocumentChanged.connect(self._on_active_document_changed)
        self._dm.documentClosed.connect(self._on_document_closed_cleanup)

        # ── AdvancedDockSystem (Docas Laterais Dinâmicas) ──────────────────
        from .dock_system import AdvancedDockSystem
        self.left_dock  = AdvancedDockSystem("left",  self)
        self.right_dock = AdvancedDockSystem("right", self)

        # Adiciona na ordem física estrita do workspace_layout:
        # [left_dock] | [viewport_container (stretch 1)] | [right_dock]
        workspace_layout.addWidget(self.left_dock)
        workspace_layout.addWidget(self.viewport_container, 1)
        workspace_layout.addWidget(self.right_dock)

        # ── PillHandles (filhas do workspace_area — NUNCA do CanvasWidget) ──
        from .pill_handle import PillHandle
        self._pill_left  = PillHandle("left",  self.workspace_area)
        self._pill_right = PillHandle("right", self.workspace_area)
        self.left_dock.inject_pill(self._pill_left)
        self.right_dock.inject_pill(self._pill_right)

        # ── Configurações de gavetas (persistidas via QSettings) ───────────
        from ui.core.screens.dock_settings_dialog import load_dock_settings
        QtCore.QTimer.singleShot(0, lambda: self.apply_dock_settings(load_dock_settings()))

        # ── Barra Flutuante (FloatingToolbar - Janela Nativa Qt.Tool) ───────
        from .floating_toolbar import FloatingToolbar
        from .secondary_tool_bar import SecondaryToolBar
        from ui.core.screens.floating_toolbar_settings_dialog import load_floating_toolbar_settings
        self.floating_toolbar = FloatingToolbar(parent=self)
        self.floating_toolbar.drag_finished.connect(self._on_floating_toolbar_dropped)
        self.floating_toolbar.status_notification.connect(self._on_status_notification)
        QtCore.QTimer.singleShot(0, lambda: self.apply_floating_toolbar_settings(load_floating_toolbar_settings()))

        # ── Barra Secundária Contextual de Ferramentas ───────────────────────
        self.secondary_toolbar = SecondaryToolBar(parent=self)
        self.secondary_toolbar.settingsChanged.connect(self._on_tool_settings_changed)

        # ── Conexão do Sinal de Cor Capturada do Canvas (Conta-Gotas) ────────
        if hasattr(self.canvas_widget, "colorPicked"):
            self.canvas_widget.colorPicked.connect(self._on_canvas_color_picked)

        # ── Stroke Lock: suspende gavetas e pílulas durante pintura ────────
        if hasattr(self.canvas_widget, "strokeStarted"):
            self.canvas_widget.strokeStarted.connect(lambda: self.left_dock.set_painting_state(True))
            self.canvas_widget.strokeStarted.connect(lambda: self.right_dock.set_painting_state(True))
            self.canvas_widget.strokeStarted.connect(self._close_unpinned_drawers)
        if hasattr(self.canvas_widget, "strokeFinished"):
            self.canvas_widget.strokeFinished.connect(lambda: self.left_dock.set_painting_state(False))
            self.canvas_widget.strokeFinished.connect(lambda: self.right_dock.set_painting_state(False))
            self.canvas_widget.strokeFinished.connect(self._on_stroke_finished_sync_previews)

        # ── Filtro de clique no canvas para fechar gavetas despinadas ───────
        self.canvas_widget.installEventFilter(self)

        self.left_dock.drawer_opened.connect(self._on_dock_state_changed)
        self.left_dock.drawer_closed.connect(self._on_dock_state_changed)
        self.left_dock.pin_toggled.connect(self._on_dock_state_changed)

        self.right_dock.drawer_opened.connect(self._on_dock_state_changed)
        self.right_dock.drawer_closed.connect(self._on_dock_state_changed)
        self.right_dock.pin_toggled.connect(self._on_dock_state_changed)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Filtro de eventos nativo no canvas para fechar gavetas flutuantes com 100% de confiabilidade."""
        if watched is self.canvas_widget and event.type() == QtCore.QEvent.MouseButtonPress:
            has_left_unpinned = self.left_dock.is_open and not self.left_dock.is_pinned
            has_right_unpinned = self.right_dock.is_open and not self.right_dock.is_pinned
            if has_left_unpinned or has_right_unpinned:
                self._close_unpinned_drawers()
                return True  # Intercepta o clique para não iniciar traço acidental no mesmo clique de fechar
        return super().eventFilter(watched, event)

    def _close_unpinned_drawers(self) -> None:
        """Fecha imediatamente todas as gavetas flutuantes não-pinadas."""
        if self.left_dock.is_open and not self.left_dock.is_pinned:
            self.left_dock.close_drawer()
        if self.right_dock.is_open and not self.right_dock.is_pinned:
            self.right_dock.close_drawer()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "left_dock"):
            self.left_dock.update_unpinned_position()
        if hasattr(self, "right_dock"):
            self.right_dock.update_unpinned_position()
        self._update_pill_positions()
        self.update_toolbar_position()

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        QtCore.QTimer.singleShot(50, self.update_toolbar_position)

    def retranslate_ui(self) -> None:
        """Propaga a re-tradução aos subsistemas do workspace."""
        if hasattr(self, "left_dock") and self.left_dock:
            self.left_dock.retranslate_ui()
        if hasattr(self, "right_dock") and self.right_dock:
            self.right_dock.retranslate_ui()
        if hasattr(self, "floating_toolbar") and self.floating_toolbar:
            self.floating_toolbar.retranslate_ui()

    # ── Engine ────────────────────────────────────────────────────────────

    def initialize_engine(self) -> None:
        """
        Inicializa o backend de motor ativo (EngineRegistry). Deve ser chamado
        após o widget ser adicionado à hierarquia de janelas (setCentralWidget),
        pois motores como o WGPU precisam do HWND nativo para criar a swapchain.

        Sem backend registrado (ou com falha de inicialização), a casca segue
        em modo canvas vazio — nunca derruba a aplicação.
        """
        try:
            self.canvas_widget.init_engine(self.canvas_w, self.canvas_h)
        except BaseException as e:  # noqa: BLE001 — PanicException (PyO3) não herda de Exception
            logger.error(f"[WorkspaceContainer] Falha ao inicializar motor: {type(e).__name__}: {e}")


    # ── API pública de painéis (stub — implementação completa na Fase 4) ──

    def add_panel(
        self,
        panel_id:  str,
        title:     str,
        widget:    QtWidgets.QWidget,
        area:      str = "right",
        icon_path: str | None = None,
    ) -> None:
        """
        Registra e monta um painel na doca dinâmica especificada (left ou right).
        Delegado ao AdvancedDockSystem da doca correspondente.
        """
        # Wiring automático baseado nas capacidades do widget
        if hasattr(widget, "preset_combo") or hasattr(widget, "size_slider") or widget.__class__.__name__ in ("BrushDock", "BrushSettingsPanel"):
            if self._brush_dock is None:
                self.connect_brush_dock(widget)
        elif hasattr(widget, "layers") and hasattr(widget, "navigator"):
            if self._properties_dock is None:
                self.connect_properties_dock(widget)
        elif hasattr(widget, "camera_changed_by_user"):
            self._navigator_panel = widget
            widget.camera_changed_by_user.connect(self._set_camera_from_navigator)
            if hasattr(widget, "request_global_fit_view"):
                widget.request_global_fit_view.connect(self.reset_view)
            self.canvas_widget.cameraChanged.connect(self._on_canvas_camera_changed)
            if self.active_document:
                widget.set_has_document(True)
                self._sync_navigator_to_canvas()
        elif hasattr(widget, "set_layer_manager"):
            self._layers_panel = widget
            if self.active_document:
                widget.set_layer_manager(self.active_document.layer_manager)
        elif hasattr(widget, "color_wheel") or hasattr(widget, "set_color"):
            self._color_panel = widget
            if hasattr(widget, "colorChanged"):
                widget.colorChanged.connect(self._on_brush_color)
            if self.active_document and hasattr(widget, "set_color"):
                widget.set_color(getattr(self, "_saved_color", QtGui.QColor(0, 0, 0)))

        dock_system = self.left_dock if area == "left" else self.right_dock
        dock_system.add_panel(panel_id, title, widget, icon_path)


    def remove_panel(self, panel_id: str) -> None:
        """Remove o painel registrado de ambas as docas."""
        self.left_dock.remove_panel(panel_id)
        self.right_dock.remove_panel(panel_id)


    # ── Propriedades de acesso público ────────────────────────────────────

    @property
    def active_document(self):
        """Referência ao documento ativo do DocumentManager."""
        if hasattr(self, "_dm") and self._dm:
            return self._dm.active_document() if callable(self._dm.active_document) else self._dm.active_document
        return None


    @property
    def canvas(self) -> CanvasWidget:

        """Referência read-only ao CanvasWidget ativo."""
        return self.canvas_widget

    @property
    def saved_color(self) -> QtGui.QColor:
        return self._saved_color

    @property
    def current_tool(self) -> str:
        return self._current_tool

    # ── Operações de Desfazer / Refazer ──────────────────────────────────────

    def undo(self) -> None:
        """Executa a operação de desfazer."""
        cw = self.canvas_widget
        if hasattr(cw, "_flood_layers") and cw._flood_layers:
            layer = cw._flood_layers.pop()
            cw._flood_redo_stack.append(layer)
            cw.update()
            self._on_status_notification("Preenchimento desfeito.")
            self._on_stroke_finished_sync_previews()
            return

        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "undo"):
            ok = backend.undo()
            if ok:
                cw.update()
                self._on_status_notification("Desfazer executado com sucesso.")
                self._on_stroke_finished_sync_previews()
            else:
                self._on_status_notification("Nada a desfazer.")

    def redo(self) -> None:
        """Executa a operação de refazer."""
        cw = self.canvas_widget
        if hasattr(cw, "_flood_redo_stack") and cw._flood_redo_stack:
            layer = cw._flood_redo_stack.pop()
            cw._flood_layers.append(layer)
            cw.update()
            self._on_status_notification("Preenchimento refeito.")
            self._on_stroke_finished_sync_previews()
            return

        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "redo"):
            ok = backend.redo()
            if ok:
                cw.update()
                self._on_status_notification("Refazer executado com sucesso.")
                self._on_stroke_finished_sync_previews()
            else:
                self._on_status_notification("Nada a refazer.")

    # ── Handlers de câmera ────────────────────────────────────────────────

    def reset_view(self) -> None:
        """Reposiciona o canvas para o centro e zoom 1:1."""
        if not self._dm.active_document():
            return
        self.canvas_widget.center_canvas()
        self.zoomChanged.emit(self.canvas_widget.zoom)
        self.canvas_widget.update()
        self._sync_navigator_to_canvas()

    def zoom_in(self) -> None:
        cw = self.canvas_widget
        cw.zoom = min(50.0, cw.zoom * 1.2)
        if cw.input_adapter:
            rot_rad = math.radians(getattr(cw, "rotation", 0.0))
            cw.input_adapter.update_view(cw.zoom, cw.pan_x, cw.pan_y, rot_rad)
        self.zoomChanged.emit(cw.zoom)
        cw.update()

    def zoom_out(self) -> None:
        cw = self.canvas_widget
        cw.zoom = max(0.05, cw.zoom / 1.2)
        if cw.input_adapter:
            rot_rad = math.radians(getattr(cw, "rotation", 0.0))
            cw.input_adapter.update_view(cw.zoom, cw.pan_x, cw.pan_y, rot_rad)
        self.zoomChanged.emit(cw.zoom)
        cw.update()

    def clear_canvas(self) -> None:
        """Limpa o canvas (usado pelo MenuBar e ToolSidebar)."""
        if hasattr(self, "canvas_widget") and self.canvas_widget:
            self.canvas_widget.clear_canvas()
        elif self.canvas_widget.renderer:
            self.canvas_widget.renderer.clear_canvas()
            self.canvas_widget.update()

    def clear_selection(self) -> None:
        """Desmarca/limpa a seleção ativa do documento."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "clear_selection"):
            backend.clear_selection()
        if hasattr(self.canvas_widget, "_selection_timer"):
            self.canvas_widget._selection_timer.stop()
        self.canvas_widget.update()
        self._on_status_notification("Seleção cancelada.")

