"""MainWindow — casca do Lumenia: monta a janela e liga menus aos colaboradores.

O que a janela faz sozinha: criar MenuBar, ToolSidebar e StatusBar, instalar
o estado compartilhado antes dos plugins, receber o workspace do WorkspaceCore,
Desfazer/Refazer, câmera, tela cheia e eventos de janela (fechar, teclas).

O resto está em colaboradores com estado próprio, cada um recebendo pelo
construtor o que usa e falando com a barra de status pelo sinal
`statusMessage` (ver `shell_actions.py`):

  documents      DocumentActions     novo, abrir, salvar, fechar
  edit_actions   EditActions         área de transferência, preencher, seleção
  layer_actions  LayerActions        menu Camada (mesmos comandos do painel)
  image_actions  ImageActions        tamanho, recorte, rotação, guias, prova de cor
  dialogs        DialogActions       diálogos e janelas auxiliares
  recovery       RecoveryController  cópias de recuperação

O workspace e o canvas são alcançados só pelo contrato de `workspace_port.py`.
Até 2026-09-24 a janela era a soma de seis mixins que se liam por `self`.
"""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.infrastructure.theme.manager import ThemeManager
from ui.core.components import MenuBar, StatusBar, ToolSidebar
from ui.infrastructure.config.manager import ConfigManager
from ui.core.document.document import Document
from ui.core.document.manager import DocumentManager
from ui.core.engine.registry import EngineRegistry
from ui.infrastructure.i18n import I18nManager, tr
from ui.core.plugins.manager import PluginManager
from ui.core.plugins.registry import ServiceRegistry
from ui.infrastructure.accessibility import name_from_tooltips
from ui.infrastructure.app_info import APP_NAME
from ui.infrastructure.runtime_paths import resource_path
from ui.core.shortcut_registry import ShortcutRegistry
from ui.core.state import install_app_state

from .dialog_actions import DialogActions
from .document_actions import DocumentActions
from .edit_actions import EditActions
from .image_actions import ImageActions
from .layer_actions import LayerActions
from .menu_wiring import ShellCollaborators, wire_menu_bar, wire_tool_sidebar
from .recovery_controller import RecoveryController
from .workspace_port import ShellCanvas, ShellWorkspace


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        icon_path = resource_path("assets", "images", "icon_lumenia.png")
        if icon_path.is_file():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        ThemeManager.instance().themeChanged.connect(self._on_theme_changed)
        self.setStyleSheet(ThemeManager.instance().get_stylesheet())

        self.dm = DocumentManager.instance()
        from ui.infrastructure.bridge_client import create_backends
        EngineRegistry.instance().setup(create_backends())
        backend = EngineRegistry.instance().get_backend
        self._backend = backend

        # Estado compartilhado (fonte única) antes dos plugins: eles o recebem
        # pelo ServiceRegistry. Ver ui/core/state/README.md.
        self.app_state = install_app_state(ServiceRegistry.instance(), backend)

        # Componentes nativos da QMainWindow.
        self.menu_bar = MenuBar(self)
        self.setMenuBar(self.menu_bar)
        self.tool_sidebar = ToolSidebar(self)
        self.addToolBar(QtCore.Qt.TopToolBarArea, self.tool_sidebar)
        self.status_bar = StatusBar(self)
        self.setStatusBar(self.status_bar)

        # Plugins: o WorkspaceCore chama self.setCentralWidget(container) no
        # activate(). Sem plugins a janela abre com a tela vazia (workspace None).
        self.plugin_manager = PluginManager.instance()
        self.plugin_manager.set_main_window(self)
        self.plugin_manager.discover_plugins()
        self.workspace: Optional[ShellWorkspace] = self.centralWidget()
        self.canvas_widget: Optional[ShellCanvas] = (
            self.workspace.canvas_widget if self.workspace is not None else None
        )

        self.shortcut_registry = ShortcutRegistry(self, self.menu_bar, self.select_tool_by_id, self.canvas_widget)
        # Ctrl+Z e Ctrl+Y estão nas ações do menu Editar; Ctrl+Shift+Z é o
        # atalho alternativo de Refazer.
        self._redo_alternate = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+Z"), self)
        self._redo_alternate.activated.connect(self.redo)

        # Colaboradores.
        self.documents = DocumentActions(self, self.dm, backend, self.app_state.brush_sync, self.workspace)
        self.layer_actions = LayerActions(self, self.dm)
        self.edit_actions = EditActions(self, backend, self.app_state.brush, self.canvas_widget,
                                        self.layer_actions.commands)
        self.image_actions = ImageActions(self, self.dm, backend, self.workspace)
        self.dialogs = DialogActions(self, backend, self.workspace, self.shortcut_registry)
        self.recovery = RecoveryController(self, self.dm, backend, self.canvas_widget, self.documents)
        for collaborator in (self.documents, self.layer_actions, self.edit_actions,
                             self.image_actions, self.dialogs, self.recovery):
            collaborator.statusMessage.connect(self.status_bar.showMessage)
        collaborators = ShellCollaborators(
            documents=self.documents, edit=self.edit_actions, layers=self.layer_actions,
            image=self.image_actions, dialogs=self.dialogs,
        )
        wire_menu_bar(self.menu_bar, self, collaborators)
        wire_tool_sidebar(self.tool_sidebar, self, collaborators)

        config = ConfigManager.instance()
        try:
            self.shortcut_registry.apply(config.get_section("shortcuts"))
        except ValueError as exc:
            self.shortcut_registry.apply({})
            self.status_bar.showMessage(str(exc), 10000)
        config.persistenceFailed.connect(self._on_config_save_failed)
        if config.last_error:
            self._on_config_save_failed(config.last_error)

        self._watched_document: Optional[Document] = None
        self._watch_document(self.dm.active_document())
        self.dm.activeDocumentChanged.connect(self._on_active_document_changed)
        self.app_state.tools.activeToolChanged.connect(self._on_active_tool_changed)
        if self.workspace is not None:
            self._wire_workspace(self.workspace)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        # Depois de todas as retraduções (o slot desta janela é o último ligado).
        I18nManager.instance().languageChanged.connect(self._schedule_name_controls)
        self.retranslate_ui()
        self.update_undo_redo_actions()
        self._name_controls()

        self._first_show = True
        self._was_maximized_before_fullscreen = False

    def _wire_workspace(self, ws: ShellWorkspace) -> None:
        ws.zoomChanged.connect(self.status_bar.update_zoom)
        ws.statusMessage.connect(self.status_bar.showMessage)
        ws.newDocumentRequested.connect(self.documents.new_document)
        ws.documentCloseRequested.connect(self.documents.close_with_confirmation)
        ws.canvas_widget.strokeFinished.connect(self._on_canvas_stroke_finished)
        self.menu_bar.togglePanelRequested.connect(ws.toggle_panel_from_menu)
        ws.panelVisibilityChanged.connect(self.menu_bar.set_panel_checked)
        self.menu_bar.collapseAllSidebarsRequested.connect(ws.collapse_all_sidebars)
        self.menu_bar.expandAllSidebarsRequested.connect(ws.expand_all_sidebars)

    # ── Eventos da janela ─────────────────────────────────────────────────

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            QtCore.QTimer.singleShot(0, self, self.reset_view)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if not self.documents.close_all_for_exit():
            event.ignore()
            return
        event.accept()
        self.recovery.close()
        super().closeEvent(event)

    def changeEvent(self, event: QtCore.QEvent) -> None:
        super().changeEvent(event)
        if event.type() == QtCore.QEvent.WindowStateChange:
            self.menu_bar.view_menu.action_fullscreen.setChecked(self.isFullScreen())

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_F11:
            self.toggle_fullscreen()
            event.accept()
            return
        if event.key() == QtCore.Qt.Key_F12:
            self.dialogs.open_telemetry_window()
            event.accept()
            return
        if self._forward_space(event, pressed=True):
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QtGui.QKeyEvent) -> None:
        if self._forward_space(event, pressed=False):
            return
        super().keyReleaseEvent(event)

    def _forward_space(self, event: QtGui.QKeyEvent, pressed: bool) -> bool:
        """Espaço (mão) chega ao canvas mesmo com o foco em outro widget da janela."""
        if event.key() != QtCore.Qt.Key_Space or self.canvas_widget is None:
            return False
        if self.canvas_widget.forward_key(event, pressed):
            event.accept()
            return True
        return False

    # ── Reações a estado ──────────────────────────────────────────────────

    def _on_theme_changed(self, _theme_name: str) -> None:
        self.setStyleSheet(ThemeManager.instance().get_stylesheet())

    def _on_config_save_failed(self, message: str) -> None:
        self.status_bar.showMessage(
            tr("status.prefs_save_failed", "Não foi possível salvar as preferências: {error}", error=message), 10000)

    def _on_active_document_changed(self, doc: Optional[Document]) -> None:
        self._watch_document(doc)
        if doc is not None:
            self.status_bar.showMessage(tr("status.active_document", "Documento ativo: {name}", name=doc.name))
        else:
            self.status_bar.showMessage(tr("status.no_document", "Nenhum documento aberto."))
        self.update_undo_redo_actions()

    def _watch_document(self, doc: Optional[Document]) -> None:
        """Escuta `modified`/`history_cleared` só do documento ativo (Desfazer/Refazer acompanham)."""
        if self._watched_document is not None:
            self._watched_document.modified.disconnect(self._on_document_modified)
            self._watched_document.history_cleared.disconnect(self.update_undo_redo_actions)
        self._watched_document = doc
        if doc is not None:
            doc.modified.connect(self._on_document_modified)
            doc.history_cleared.connect(self.update_undo_redo_actions)

    def _on_document_modified(self, _reason: str) -> None:
        self.update_undo_redo_actions()

    def _on_canvas_stroke_finished(self) -> None:
        # O traço não passa pelo modelo de camadas: quem suja o documento é a
        # casca (o `modified` resultante atualiza Desfazer/Refazer).
        document = self.dm.active_document()
        if document is not None:
            document.mark_dirty("canvas")

    def _on_active_tool_changed(self, tool_id: str, _previous: str) -> None:
        self.tool_sidebar.show_active_tool(tool_id)

    def _schedule_name_controls(self) -> None:
        QtCore.QTimer.singleShot(0, self, self._name_controls)

    def _name_controls(self) -> None:
        """Nome acessível de cada controle só com ícone = a dica traduzida."""
        name_from_tooltips(self)

    def retranslate_ui(self) -> None:
        """Propaga a tradução ativa para os componentes da janela."""
        self.menu_bar.retranslate_ui()
        self.tool_sidebar.retranslate_ui()
        if self.workspace is not None:
            self.workspace.retranslate_ui()

    # ── Desfazer / Refazer ────────────────────────────────────────────────

    def undo(self) -> None:
        if self.workspace is not None:
            self.workspace.undo()
            self.update_undo_redo_actions()

    def redo(self) -> None:
        if self.workspace is not None:
            self.workspace.redo()
            self.update_undo_redo_actions()

    def update_undo_redo_actions(self) -> None:
        """Atualiza a disponibilidade de Desfazer e Refazer no menu e na barra."""
        backend = self._backend()
        has_doc = self.dm.has_document()
        can_undo = bool(has_doc and backend and backend.can_undo())
        can_redo = bool(has_doc and backend and backend.can_redo())
        self.menu_bar.update_history_state(can_undo, can_redo)
        self.tool_sidebar.update_history_state(can_undo, can_redo)

    # ── Ferramenta, câmera e tela cheia ───────────────────────────────────

    def select_tool_by_id(self, tool_id: str) -> None:
        """Atalhos, menus e barra lateral pedem a troca ao ToolState; as views reagem."""
        self.app_state.tools.set_active_tool(tool_id)

    def reset_view(self) -> None:
        if self.workspace is not None:
            self.workspace.reset_view()
        self.status_bar.showMessage(tr("status.view_reset", "Visão do canvas resetada."), 2000)

    def zoom_in(self) -> None:
        if self.workspace is not None:
            self.workspace.zoom_in()

    def zoom_out(self) -> None:
        if self.workspace is not None:
            self.workspace.zoom_out()

    def toggle_fullscreen(self) -> None:
        """Alterna entre tela cheia e o estado anterior (normal ou maximizado)."""
        if self.isFullScreen():
            self.showMaximized() if self._was_maximized_before_fullscreen else self.showNormal()
            msg = tr("status.fullscreen_off", "Modo normal restaurado.")
        else:
            self._was_maximized_before_fullscreen = self.isMaximized()
            self.showFullScreen()
            msg = tr("status.fullscreen_on", "Modo Tela Cheia ativado. Pressione F11 para sair.")
        self.status_bar.showMessage(msg, 3500)
        self.menu_bar.view_menu.action_fullscreen.setChecked(self.isFullScreen())
