"""
Testes de Regressão e Contrato para a Decomposição da Fase 4 da Camada 5 (ARCcC v2)
====================================================================================
Valida o desacoplamento de MainWindowDialogActionsMixin e MainWindowMenuActionsMixin.
"""

import pytest
from PySide6 import QtWidgets, QtCore, QtGui

from ui.boundary.orchestrator.main_window_dialog_actions import MainWindowDialogActionsMixin
from ui.boundary.orchestrator.main_window_menu_actions import MainWindowMenuActionsMixin


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


class DummyHost(QtWidgets.QMainWindow, MainWindowMenuActionsMixin):
    """Host falso simulando a MainWindow para testar o mixin desacoplado."""

    def __init__(self):
        super().__init__()
        from ui.core.components.menu_bar import MenuBar
        from ui.core.shortcut_registry import ShortcutRegistry
        self.status_bar = QtWidgets.QStatusBar()
        self.workspace = None
        self.menu_bar = MenuBar(self)
        self.shortcut_undo = self.menu_bar.edit_menu.act_undo
        self.shortcut_tool_b = QtGui.QAction("Brush", self)
        for suffix in ("e", "u", "t"):
            setattr(self, f"shortcut_tool_{suffix}", QtGui.QShortcut(self))
        self.shortcut_registry = ShortcutRegistry(self)


def test_main_window_dialog_actions_mixin_contract():
    """Valida a presença de todos os métodos esperados em MainWindowDialogActionsMixin."""
    expected_dialog_methods = [
        "open_filter_gallery",
        "open_filter_dialog",
        "open_diagnostics_dialog",
        "open_user_guide",
        "open_test_report_dialog",
        "open_shortcuts_dialog",
        "_on_shortcuts_applied",
        "open_cursor_settings_dialog",
        "_on_cursor_settings_changed",
        "open_feedback_form",
        "open_about_dialog",
        "load_custom_texture",
        "set_application_language",
        "open_telemetry_grid_window",
    ]
    for method_name in expected_dialog_methods:
        assert hasattr(MainWindowDialogActionsMixin, method_name), f"Método {method_name} ausente em MainWindowDialogActionsMixin"


def test_main_window_menu_actions_mixin_inheritance(qapp):
    """Valida que MainWindowMenuActionsMixin herda e mantém 100% dos métodos."""
    assert issubclass(MainWindowMenuActionsMixin, MainWindowDialogActionsMixin)

    host = DummyHost()
    try:
        # Testa aplicação de atalhos pelo mixin
        host._on_shortcuts_applied({"edit_undo": "Ctrl+Z", "tool_brush": "B"})
        assert host.shortcut_undo.shortcut().toString() == "Ctrl+Z"
        assert host.shortcut_tool_b.shortcut().toString() == "B"

        # Testa troca de idioma
        host.set_application_language("auto")
        assert "Idioma" in host.status_bar.currentMessage()
    finally:
        host.shortcut_registry.cleanup()
        host.deleteLater()
