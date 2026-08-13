"""
MainWindow — Shell principal do Lumenia Brush Engine 2.0
=========================================================
Responsabilidades desta classe (Fase 3+):
  - Montar componentes nativos da QMainWindow: MenuBar, ToolSidebar,
    BrushDock (QDockWidget), PropertiesDock (QDockWidget), StatusBar
  - Injetar-se no PluginManager ANTES de discover_plugins() para que o
    WorkspaceCore system plugin monte o WorkspaceContainer via setCentralWidget
  - Delegar toda lógica de canvas, brush e câmera ao WorkspaceContainer
  - Abrir diálogos (tema, plugins, novo documento, fechar documento)

O que NÃO pertence aqui:
  - Handlers on_brush_* (em WorkspaceContainer)
  - Câmera / navigator sync (em WorkspaceContainer)
  - _on_active_document_changed (em WorkspaceContainer)
  - Criação direta do WorkspaceContainer (responsabilidade do WorkspaceCore plugin)
"""

import os
from PySide6 import QtWidgets, QtCore, QtGui

from ui.core import ThemeManager
from ui.core.components import MenuBar, ToolSidebar, StatusBar, ThemeDialog


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lumenia Brush Engine 2.0")

        # ── Tema ──────────────────────────────────────────────────────────
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)
        self.setStyleSheet(ThemeManager.instance().get_stylesheet())

        # ── Document Manager ──────────────────────────────────────────────
        from ui.core.document.manager import DocumentManager
        self.dm = DocumentManager.instance()

        # ── Plugin Manager — injeta self ANTES de discover_plugins() ──────
        # O WorkspaceCore system plugin usa context.main_window para chamar
        # self.setCentralWidget(workspace_container) durante seu activate().
        from ui.core.plugins.manager import PluginManager
        self.plugin_manager = PluginManager.instance()
        self.plugin_manager.set_main_window(self)
        self.plugin_manager.discover_plugins()

        # ── Referência ao workspace (preenchida pelo WorkspaceCore plugin) ─
        # O WorkspaceCore chama self.setCentralWidget(container), então após
        # discover_plugins() o centralWidget() já é o WorkspaceContainer.
        self.workspace = self.centralWidget()

        # ── Atalhos de compatibilidade retroativa ─────────────────────────
        if self.workspace is not None:
            self.canvas_widget      = self.workspace.canvas_widget
            self.viewport_container = self.workspace.viewport_container
        else:
            # Fallback: se plugins não carregaram, app mostra tela vazia
            self.canvas_widget      = None
            self.viewport_container = None

        # ── Componentes nativos da QMainWindow ────────────────────────────
        self._setup_components()

        # ── Primeiro show: centraliza canvas após layout realizado ─────────
        self._first_show = True

    # ── Eventos do ciclo de vida ──────────────────────────────────────────


    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QtCore.QTimer.singleShot(0, self.reset_view)

    # ── Setup de componentes da janela ────────────────────────────────────

    def _setup_components(self) -> None:
        """
        Monta os componentes nativos da QMainWindow:
        MenuBar, ToolSidebar, BrushDock, PropertiesDock, StatusBar.
        Todo o wiring brush/câmera é delegado ao WorkspaceContainer.
        Se o workspace não foi montado (WorkspaceCore falhou), apenas
        monta MenuBar e StatusBar para não crashar.
        """
        # ── Menu Bar ──────────────────────────────────────────────────────
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.menu_bar.clearCanvasRequested.connect(self.clear_screen)
        self.menu_bar.resetViewRequested.connect(self.reset_view)
        self.menu_bar.resetRotationRequested.connect(self.reset_rotation)
        self.menu_bar.zoomInRequested.connect(self.zoom_in)
        self.menu_bar.zoomOutRequested.connect(self.zoom_out)
        self.menu_bar.exportImageRequested.connect(self.export_image)
        self.menu_bar.curvesLutRequested.connect(self.open_curve_window)
        self.menu_bar.themeSettingsRequested.connect(self.open_theme_dialog)
        self.menu_bar.managePluginsRequested.connect(self.open_plugins_dialog)
        self.menu_bar.newDocumentRequested.connect(self.open_new_document_dialog)
        self.menu_bar.closeDocumentRequested.connect(self.close_active_document)
        self.menu_bar.dockSettingsRequested.connect(self.open_dock_settings_dialog)

        # ── Tool Sidebar ──────────────────────────────────────────────────
        self.tool_sidebar = ToolSidebar(self)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.tool_sidebar)
        self.tool_sidebar.brushSelected.connect(self.select_brush_tool)
        self.tool_sidebar.eraserSelected.connect(self.select_eraser_tool)
        self.tool_sidebar.zoomInRequested.connect(self.zoom_in)
        self.tool_sidebar.zoomOutRequested.connect(self.zoom_out)
        self.tool_sidebar.resetRequested.connect(self.reset_view)
        self.tool_sidebar.clearRequested.connect(self.clear_screen)

        # ── Status Bar ────────────────────────────────────────────────────
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)

        # ── Wiring: documento ativo → status bar ─────────────────────────
        self.dm.activeDocumentChanged.connect(self._on_active_document_status)

        # ── Componentes que dependem do workspace (WorkspaceCore plugin) ──
        if self.workspace is None:
            return

        # ── Wiring: WorkspaceContainer → StatusBar ────────────────────────
        self.workspace.zoomChanged.connect(self.status_bar.update_zoom)
        self.workspace.newDocumentRequested.connect(self.open_new_document_dialog)
        self.workspace.documentCloseRequested.connect(self.close_document_with_confirmation)

        # Propriedades de compatibilidade para código que acessa main_window.brush_dock
        if hasattr(self.workspace, "_brush_dock") and self.workspace._brush_dock:
            self.brush_dock = self.workspace._brush_dock
            self.brush_dock.toolActivated.connect(self._on_dock_tool_activated)
        if hasattr(self.workspace, "_properties_dock") and self.workspace._properties_dock:
            self.properties_dock = self.workspace._properties_dock

        # ── Menu Janela: conecta sinais de controle de paineis e gavetas ───
        self.menu_bar.togglePanelRequested.connect(
            lambda pid, side: self.workspace.toggle_panel_from_menu(pid, side)
        )
        self.menu_bar.collapseAllSidebarsRequested.connect(self.workspace.collapse_all_sidebars)
        self.menu_bar.expandAllSidebarsRequested.connect(self.workspace.expand_all_sidebars)
        self.menu_bar.dockSettingsRequested.connect(self.open_dock_settings_dialog)
        self.menu_bar.floatingToolbarSettingsRequested.connect(self.open_floating_toolbar_settings_dialog)




    # ── Callbacks de tema ─────────────────────────────────────────────────

    def _on_theme_changed(self, theme_name: str) -> None:
        self.setStyleSheet(ThemeManager.instance().get_stylesheet())

    # ── Callbacks de status (responsabilidade que fica na MainWindow) ──────

    def _on_active_document_status(self, doc) -> None:
        """Atualiza mensagem da StatusBar quando documento ativo muda."""
        if not doc:
            self.status_bar.showMessage("Nenhum documento aberto.")
        else:
            self.status_bar.showMessage(f"Documento ativo: {doc.name}")

    # ── Ferramenta ────────────────────────────────────────────────────────

    def _on_dock_tool_activated(self, tool_id: str) -> None:
        """Sincroniza ToolSidebar quando a ferramenta muda via BrushDock."""
        if tool_id == "brush":
            self.tool_sidebar.action_brush.setChecked(True)
            self.tool_sidebar.action_eraser.setChecked(False)
        elif tool_id == "eraser":
            self.tool_sidebar.action_brush.setChecked(False)
            self.tool_sidebar.action_eraser.setChecked(True)

    def select_brush_tool(self) -> None:

        self.workspace.select_tool("brush")
        self.tool_sidebar.action_brush.setChecked(True)
        self.tool_sidebar.action_eraser.setChecked(False)
        self.status_bar.showMessage("Ferramenta Pincel selecionada.")

    def select_eraser_tool(self) -> None:
        self.workspace.select_tool("eraser")
        self.tool_sidebar.action_brush.setChecked(False)
        self.tool_sidebar.action_eraser.setChecked(True)
        self.status_bar.showMessage("Ferramenta Borracha selecionada.")

    # ── Câmera ────────────────────────────────────────────────────────────

    def reset_view(self) -> None:
        self.workspace.reset_view()
        self.status_bar.showMessage("Visão do canvas resetada.", 2000)

    def zoom_in(self) -> None:
        self.workspace.zoom_in()

    def zoom_out(self) -> None:
        self.workspace.zoom_out()

    # ── Canvas ────────────────────────────────────────────────────────────

    def clear_screen(self) -> None:
        self.workspace.clear_canvas()
        self.status_bar.showMessage("Tela limpa.", 2000)

    # ── Diálogos ─────────────────────────────────────────────────────────

    def open_theme_dialog(self) -> None:
        dialog = ThemeDialog(self)
        dialog.exec()

    def open_plugins_dialog(self) -> None:
        from ui.core.screens import PluginsWindow
        dialog = PluginsWindow(self)
        dialog.exec()

    def open_dock_settings_dialog(self) -> None:
        from ui.core.screens.dock_settings_dialog import DockBarsSettingsDialog
        dialog = DockBarsSettingsDialog(self.workspace, self)
        dialog.settings_applied.connect(
            lambda cfg: self.workspace.apply_dock_settings(cfg)
        )
        dialog.exec()

    def open_floating_toolbar_settings_dialog(self) -> None:
        from ui.core.screens.floating_toolbar_settings_dialog import FloatingToolbarSettingsDialog
        dialog = FloatingToolbarSettingsDialog(self)
        dialog.settings_applied.connect(
            lambda cfg: self.workspace.apply_floating_toolbar_settings(cfg)
        )
        dialog.exec()

    def open_new_document_dialog(self) -> None:
        from ui.core.screens.new_document_dialog import NewDocumentDialog
        dialog = NewDocumentDialog(self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            params = dialog.get_document_params()
            name = params["name"]
            w = params["width"]
            h = params["height"]
            bg_color = params.get("bg_color", (255, 255, 255, 255))
            paper_tex = params.get("paper_texture_id", 0)

            doc = self.dm.new_document(
                width=w,
                height=h,
                name=name,
                bg_color=bg_color,
                paper_texture_id=paper_tex
            )

            # Inicializa a Facade C++ com as novas dimensões e papel do documento
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            if backend:
                backend.init_renderer(0, w, h, w, h)
                if hasattr(backend, "_facade") and backend._facade:
                    backend._facade.clear_canvas()

                    # Aplica a cor inicial do papel selecionada no diálogo
                    r, g, b, a = bg_color
                    if hasattr(backend, "set_background_color"):
                        backend.set_background_color(r, g, b, a)
                    elif hasattr(backend._facade, "set_background_color"):
                        backend._facade.set_background_color(r, g, b, a)

                    # Visibilidade do fundo (falso se for transparente com a == 0)
                    is_vis = (a > 0)
                    if hasattr(backend._facade, "set_background_visibility"):
                        backend._facade.set_background_visibility(is_vis)

                    # Aplica textura se selecionada
                    if paper_tex > 0:
                        backend._facade.set_canvas_height_preset(paper_tex)
                        if hasattr(backend, "set_canvas_grain_enabled"):
                            backend.set_canvas_grain_enabled(True)
                        if hasattr(backend._facade, "get_canvas_texture"):
                            c_tex = backend._facade.get_canvas_texture()
                            if c_tex:
                                c_tex.canvas_grain_enabled = True

                # Mantém e aplica a cor de tinta ativa do usuário
                if self.workspace and hasattr(self.workspace, "_saved_color"):
                    color = self.workspace._saved_color
                    backend.set_brush_color(color.redF(), color.greenF(), color.blueF())

            self.reset_view()

    def close_active_document(self) -> None:
        doc = self.dm.active_document()
        if doc:
            self.close_document_with_confirmation(doc.uid)

    def close_document_with_confirmation(self, uid: str) -> None:
        doc = self.dm.get_document(uid)
        if not doc:
            return
        from ui.core.screens.close_document_dialog import CloseDocumentDialog
        dialog = CloseDocumentDialog(doc.name, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            if dialog.result_code == CloseDocumentDialog.SAVE:
                self.status_bar.showMessage(
                    f"Documento '{doc.name}' salvo com sucesso!", 3000
                )
                self.dm.close_document(uid)
            elif dialog.result_code == CloseDocumentDialog.DISCARD:
                self.dm.close_document(uid)

    # ── Textura (delegado ao WorkspaceContainer, mantido aqui para compatibilidade) ──

    def reset_rotation(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            cw.rotation = 0.0
            cw.update()
            self.status_bar.showMessage("Rotação do canvas resetada para 0°.", 2000)

    def export_image(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Exportar Imagem", "", "Imagem PNG (*.png);;Imagem JPEG (*.jpg *.jpeg)"
        )
        if filename:
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            if backend and hasattr(backend, "get_qimage"):
                qimg = backend.get_qimage()
                if qimg and not qimg.isNull():
                    qimg.save(filename)
                    self.status_bar.showMessage(f"Imagem exportada com sucesso para '{filename}'", 4000)

    def open_curve_window(self) -> None:
        if not hasattr(self, "_curve_win") or self._curve_win is None:
            from ui.core.screens.curve_window import CurveWindow
            self._curve_win = CurveWindow(self)
        self._curve_win.show()
        self._curve_win.raise_()
        self._curve_win.activateWindow()

    def load_custom_texture(self, is_shape: bool) -> None:
        """Delegado ao WorkspaceContainer. Mantido para compatibilidade com chamadas externas."""
        self.workspace._load_custom_texture(is_shape)
        if is_shape:
            kind = "Shape"
        else:
            kind = "Heightmap"
        self.status_bar.showMessage(f"Textura {kind} carregada.", 3000)
