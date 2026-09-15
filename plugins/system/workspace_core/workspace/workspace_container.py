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
from .panel_bindings import WorkspacePanelBindingsMixin
from .workspace_actions import WorkspaceActionsMixin, _history_failure_message

logger = logging.getLogger("Workspace.Container")

class WorkspaceContainer(
    QtWidgets.QWidget,
    WorkspaceLayoutMixin,
    WorkspacePanelBindingsMixin,
    WorkspaceDocSyncMixin,
    WorkspaceBrushMixin,
    WorkspaceActionsMixin,
):
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
        self._navigator_panel = None
        self._layers_panel = None
        self._color_panel = None
        self._initialize_panel_bindings()

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
        if hasattr(self, 'secondary_toolbar') and self.secondary_toolbar:
            self.secondary_toolbar.retranslate_ui()

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
        previous_widget = self._panel_widgets.get(panel_id)
        if previous_widget is widget:
            return
        if previous_widget is not None:
            self.remove_panel(panel_id)
        self._register_panel_widget(panel_id, widget)

        # IDs pertencem ao contrato WorkspaceService; não inferimos mais por
        # atributos ocasionais de widgets de terceiros.
        if panel_id == "brush_settings":
            self.connect_brush_dock(widget, panel_id)
        elif panel_id == "properties":
            self.connect_properties_dock(widget, panel_id)
        elif panel_id == "navigator":
            self._navigator_panel = widget
            self._bind_panel_signal(panel_id, widget.camera_changed_by_user, self._set_camera_from_navigator)
            self._bind_panel_signal(panel_id, widget.request_global_fit_view, self.reset_view)
            self._bind_panel_signal(panel_id, self.canvas_widget.cameraChanged, self._on_canvas_camera_changed)
            if self.active_document:
                widget.set_has_document(True)
                self._sync_navigator_to_canvas()
        elif panel_id == "layers":
            self._layers_panel = widget
            if self.active_document:
                widget.set_layer_manager(self.active_document.layer_manager)
        elif panel_id == "color_wheel":
            self._color_panel = widget
            self._bind_panel_signal(panel_id, widget.colorChanged, self._on_brush_color)
            if self.active_document:
                widget.set_color(getattr(self, "_saved_color", QtGui.QColor(0, 0, 0)))

        dock_system = self.left_dock if area == "left" else self.right_dock
        try:
            dock_system.add_panel(panel_id, title, widget, icon_path)
        except Exception:
            self._release_panel_binding(panel_id)
            raise


    def remove_panel(self, panel_id: str) -> None:
        """Remove o painel registrado de ambas as docas."""
        self._release_panel_binding(panel_id)
        self.left_dock.remove_panel(panel_id)
        self.right_dock.remove_panel(panel_id)

    def _release_panel_binding(self, panel_id: str) -> None:
        """Desconecta slots e elimina referências somente do painel removido."""
        widget = self._panel_widgets.get(panel_id)
        if widget is self._brush_dock:
            self.disconnect_brush_dock(widget, panel_id)
        elif widget is self._properties_dock:
            self.disconnect_properties_dock(widget, panel_id)
        else:
            self._disconnect_panel_signals(panel_id)

        self._take_panel_widget(panel_id)
        if widget is self._layers_panel:
            self._layers_panel = None
        if widget is self._navigator_panel:
            self._navigator_panel = None
        if widget is self._color_panel:
            self._color_panel = None


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

