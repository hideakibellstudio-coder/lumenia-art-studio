"""MainWindow — Shell principal do Lumenia Brush Engine 2.0 (ARCcC Shell Layer)."""

import os
from PySide6 import QtWidgets, QtCore, QtGui

from ui.core import ThemeManager
from ui.core.components import MenuBar, ToolSidebar, StatusBar, ThemeDialog
from .main_window_menu_actions import MainWindowMenuActionsMixin


class MainWindow(QtWidgets.QMainWindow, MainWindowMenuActionsMixin):

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

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        super().closeEvent(event)

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

        # ── Internacionalização (i18n) ──────────────────────────────────
        from ui.core.i18n import I18nManager
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Propaga a tradução ativa para todos os subcomponentes da interface."""
        if hasattr(self, "menu_bar") and hasattr(self.menu_bar, "retranslate_ui"):
            self.menu_bar.retranslate_ui()
        if hasattr(self, "tool_sidebar") and hasattr(self.tool_sidebar, "retranslate_ui"):
            self.tool_sidebar.retranslate_ui()
        if hasattr(self, "workspace") and self.workspace and hasattr(self.workspace, "retranslate_ui"):
            self.workspace.retranslate_ui()

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
        if self.workspace:
            self.workspace.reset_view()
        self.status_bar.showMessage("Visão do canvas resetada.", 2000)

    def zoom_in(self) -> None:
        if self.workspace:
            self.workspace.zoom_in()

    def zoom_out(self) -> None:
        if self.workspace:
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
        if self.workspace:
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
            dpi = params.get("dpi", 300)
            color_prof = params.get("color_profile_id", 0)
            bg_color = params.get("bg_color", (255, 255, 255, 255))
            paper_tex = params.get("paper_texture_id", 0)

            doc = self.dm.new_document(
                width=w,
                height=h,
                name=name,
                bg_color=bg_color,
                paper_texture_id=paper_tex
            )
            if hasattr(doc, "dpi"):
                doc.dpi = dpi

            # Inicializa a Facade C++ com as novas dimensões e papel do documento
            from ui.core.engine.registry import EngineRegistry
            backend = EngineRegistry.instance().get_backend()
            if backend:
                if hasattr(backend, "set_active_document_context"):
                    backend.set_active_document_context(doc.uid, w, h)
                else:
                    backend.init_renderer(0, w, h, w, h)
                if hasattr(backend, "set_color_profile"):
                    backend.set_color_profile(color_prof)

                backend.clear_canvas()
                r, g, b, a = bg_color
                is_vis = (a > 0)
                backend.set_canvas_paper_state(QtGui.QColor(r, g, b, a), is_vis, paper_tex, paper_tex > 0)

                # Mantém e aplica a cor de tinta ativa do usuário
                if self.workspace and hasattr(self.workspace, "_saved_color"):
                    color = self.workspace._saved_color
                    backend.set_brush_color(color.redF(), color.greenF(), color.blueF())

            self.reset_view()
            prof_name = backend.get_color_profile_name(color_prof) if backend else "sRGB"
            self.status_bar.showMessage(f"Novo documento '{name}' ({w}×{h} px, {dpi} DPI, {prof_name}) criado.", 3000)

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
