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
from typing import TYPE_CHECKING

from PySide6 import QtCore, QtGui, QtWidgets

from .canvas.render_widget import CanvasWidget

class WorkspaceContainer(QtWidgets.QWidget):
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
        self.left_dock.drawer_container.header.pin_toggled.connect(self._on_dock_state_changed)

        self.right_dock.drawer_opened.connect(self._on_dock_state_changed)
        self.right_dock.drawer_closed.connect(self._on_dock_state_changed)
        self.right_dock.drawer_container.header.pin_toggled.connect(self._on_dock_state_changed)

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

    def _on_dock_state_changed(self, *args) -> None:
        """Atualiza o posicionamento e a elevação das gavetas despinadas (flutuantes)."""
        if hasattr(self, "left_dock"):
            self.left_dock.update_unpinned_position()
        if hasattr(self, "right_dock"):
            self.right_dock.update_unpinned_position()
        self._update_pill_positions()
        self.update_toolbar_position()

    def _update_pill_positions(self) -> None:
        """Atualiza a posição das PillHandles estritamente nas faixas das sidebars (54px nas extremidades)."""
        if not hasattr(self, "_pill_left"):
            return

        wa_w = self.workspace_area.width()

        if hasattr(self, "left_dock"):
            self._pill_left.update_position(sidebar_slot_x=0, sidebar_slot_w=54)

        if hasattr(self, "right_dock"):
            right_slot_x = max(0, wa_w - 54)
            self._pill_right.update_position(sidebar_slot_x=right_slot_x, sidebar_slot_w=54)

    # ── Barra Flutuante (FloatingToolbar) ────────────────────────────────

    def _get_left_dock_visual_width(self) -> int:
        if not hasattr(self, "left_dock"):
            return 0
        if self.left_dock.is_pinned:
            return self.left_dock.width()
        else:
            w = self.left_dock.sidebar.width() if self.left_dock.sidebar.isVisible() else 0
            if self.left_dock.is_open and self.left_dock.drawer_container.isVisible():
                w += self.left_dock.drawer_container.width()
            return w

    def _get_right_dock_visual_width(self) -> int:
        if not hasattr(self, "right_dock"):
            return 0
        if self.right_dock.is_pinned:
            return self.right_dock.width()
        else:
            w = self.right_dock.sidebar.width() if self.right_dock.sidebar.isVisible() else 0
            if self.right_dock.is_open and self.right_dock.drawer_container.isVisible():
                w += self.right_dock.drawer_container.width()
            return w

    def update_toolbar_position(self) -> None:
        """Atualiza a posição da FloatingToolbar nativa de topo de acordo com o estado magnético."""
        if not hasattr(self, "floating_toolbar") or not self.floating_toolbar.isVisible():
            return

        state = self.floating_toolbar.dock_state
        if not state:
            return

        if state in ("snapped_left", "snapped_right"):
            self.floating_toolbar.set_orientation(QtCore.Qt.Vertical)
        else:
            self.floating_toolbar.set_orientation(QtCore.Qt.Horizontal)

        wa_global = self.workspace_area.mapToGlobal(QtCore.QPoint(0, 0))
        wa_w = self.workspace_area.width()
        wa_h = self.workspace_area.height()

        tb_w = self.floating_toolbar.width()
        tb_h = self.floating_toolbar.height()

        margin_x, margin_y = 16, 12

        if state == "snapped_bottom":
            gx = wa_global.x() + (wa_w - tb_w) // 2
            gy = wa_global.y() + wa_h - tb_h - margin_y
        elif state == "snapped_top":
            gx = wa_global.x() + (wa_w - tb_w) // 2
            gy = wa_global.y() + margin_y
        elif state == "snapped_left":
            left_w = self._get_left_dock_visual_width()
            gx = wa_global.x() + left_w + margin_x
            gy = wa_global.y() + (wa_h - tb_h) // 2
        elif state == "snapped_right":
            right_w = self._get_right_dock_visual_width()
            gx = wa_global.x() + wa_w - right_w - tb_w - margin_x
            gy = wa_global.y() + (wa_h - tb_h) // 2
        else:
            return

        self.floating_toolbar.move(gx, gy)
        self.floating_toolbar.raise_()

        # Posiciona a barra de opções secundária se estiver visível
        if hasattr(self, "secondary_toolbar") and self.secondary_toolbar.isVisible():
            sec_w = self.secondary_toolbar.width()
            sec_h = self.secondary_toolbar.height()
            if state in ("snapped_bottom", "free"):
                sec_gx = gx + (tb_w - sec_w) // 2
                sec_gy = gy - sec_h - 4
            elif state == "snapped_top":
                sec_gx = gx + (tb_w - sec_w) // 2
                sec_gy = gy + tb_h + 4
            elif state == "snapped_left":
                sec_gx = gx + tb_w + 4
                sec_gy = gy + (tb_h - sec_h) // 2
            elif state == "snapped_right":
                sec_gx = gx - sec_w - 4
                sec_gy = gy + (tb_h - sec_h) // 2
            else:
                sec_gx = gx
                sec_gy = gy - sec_h - 4
            self.secondary_toolbar.move(sec_gx, sec_gy)
            self.secondary_toolbar.raise_()

    def _on_floating_toolbar_dropped(self, global_pos: QtCore.QPoint) -> None:
        """Calcula o encaixe magnético (threshold 50px) ao soltar a barra flutuante."""
        if not hasattr(self, "floating_toolbar"):
            return

        threshold = 50
        wa_local = self.workspace_area.mapFromGlobal(global_pos)
        wa_w = self.workspace_area.width()
        wa_h = self.workspace_area.height()
        tb_w = self.floating_toolbar.width()
        tb_h = self.floating_toolbar.height()

        left_x = self._get_left_dock_visual_width()
        if abs(wa_local.x() - left_x) < threshold:
            self.floating_toolbar.dock_state = "snapped_left"
            self.update_toolbar_position()
            return

        right_w = self._get_right_dock_visual_width()
        right_edge_x = wa_w - right_w
        tb_right_x = wa_local.x() + tb_w
        if abs(tb_right_x - right_edge_x) < threshold:
            self.floating_toolbar.dock_state = "snapped_right"
            self.update_toolbar_position()
            return

        if wa_local.y() < threshold:
            self.floating_toolbar.dock_state = "snapped_top"
            self.update_toolbar_position()
            return

        tb_bottom_y = wa_local.y() + tb_h
        if abs(wa_h - tb_bottom_y) < threshold:
            self.floating_toolbar.dock_state = "snapped_bottom"
            self.update_toolbar_position()
            return

        self.floating_toolbar.dock_state = None
        self.update_toolbar_position()

    def apply_floating_toolbar_settings(self, cfg: dict) -> None:
        """Aplica configurações salvas à FloatingToolbar."""
        if not hasattr(self, "floating_toolbar"):
            return

        self.floating_toolbar.auto_collapse_speed = cfg.get("speed", "Rápido")
        self.floating_toolbar.visible_tool_ids = cfg.get("tools", [])
        self.floating_toolbar.rebuild_tools()

        if cfg.get("active", True):
            self.floating_toolbar.show()
            self.floating_toolbar.raise_()
            QtCore.QTimer.singleShot(30, self.update_toolbar_position)
        else:
            self.floating_toolbar.hide()

    def _on_status_notification(self, message: str) -> None:
        win = self.window()
        if hasattr(win, "statusBar") and win.statusBar():
            win.statusBar().showMessage(message, 3500)



    # ── API de controle de docas (Menu Janela) ────────────────────────────

    def apply_dock_settings(self, cfg: dict) -> None:
        """Aplica configurações de auto-recolhimento a ambas as docas."""
        kw = dict(
            auto_collapse=cfg.get("auto_collapse", False),
            speed=cfg.get("speed", "Rápido"),
            delay=cfg.get("hover_delay", "Normal (350ms)"),
        )
        if hasattr(self, "left_dock"):
            self.left_dock.apply_settings(**kw)
        if hasattr(self, "right_dock"):
            self.right_dock.apply_settings(**kw)

    def toggle_panel_from_menu(self, panel_id: str, side: str) -> None:
        """Alterna um painel específico via Menu Janela."""
        dock = self.left_dock if side == "left" else self.right_dock
        dock.toggle_panel(panel_id)

    def collapse_all_sidebars(self) -> None:
        """Recolhe ambas as sidebars via animação."""
        if hasattr(self, "left_dock"):
            self.left_dock._do_collapse()
        if hasattr(self, "right_dock"):
            self.right_dock._do_collapse()

    def expand_all_sidebars(self) -> None:
        """Expande ambas as sidebars via animação."""
        if hasattr(self, "left_dock"):
            self.left_dock._do_expand()
        if hasattr(self, "right_dock"):
            self.right_dock._do_expand()










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


    # ── Conexão de painéis externos ───────────────────────────────────────

    def connect_brush_dock(self, dock: Any) -> None:
        """
        Conecta os sinais do BrushSettingsPanel ao renderer do canvas.
        Deve ser chamado pelo plugin de UI após add_panel().
        """
        self._brush_dock = dock

        if hasattr(dock, "colorChanged"):
            dock.colorChanged.connect(self._on_brush_color)
        if hasattr(dock, "sizeChanged"):
            dock.sizeChanged.connect(self._on_brush_size)
        if hasattr(dock, "opacityChanged"):
            dock.opacityChanged.connect(self._on_brush_opacity)
        if hasattr(dock, "pressureChanged"):
            dock.pressureChanged.connect(self._on_brush_pressure)
        if hasattr(dock, "pressureCurvePowerChanged"):
            dock.pressureCurvePowerChanged.connect(self._on_brush_pressure_curve)
        if hasattr(dock, "stabilizerWeightChanged"):
            dock.stabilizerWeightChanged.connect(self._on_brush_stabilizer)
        if hasattr(dock, "spacingChanged"):
            dock.spacingChanged.connect(self._on_brush_spacing)
        if hasattr(dock, "minDensityActiveChanged"):
            dock.minDensityActiveChanged.connect(self._on_min_density_active)
        if hasattr(dock, "minDensityValueChanged"):
            dock.minDensityValueChanged.connect(self._on_min_density_value)
        if hasattr(dock, "contrastChanged"):
            dock.contrastChanged.connect(self._on_brush_contrast)
        if hasattr(dock, "invertHeightChanged"):
            dock.invertHeightChanged.connect(self._on_brush_invert)
        if hasattr(dock, "loadShapeRequested"):
            dock.loadShapeRequested.connect(lambda: self._load_custom_texture(is_shape=True))
        if hasattr(dock, "loadHeightmapRequested"):
            dock.loadHeightmapRequested.connect(lambda: self._load_custom_texture(is_shape=False))

        # Sincroniza ativação de ferramentas do painel de forma única sem emitir RuntimeWarning
        if hasattr(dock, "toolActivated"):
            dock.toolActivated.connect(self.select_tool, QtCore.Qt.UniqueConnection)


    def connect_properties_dock(self, dock: "PropertiesDock") -> None:
        """
        Conecta os sinais do navigator (PropertiesDock) à câmera do canvas.
        Deve ser chamado pelo plugin de UI após add_panel().
        """
        self._properties_dock = dock

        dock.navigator.camera_changed_by_user.connect(self._set_camera_from_navigator)
        dock.navigator.request_global_fit_view.connect(self.reset_view)

        # Câmera canvas → navigator (bidirecional)
        self.canvas_widget.cameraChanged.connect(self._on_canvas_camera_changed)

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

    # ── Sincronização inicial ─────────────────────────────────────────────

    def sync_all_properties(self) -> None:
        """
        Sincroniza todos os parâmetros de pincel do BrushDock para o renderer.
        Deve ser chamado após connect_brush_dock() e initialize_engine().
        """
        if not self._brush_dock:
            return
        s = self._brush_dock
        self._apply_brush_color(self._saved_color)
        s.color_wheel.set_color(self._saved_color)

        self._on_brush_size(s.slider_size.value())
        self._on_brush_pressure(s.slider_pressure.value())
        self._on_brush_pressure_curve(s.slider_curve.value())
        self._on_brush_stabilizer(s.slider_stabilizer.value() / 100.0)
        self._on_brush_spacing(s.slider_spacing.value() / 100.0)
        self._on_brush_opacity(s.slider_opacity.value() / 100.0)
        self._on_min_density_active(s.chk_min_density.isChecked())
        self._on_min_density_value(s.slider_min_density.value() / 100.0)
        self._on_brush_contrast(s.slider_contrast.value())
        self._on_brush_invert(s.chk_invert.isChecked())

        self.canvas_widget.manual_pressure = s.slider_pressure.value()

    # ── Operações de Desfazer / Refazer ──────────────────────────────────────

    def undo(self) -> None:
        """Executa a operação de desfazer no backend nativo."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "undo"):
            ok = backend.undo()
            if ok:
                self.canvas_widget.update()
                self._on_status_notification("Desfazer executado com sucesso.")
            else:
                self._on_status_notification("Nada a desfazer.")

    def redo(self) -> None:
        """Executa a operação de refazer no backend nativo."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "redo"):
            ok = backend.redo()
            if ok:
                self.canvas_widget.update()
                self._on_status_notification("Refazer executado com sucesso.")
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
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.clear_canvas()
            self.canvas_widget.update()

    def select_tool(self, tool: str) -> None:
        """
        Alterna entre as ferramentas ativas (brush, eraser, eyedrop, etc.).
        Sincroniza bidirecionalmente a FloatingToolbar, o BrushDock e a ToolSidebar.
        """
        if getattr(self, "_is_selecting_tool", False):
            return

        self._is_selecting_tool = True
        try:
            from .floating_toolbar import TOOL_META

            self._current_tool = tool
            if hasattr(self, "canvas_widget"):
                self.canvas_widget.active_tool = tool
                if tool == "eyedrop":
                    self.canvas_widget.setCursor(QtCore.Qt.CrossCursor)
                else:
                    self.canvas_widget.unsetCursor()

            if tool == "brush":
                self._apply_brush_color(self._saved_color)
            elif tool == "eraser":
                self._apply_brush_color(QtGui.QColor("#ffffff"))

            if hasattr(self, "_brush_dock") and self._brush_dock:
                self._brush_dock.set_tool_active(tool)

            if hasattr(self, "floating_toolbar") and self.floating_toolbar:
                self.floating_toolbar.select_tool(tool, notify=False, animate=False)

            if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
                self.secondary_toolbar.set_tool(tool)
                self.update_toolbar_position()

            win = self.window()
            if hasattr(win, "tool_sidebar") and win.tool_sidebar:
                if tool == "brush":
                    win.tool_sidebar.action_brush.setChecked(True)
                    win.tool_sidebar.action_eraser.setChecked(False)
                elif tool == "eraser":
                    win.tool_sidebar.action_brush.setChecked(False)
                    win.tool_sidebar.action_eraser.setChecked(True)

            meta = TOOL_META.get(tool, {"name": tool.capitalize(), "implemented": False})
            if not meta.get("implemented", False):
                self._on_status_notification(f"Ferramenta '{meta['name']}' em desenvolvimento.")
            else:
                self._on_status_notification(f"Ferramenta ativa: {meta['name']}")
        finally:
            self._is_selecting_tool = False

    def _on_canvas_color_picked(self, color: QtGui.QColor) -> None:
        """Chamado quando o conta-gotas captura uma cor do canvas."""
        self._saved_color = color
        self._apply_brush_color(color)
        if hasattr(self, "_brush_dock") and self._brush_dock:
            self._brush_dock.set_color(color)
        if hasattr(self, "_color_panel") and self._color_panel and hasattr(self._color_panel, "set_color"):
            self._color_panel.set_color(color)
        if hasattr(self, "secondary_toolbar") and self.secondary_toolbar:
            self.secondary_toolbar.set_captured_color(color)

    def _on_tool_settings_changed(self, tool_id: str, settings: dict) -> None:
        """Chamado quando as configurações de uma ferramenta mudam na SecondaryToolBar ou no Dock."""
        if tool_id == "eyedrop":
            self.canvas_widget._eyedrop_settings.update(settings)

    def _sync_navigator_to_canvas(self) -> None:
        """Lê o estado atual da câmera do canvas e empurra para o navigator."""
        cw = self.canvas_widget
        self._on_canvas_camera_changed(
            cw.zoom, cw.pan_x, cw.pan_y, cw.rotation,
            float(max(1, cw.width())), float(max(1, cw.height()))
        )

    def _set_camera_from_navigator(
        self, zoom: float, norm_x: float, norm_y: float, rotation: float
    ) -> None:
        """Recebe coordenadas normalizadas do navigator e aplica ao canvas."""
        cw = self.canvas_widget
        cw.zoom     = zoom
        cw.pan_x    = (0.5 - norm_x) * zoom * self.canvas_w
        cw.pan_y    = (0.5 - norm_y) * zoom * self.canvas_h
        cw.rotation = rotation

        if cw.input_adapter:
            rot_rad = math.radians(rotation)
            cw.input_adapter.update_view(cw.zoom, cw.pan_x, cw.pan_y, rot_rad)

        self.zoomChanged.emit(cw.zoom)
        cw.update()

    def _on_canvas_camera_changed(
        self,
        zoom: float, pan_x: float, pan_y: float, rotation: float,
        view_w: float, view_h: float,
    ) -> None:
        """Mapeia parâmetros de câmera para coordenadas normalizadas do navigator."""
        norm_x  = 0.5 - pan_x / (zoom * self.canvas_w)
        norm_y  = 0.5 - pan_y / (zoom * self.canvas_h)
        ratio_w = view_w / (zoom * self.canvas_w)
        ratio_h = view_h / (zoom * self.canvas_h)

        if self._properties_dock:
            self._properties_dock.navigator.update_viewport(
                zoom, norm_x, norm_y, rotation, False, False, ratio_w, ratio_h
            )
        if hasattr(self, "_navigator_panel") and self._navigator_panel:
            self._navigator_panel.update_viewport(
                zoom, norm_x, norm_y, rotation, False, False, ratio_w, ratio_h
            )

    # ── Handlers de documento ─────────────────────────────────────────────

    def _on_active_document_changed(self, doc) -> None:
        """
        Chamado pelo DocumentManager quando o documento ativo muda.
        Salva câmera do doc anterior; restaura câmera e cor do novo doc.
        """
        # Salva câmera e cor do documento anterior
        if self._last_active_doc_uid:
            last_doc = self._dm.get_document(self._last_active_doc_uid)
            if last_doc:
                last_doc.zoom        = self.canvas_widget.zoom
                last_doc.pan_x       = self.canvas_widget.pan_x
                last_doc.pan_y       = self.canvas_widget.pan_y
                last_doc.rotation    = self.canvas_widget.rotation
                last_doc.saved_color = self._saved_color

        self._last_active_doc_uid = doc.uid if doc else None

        if not doc:
            # Nenhum documento ativo — desabilita canvas
            self.canvas_widget.setEnabled(False)
            if self._properties_dock:
                self._properties_dock.layers.set_layer_manager(None)
                self._properties_dock.navigator.set_has_document(False)
            if hasattr(self, "_layers_panel") and self._layers_panel:
                self._layers_panel.set_layer_manager(None)
            if hasattr(self, "_navigator_panel") and self._navigator_panel:
                self._navigator_panel.set_has_document(False)
            if self.canvas_widget.renderer:
                self.canvas_widget.renderer.clear_canvas()
            self.canvas_widget.update()
            return

        self.canvas_widget.setEnabled(True)
        self.canvas_widget.canvas_w = doc.width
        self.canvas_widget.canvas_h = doc.height

        # Sincroniza aba ativa na TabBar
        self.viewport_container.sync_active_tab(doc.uid)

        # Restaura câmera ou centraliza se for novo
        if doc.zoom == 1.0 and doc.pan_x == 0.0 and doc.pan_y == 0.0:
            self.canvas_widget.center_canvas()
        else:
            self.canvas_widget.zoom     = doc.zoom
            self.canvas_widget.pan_x    = doc.pan_x
            self.canvas_widget.pan_y    = doc.pan_y
            self.canvas_widget.rotation = doc.rotation

        # Restaura e aplica cor ativa ao motor nativo
        color = doc.saved_color if doc.saved_color else self._saved_color
        self._saved_color = color
        self._apply_brush_color(color)
        if hasattr(self, "_color_panel") and self._color_panel and hasattr(self._color_panel, "set_color"):
            self._color_panel.set_color(color)
        elif self._brush_dock and hasattr(self._brush_dock, "set_color"):
            self._brush_dock.set_color(color)
        elif self._brush_dock and hasattr(self._brush_dock, "color_wheel"):
            self._brush_dock.color_wheel.set_color(color)

        # Comunica câmera ao motor físico
        if self.canvas_widget.input_adapter:
            rot_rad = math.radians(doc.rotation)
            self.canvas_widget.input_adapter.update_view(
                doc.zoom, doc.pan_x, doc.pan_y, rot_rad
            )
        self.canvas_widget.update()

        # Sincroniza zoom e navigator
        self.zoomChanged.emit(doc.zoom)
        self._sync_navigator_to_canvas()

        # Sincroniza painel de camadas
        if self._properties_dock:
            self._properties_dock.layers.set_layer_manager(doc.layer_manager)
            self._properties_dock.navigator.set_has_document(True)
        if hasattr(self, "_layers_panel") and self._layers_panel:
            self._layers_panel.set_layer_manager(doc.layer_manager)
            if hasattr(self._layers_panel, "paper_widget"):
                pw = self._layers_panel.paper_widget
                p_col = getattr(doc, "paper_color", QtGui.QColor(255, 255, 255, 255))
                p_vis = getattr(doc, "paper_visible", True)
                p_tex = getattr(doc, "paper_texture_id", 0)
                p_ena = getattr(doc, "paper_texture_enabled", False)
                pw.set_paper_state(color=p_col, visible=p_vis, preset_id=p_tex, enabled=p_ena)
        if hasattr(self, "_navigator_panel") and self._navigator_panel:
            self._navigator_panel.set_has_document(True)

        # Garante Pincel Redondo (Pincel Básico, 24px, #000000) por padrão no motor e na UI ao abrir documento
        active_color = getattr(self, "_saved_color", QtGui.QColor(0, 0, 0))
        self._apply_brush_color(active_color)
        if hasattr(self, "_brush_dock") and self._brush_dock and hasattr(self._brush_dock, "preset_combo"):
            preset_data = {
                "label": "Pincel Redondo",
                "engine_type": 0,
                "brush_size": 24.0,
                "opacity": 1.0,
                "hardness": 0.85,
                "spacing_factor": 0.12
            }
            self._brush_dock.preset_combo._on_preset_selected("Pincel Redondo", preset_data)


    # ── Handlers de ferramentas ───────────────────────────────────────────

    def _on_dock_tool_activated(self, tool_id: str) -> None:
        """Recebe seleção de ferramenta vinda do BrushDock."""
        self.select_tool(tool_id)

    def _apply_brush_color(self, color: QtGui.QColor) -> None:
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.set_brush_color(color.redF(), color.greenF(), color.blueF())
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_brush_color(
                color.redF(), color.greenF(), color.blueF()
            )
        self.canvas_widget.update()

    # ── Handlers de brush ─────────────────────────────────────────────────

    def _on_brush_color(self, color: QtGui.QColor) -> None:
        self._saved_color = color
        if self._current_tool == "brush":
            self._apply_brush_color(color)
        if self._brush_dock and hasattr(self._brush_dock, "stroke_preview"):
            size_val = self._brush_dock.qs_size.value() if hasattr(self._brush_dock, "qs_size") else 60
            opac_val = (self._brush_dock.qs_opacity.value() / 100.0) if hasattr(self._brush_dock, "qs_opacity") else 1.0
            self._brush_dock.stroke_preview.update_brush_state(
                size=size_val,
                opacity=opac_val,
                color=[color.redF(), color.greenF(), color.blueF()],
            )

    def _on_brush_size(self, val: float) -> None:
        cw = self.canvas_widget
        cw.brush_size = val
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.set_brush_size(val)
        if cw.renderer:
            cw.renderer.set_brush_size(val)
        cw.update()
        if self._brush_dock:
            d = self._brush_dock
            if hasattr(d, "qs_size"):
                d.qs_size.blockSignals(True)
                d.qs_size.setValue(int(val))
                d.qs_size.blockSignals(False)
            # Sincroniza slider do AdvancedPanel se estiver aberto
            if hasattr(d, "_adv_panel") and d._adv_panel and hasattr(d._adv_panel, "slider_size"):
                d._adv_panel.slider_size.blockSignals(True)
                d._adv_panel.slider_size.setValue(val)
                d._adv_panel.slider_size.blockSignals(False)
            c = self._saved_color
            if hasattr(d, "stroke_preview"):
                opac_val = (d.qs_opacity.value() / 100.0) if hasattr(d, "qs_opacity") else 1.0
                d.stroke_preview.update_brush_state(
                    size=val,
                    opacity=opac_val,
                    color=[c.redF(), c.greenF(), c.blueF()],
                )


    def _on_brush_pressure(self, val: float) -> None:
        cw = self.canvas_widget
        cw.manual_pressure = val
        if cw.renderer:
            cw.renderer.set_brush_pressure(val)
            cw.update()
        if self._brush_dock:
            self._brush_dock.stroke_preview.update_brush_state(pressure=val)

    def _on_brush_pressure_curve(self, val: float) -> None:
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_pressure_curve_power(val)
            self.canvas_widget.update()

    def _on_brush_stabilizer(self, weight: float) -> None:
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_stabilizer_weight(weight)
            self.canvas_widget.update()

    def _on_brush_spacing(self, factor: float) -> None:
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_brush_spacing(factor)
            self.canvas_widget.update()
        if self._brush_dock:
            self._brush_dock.stroke_preview.update_brush_state(spacing=factor)

    def _on_brush_opacity(self, factor: float) -> None:
        cw = self.canvas_widget
        if cw.renderer:
            cw.renderer.set_brush_opacity(factor)
            cw.update()
        if self._brush_dock:
            d = self._brush_dock
            val = int(factor * 100.0)
            d.qs_opacity.blockSignals(True)
            d.qs_opacity.setValue(val)
            d.qs_opacity.blockSignals(False)
            if d._adv_panel:
                d._adv_panel.slider_opacity.blockSignals(True)
                d._adv_panel.slider_opacity.setValue(val)
                d._adv_panel.slider_opacity.blockSignals(False)
            d.stroke_preview.update_brush_state(opacity=factor)

    def _on_min_density_active(self, active: bool) -> None:
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_min_density_active(active)
            self.canvas_widget.update()

    def _on_min_density_value(self, weight: float) -> None:
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_min_density_value(weight)
            self.canvas_widget.update()

    def _on_brush_contrast(self, val: float) -> None:
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_brush_contrast(val)
            self.canvas_widget.update()
        if self._brush_dock:
            hardness = min(0.99, max(0.01, val / 3.0))
            self._brush_dock.stroke_preview.update_brush_state(hardness=hardness)

    def _on_brush_invert(self, invert: bool) -> None:
        if self.canvas_widget.renderer:
            self.canvas_widget.renderer.set_brush_invert_height(invert)
            self.canvas_widget.update()

    # ── Carregamento de texturas ──────────────────────────────────────────

    def _load_custom_texture(self, is_shape: bool) -> None:
        """Abre diálogo de arquivo e carrega textura de shape ou heightmap."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Selecionar Imagem de Textura",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.tga)",
        )
        if not file_path:
            return

        image = QtGui.QImage(file_path)
        if image.isNull():
            QtWidgets.QMessageBox.warning(
                self, "Erro", "Não foi possível carregar a imagem selecionada."
            )
            return

        image    = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
        width    = image.width()
        height   = image.height()
        ptr      = image.constBits()
        px_bytes = ptr.tobytes()

        renderer = self.canvas_widget.renderer
        if renderer:
            if is_shape:
                renderer.set_shape_texture(px_bytes, width, height)
            else:
                renderer.set_heightmap_texture(px_bytes, width, height)

        if self._brush_dock:
            self._brush_dock.update_thumbnail(is_shape, file_path)

        self.canvas_widget.update()

    def _on_stroke_finished_sync_previews(self) -> None:
        """Sincroniza os previews do Navigator e a miniatura da camada ativa após a conclusão do traço."""
        try:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            facade = getattr(backend, "_facade", None)

            # 1. Atualiza miniatura da camada ativa no painel de camadas
            if hasattr(self, "_layers_panel") and self._layers_panel and hasattr(self._layers_panel, "layer_manager"):
                lm = self._layers_panel.layer_manager
                if lm and lm.get_active_layer() and facade:
                    lm.update_thumbnail(lm.get_active_layer().uid, facade)

            # 2. Atualiza snapshot do Navigator
            if hasattr(self, "_navigator_panel") and self._navigator_panel:
                if hasattr(self.canvas_widget, "get_canvas_image"):
                    canvas_img = self.canvas_widget.get_canvas_image()
                    if canvas_img and not canvas_img.isNull():
                        self._navigator_panel.set_artwork(canvas_img)
                elif backend and hasattr(backend, "get_qimage"):
                    qimg = backend.get_qimage()
                    if qimg and not qimg.isNull():
                        self._navigator_panel.set_artwork(qimg)
        except Exception as e:
            logger.debug(f"[WorkspaceContainer] Erro ao sincronizar previews: {e}")
