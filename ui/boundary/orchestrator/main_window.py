"""MainWindow — Shell principal do Lumenia Brush Engine 2.0 (ARCcC Shell Layer)."""

import os
from PySide6 import QtWidgets, QtCore, QtGui

from ui.core import ThemeManager
from ui.core.components import MenuBar, ToolSidebar, StatusBar, ThemeDialog


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lumenia Brush Engine 2.0")

        # ── Ícone Oficial da Aplicação ────────────────────────────────────
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        icon_path = os.path.join(project_root, "assets", "images", "icon_lumenia.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QtGui.QIcon(icon_path))

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
        """
        from .main_window_menu_builder import setup_menu_and_shortcuts
        setup_menu_and_shortcuts(self)

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
        self.select_tool_by_id("brush")

    def select_eraser_tool(self) -> None:
        self.select_tool_by_id("eraser")

    def select_shapes_tool(self) -> None:
        self.select_tool_by_id("shapes")

    def select_text_tool(self) -> None:
        self.select_tool_by_id("text")

    def select_tool_by_id(self, tool_id: str) -> None:
        if self.workspace:
            self.workspace.select_tool(tool_id)
        if hasattr(self, "tool_sidebar"):
            self.tool_sidebar.action_brush.setChecked(tool_id == "brush")
            self.tool_sidebar.action_eraser.setChecked(tool_id == "eraser")
            if hasattr(self.tool_sidebar, "action_shapes"):
                self.tool_sidebar.action_shapes.setChecked(tool_id.startswith("shape") or tool_id == "shapes")
        
        from ui.core.tools import TOOL_META
        tool_name = TOOL_META.get(tool_id, {}).get("name", tool_id.capitalize())
        self.status_bar.showMessage(f"Ferramenta {tool_name} selecionada.")

    # ── Câmera ────────────────────────────────────────────────────────────

    def reset_view(self) -> None:
        self.workspace.reset_view()
        self.status_bar.showMessage("Visão do canvas resetada.", 2000)

    def zoom_in(self) -> None:
        self.workspace.zoom_in()

    def zoom_out(self) -> None:
        self.workspace.zoom_out()

    # ── Desfazer / Refazer ────────────────────────────────────────────────

    def undo(self) -> None:
        if self.workspace:
            self.workspace.undo()

    def redo(self) -> None:
        if self.workspace:
            self.workspace.redo()

    # ── Canvas ────────────────────────────────────────────────────────────

    def clear_screen(self) -> None:
        self.workspace.clear_canvas()
        self.status_bar.showMessage("Tela limpa.", 2000)

    def deselect_selection(self) -> None:
        if self.workspace and hasattr(self.workspace, "clear_selection"):
            self.workspace.clear_selection()
            self.status_bar.showMessage("Seleção desmarcada.", 2000)

    # ── Diálogos ─────────────────────────────────────────────────────────

    def open_theme_dialog(self) -> None:
        dialog = ThemeDialog(self)
        dialog.exec()

    def open_plugins_dialog(self) -> None:
        from ui.core.screens import PluginsWindow
        dialog = PluginsWindow(self)
        dialog.exec()

    def open_render_settings_dialog(self) -> None:
        from ui.core.dialogs.render_settings_dialog import RenderSettingsDialog
        dialog = RenderSettingsDialog(self)
        dialog.profileChanged.connect(self._on_color_profile_changed)
        dialog.exec()

    def _on_color_profile_changed(self, profile_id: int) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            self.workspace.canvas_widget.update()
            if hasattr(self.workspace, "_sync_navigator_to_canvas"):
                self.workspace._sync_navigator_to_canvas()
        prof_name = ""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "get_color_profile_name"):
            prof_name = backend.get_color_profile_name(profile_id)
        self.status_bar.showMessage(f"Modo de Cor ativo: {prof_name}", 3000)

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

    def select_tool_by_id(self, tool_id: str) -> None:
        if self.workspace:
            self.workspace.select_tool(tool_id)

    def open_image_file(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Abrir Imagem", "", "Imagens (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if filename:
            qimg = QtGui.QImage(filename)
            if not qimg.isNull():
                import os
                name = os.path.splitext(os.path.basename(filename))[0]
                w, h = qimg.width(), qimg.height()
                doc = self.dm.new_document(width=w, height=h, name=name)
                self.status_bar.showMessage(f"Imagem '{name}' ({w}x{h}) aberta com sucesso!", 3000)

    def save_active_document(self) -> None:
        doc = self.dm.active_document()
        if doc:
            self.status_bar.showMessage(f"Documento '{doc.name}' salvo.", 2000)
        else:
            self.status_bar.showMessage("Nenhum documento ativo para salvar.", 2000)

    def flip_horizontal(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            if hasattr(cw, "flip_x"):
                cw.flip_x = not getattr(cw, "flip_x", False)
                cw.update()
                self.status_bar.showMessage("Visualização espelhada horizontalmente.", 2000)

    def flip_vertical(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            if hasattr(cw, "flip_y"):
                cw.flip_y = not getattr(cw, "flip_y", False)
                cw.update()
                self.status_bar.showMessage("Visualização espelhada verticalmente.", 2000)

    def create_new_layer(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            idx = doc.layer_manager.add_layer("Nova Camada")
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Nova camada criada.", 2000)

    def create_new_group(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            idx = doc.layer_manager.add_group("Novo Grupo")
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Novo grupo de camadas criado.", 2000)

    def duplicate_active_layer(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx >= 0:
                lm.duplicate_layer(act_idx)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage("Camada duplicada.", 2000)

    def delete_active_layer(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx >= 0:
                lm.remove_layer(act_idx)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage("Camada removida.", 2000)

    def merge_layer_down(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx > 0:
                lm.merge_down(act_idx)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage("Camada mesclada para baixo.", 2000)

    def open_filter_gallery(self) -> None:
        from ui.core.screens.filters.filter_adjustment_dialog import FilterAdjustmentDialog
        dialog = FilterAdjustmentDialog(self)
        dialog.exec()

    def open_shortcuts_dialog(self) -> None:
        QtWidgets.QMessageBox.information(
            self,
            "Atalhos de Teclado",
            "ATALHOS PRINCIPAIS DO LUMENIA:\n\n"
            "• B: Pincel\n"
            "• E: Borracha\n"
            "• G: Balde de Tinta\n"
            "• I / Alt (segurar): Conta-Gotas\n"
            "• W: Varinha Mágica\n"
            "• Ctrl+T: Transformação Livre\n"
            "• Ctrl+Z: Desfazer\n"
            "• Ctrl+Y / Ctrl+Shift+Z: Refazer\n"
            "• Ctrl++ / Ctrl+-: Zoom In / Zoom Out\n"
            "• Ctrl+0: Zoom 100%\n"
            "• Ctrl+R: Resetar Rotação\n"
            "• H: Espelho Horizontal\n"
            "• Ctrl+N: Novo Documento\n"
            "• Ctrl+S / Ctrl+E: Exportar Imagem\n"
            "• Ctrl+Shift+N: Nova Camada\n"
            "• Ctrl+G: Novo Grupo\n"
            "• Ctrl+J: Duplicar Camada\n"
            "• Delete: Limpar Camada"
        )

    def open_feedback_form(self) -> None:
        """Abre o formulário oficial de feedback Enviar_Feedback.html no navegador padrão."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        feedback_path = os.path.join(project_root, "Enviar_Feedback.html")
        if os.path.exists(feedback_path):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(feedback_path))
        else:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl("mailto:lumeniateam@protonmail.com?subject=[Lumenia%20Alpha%20Feedback]"))

    def open_about_dialog(self) -> None:
        from ui.core.screens.about_dialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec()

    def load_custom_texture(self, is_shape: bool) -> None:
        """Delegado ao WorkspaceContainer. Mantido para compatibilidade com chamadas externas."""
        self.workspace._load_custom_texture(is_shape)
        if is_shape:
            kind = "Shape"
        else:
            kind = "Heightmap"
        self.status_bar.showMessage(f"Textura {kind} carregada.", 3000)
