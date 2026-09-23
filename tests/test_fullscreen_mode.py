"""
Test Suite: Full Screen Mode via F11 and Menus (ARCcC Phase 5)
==============================================================
Valida o ciclo completo de alternância de tela cheia (Full Screen):
- Atalho canônico F11
- Ações nos menus Exibir e Janela
- Integração com ShortcutRegistry e DEFAULT_SHORTCUTS
- Sincronização do checkmark de status
"""

import pytest
from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.components.menu_bar.menu_bar import MenuBar
from ui.core.shortcut_registry import ShortcutRegistry
from ui.core.shortcut_catalog import DEFAULT_SHORTCUTS


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def test_fullscreen_actions_and_shortcuts_in_menus(qapp):
    """Valida que ViewMenu e WindowMenu possuem as ações de Tela Cheia com atalho F11."""
    win = QtWidgets.QMainWindow()
    menu_bar = MenuBar(win)

    # 1. ViewMenu
    act_view_fs = menu_bar.view_menu.action_fullscreen
    assert act_view_fs is not None
    assert act_view_fs.isCheckable() is True
    assert act_view_fs.shortcut().toString() == "F11"

    # 2. WindowMenu
    act_win_fs = menu_bar.window_menu.act_fullscreen
    assert act_win_fs is not None

    # 3. Propagação de sinal para MenuBar
    signals_received = []
    menu_bar.toggleFullscreenRequested.connect(lambda: signals_received.append(True))

    act_view_fs.trigger()
    assert len(signals_received) == 1

    act_win_fs.trigger()
    assert len(signals_received) == 2

    win.deleteLater()


def test_fullscreen_registered_in_shortcut_catalog(qapp):
    """Valida presença de view_fullscreen no catálogo canônico e ShortcutRegistry."""
    win = QtWidgets.QMainWindow()
    win.menu_bar = MenuBar(win)
    win.select_tool_by_id = lambda tool: None
    for suffix in ("b", "e", "u", "t"):
        setattr(win, f"shortcut_tool_{suffix}", QtGui.QShortcut(win))

    registry = ShortcutRegistry(win)
    try:
        assert "view_fullscreen" in registry.targets
        target = registry.targets["view_fullscreen"]
        assert isinstance(target, QtGui.QAction)
        assert target.shortcut().toString() == "F11"

        catalog_entry = next((item for item in DEFAULT_SHORTCUTS if item["id"] == "view_fullscreen"), None)
        assert catalog_entry is not None
        assert catalog_entry["default"] == "F11"
        assert catalog_entry["category"] == "Exibir"
    finally:
        registry.cleanup()
        win.deleteLater()


def test_main_window_toggle_fullscreen(qapp):
    """Valida o método toggle_fullscreen da MainWindow e sincronização de estado."""
    # Usa a MainWindow compartilhada da suíte em vez de criar e destruir uma:
    # só a primeira MainWindow do processo recebe o WorkspaceCore, e destruí-la
    # deixava os módulos seguintes (MDI, menu bar, camadas) sem workspace.
    from tests.main_window_fixture import main_window_com_workspace
    win = main_window_com_workspace()
    try:
        assert win.isFullScreen() is False
        assert win.menu_bar.view_menu.action_fullscreen.isChecked() is False

        # 1. Ativa FullScreen
        win.toggle_fullscreen()
        assert win.isFullScreen() is True
        assert win.menu_bar.view_menu.action_fullscreen.isChecked() is True
        assert "F11" in win.status_bar.currentMessage()

        # 2. Desativa FullScreen
        win.toggle_fullscreen()
        assert win.isFullScreen() is False
        assert win.menu_bar.view_menu.action_fullscreen.isChecked() is False
        assert "normal" in win.status_bar.currentMessage().lower()

        # 3. Disparo via keyPressEvent simulado com F11
        key_event_f11 = QtGui.QKeyEvent(QtCore.QEvent.Type.KeyPress, QtCore.Qt.Key_F11, QtCore.Qt.KeyboardModifier.NoModifier)
        win.keyPressEvent(key_event_f11)
        assert win.isFullScreen() is True
        assert win.menu_bar.view_menu.action_fullscreen.isChecked() is True

        # Pressiona F11 novamente para sair
        win.keyPressEvent(key_event_f11)
        assert win.isFullScreen() is False
        assert win.menu_bar.view_menu.action_fullscreen.isChecked() is False
    finally:
        if win.isFullScreen():
            win.toggle_fullscreen()
