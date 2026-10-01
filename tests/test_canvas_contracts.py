"""Contratos dos colaboradores do canvas e pastas Python sem importar a mãe.

Até 2026-09-25 os colaboradores do canvas (`canvas/tools`, `canvas/viewport`)
importavam o `RenderWidget` da pasta mãe só para anotar tipo: os dois ciclos
Python que restavam (canvas ↔ tools, canvas ↔ viewport). Agora cada um declara
o contrato que usa (`RouterCanvas`, `KeyCanvas`, `ViewportCanvas`,
`StrokeCanvas`, `CursorCanvas`, `TextCanvas`, `ToolCanvas`, `SelectionCanvas`,
`TransformCanvas`, `ShapeCanvas`, `EyedropCanvas`, `GeometryCanvas`) e este teste
confere que o `RenderWidget` cumpre todos.

O segundo teste é a catraca do ARCcC "subpasta não importa a mãe" para o
Python (a do C++ está em `test_arccc_cxx_layers.py`): os pares que restam
são módulos soltos na pasta mãe, listados em `KNOWN_PARENT_IMPORTS`; par novo
reprova, par que some deve sair da lista.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ui.plugins.system.workspace_core.workspace.canvas.tools.eyedrop_tool_controller import EyedropCanvas
from ui.plugins.system.workspace_core.workspace.canvas.tools.geometry_tool_controller import GeometryCanvas
from ui.plugins.system.workspace_core.workspace.canvas.tools.selection_tool_controller import SelectionCanvas
from ui.plugins.system.workspace_core.workspace.canvas.tools.shape_tool_controller import ShapeCanvas
from ui.plugins.system.workspace_core.workspace.canvas.tools.text_tool_controller import TextCanvas
from ui.plugins.system.workspace_core.workspace.canvas.tools.tool_manager import ToolCanvas
from ui.plugins.system.workspace_core.workspace.canvas.tools.transform_tool_controller import TransformCanvas
from ui.plugins.system.workspace_core.workspace.canvas.viewport.canvas_stroke_pipeline import StrokeCanvas
from ui.plugins.system.workspace_core.workspace.canvas.viewport.cursor_controller import CursorCanvas
from ui.plugins.system.workspace_core.workspace.canvas.viewport.input_router import RouterCanvas
from ui.plugins.system.workspace_core.workspace.canvas.viewport.key_router import KeyCanvas
from ui.plugins.system.workspace_core.workspace.canvas.viewport.viewport_renderer import ViewportCanvas

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = (
    RouterCanvas, KeyCanvas, ViewportCanvas, StrokeCanvas, CursorCanvas, TextCanvas, ToolCanvas,
    SelectionCanvas, TransformCanvas, ShapeCanvas, EyedropCanvas, GeometryCanvas,
)

# Subpasta que importa módulo solto da pasta mãe (dívida conhecida em 2026-09-25).
KNOWN_PARENT_IMPORTS = {
    ("ui/core/screens", "ui/core"),                            # tools, shortcut_catalog
    ("ui/core/state", "ui/core"),                              # tool_settings, tools
    ("ui/core/widgets/tool_options", "ui/core/widgets"),       # shape_dropdown, compact_slider
    ("ui/infrastructure/i18n", "ui/infrastructure"),           # runtime_paths
    ("ui/infrastructure/logging", "ui/infrastructure"),        # runtime_paths
}


@pytest.mark.parametrize("contract", CONTRACTS, ids=lambda c: c.__name__)
def test_render_widget_fulfils_every_collaborator_contract(qapp, contract):
    from ui.plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget

    widget = RenderWidget()
    try:
        missing = [name for name in contract.__protocol_attrs__ if not hasattr(widget, name)] \
            if hasattr(contract, "__protocol_attrs__") else []
        assert isinstance(widget, contract), f"{contract.__name__}: faltam {missing}"
    finally:
        widget.deleteLater()


def _parent_imports() -> set[tuple[str, str]]:
    pairs = set()
    for path in (ROOT / "ui").rglob("*.py"):
        package = path.parent.relative_to(ROOT).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base = path.parent
                    for _ in range(node.level - 1):
                        base = base.parent
                    module = base.relative_to(ROOT).as_posix().replace("/", ".") + (f".{node.module}" if node.module else "")
                else:
                    module = node.module or ""
                names = [module]
            elif isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                continue
            for name in names:
                if not name.startswith("ui."):
                    continue
                target = ROOT / name.replace(".", "/")
                folder = target if target.is_dir() else target.parent
                folder_rel = folder.relative_to(ROOT).as_posix()
                if package.startswith(folder_rel + "/"):
                    pairs.add((package, folder_rel))
    return pairs


def test_no_new_python_folder_imports_its_parent():
    pairs = _parent_imports()
    assert pairs - KNOWN_PARENT_IMPORTS == set(), "subpasta importando a pasta mãe (ciclo)"
    assert KNOWN_PARENT_IMPORTS - pairs == set(), "par resolvido: tire de KNOWN_PARENT_IMPORTS"
