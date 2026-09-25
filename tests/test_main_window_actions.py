"""Contrato da casca: colaboradores da MainWindow e a porta do workspace.

Até 2026-09-24 a MainWindow era a soma de seis mixins que se liam por `self`
(este arquivo testava que `MainWindowMenuActionsMixin` herdava os outros).
Agora cada ação mora num colaborador com construtor próprio, e a casca só
fala com o workspace e o canvas pelo que `workspace_port.py` declara.
"""

import ast
from pathlib import Path

import pytest
from PySide6 import QtWidgets

from ui.boundary.orchestrator.dialog_actions import DialogActions
from ui.boundary.orchestrator.shell_actions import ShellActions
from ui.boundary.orchestrator.workspace_port import SHELL_CANVAS_MEMBERS, SHELL_WORKSPACE_MEMBERS

_ORCHESTRATOR = Path("ui/boundary/orchestrator")


def test_workspace_container_fulfils_shell_port():
    """O WorkspaceContainer e o RenderWidget têm tudo que a casca usa."""
    from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget
    from plugins.system.workspace_core.workspace.workspace_container import WorkspaceContainer

    class_members = {"canvas_widget"}  # atributo de instância criado no __init__
    missing = [m for m in SHELL_WORKSPACE_MEMBERS if m not in class_members and not hasattr(WorkspaceContainer, m)]
    assert missing == [], f"WorkspaceContainer não cumpre a porta da casca: {missing}"
    instance_members = {"rotation", "flip_x", "flip_y"}  # propriedades da câmera
    missing = [m for m in SHELL_CANVAS_MEMBERS if not hasattr(RenderWidget, m) and m not in instance_members]
    assert missing == [], f"RenderWidget não cumpre a porta da casca: {missing}"


def test_collaborators_do_not_read_each_other_through_self():
    """Nenhum colaborador herda de outro nem usa hasattr/getattr para descobrir o dono."""
    for path in sorted(_ORCHESTRATOR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in ("hasattr", "getattr"), f"{path}:{node.lineno} usa {node.func.id}"
            if isinstance(node, ast.ClassDef) and node.name.endswith("Mixin"):
                pytest.fail(f"{path}: mixin {node.name} voltou para a casca")


def test_dialog_actions_apply_shortcuts_and_language(qapp):
    from ui.core.components.menu_bar import MenuBar
    from ui.infrastructure.i18n import tr
    from ui.core.shortcut_registry import ShortcutRegistry

    window = QtWidgets.QMainWindow()
    menu = MenuBar(window)
    registry = ShortcutRegistry(window, menu, lambda tool: None)
    dialogs = DialogActions(window, lambda: None, None, registry)
    messages = []
    dialogs.statusMessage.connect(lambda text, _ms: messages.append(text))
    try:
        assert isinstance(dialogs, ShellActions)
        dialogs.apply_shortcuts({"edit_undo": "Ctrl+Z", "tool_brush": "B"})
        assert menu.edit_menu.act_undo.shortcut().toString() == "Ctrl+Z"
        assert registry.targets["tool_brush"].key().toString() == "B"

        # "auto" segue o idioma do sistema: a mensagem esperada é a do idioma
        # que ficou ativo, não uma frase fixa em português.
        dialogs.set_language("auto")
        assert messages[-1] == tr("status.language_changed", "Idioma sincronizado com o sistema operacional.")
    finally:
        from tests.qt_windows import destroy_now
        registry.cleanup()
        destroy_now(window)


def test_main_window_exposes_collaborators(qapp):
    from tests.main_window_fixture import main_window_com_workspace

    win = main_window_com_workspace()
    for name in ("documents", "edit_actions", "layer_actions", "image_actions", "dialogs", "recovery"):
        assert isinstance(getattr(win, name), ShellActions), name
    # O LayerCommands do menu Camada age sempre no documento ativo.
    doc = win.dm.active_document()
    expected = doc.layer_manager if doc is not None else None
    assert win.layer_actions.commands.layer_manager is expected
