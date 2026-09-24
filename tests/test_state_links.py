"""Regras entre estados (ui/core/state/state_links.py).

- ShapeColorLink: as formas usam a cor do pincel; o fundo mantém a própria
  opacidade. Antes existiam três cópias desta regra (canvas, barra
  secundária, painel de pincel) e a do canvas zerava a transparência do fundo.
- ToolEngineSync: as opções do Smudge chegam ao motor por um caminho só.
"""
from PySide6 import QtGui

from ui.core.plugins.registry import ServiceRegistry
from ui.core.state import BrushState, ShapeColorLink, ToolEngineSync, ToolState, install_app_state


def test_shape_colors_follow_the_brush_and_keep_the_fill_opacity(qapp):
    brush, tools = BrushState(), ToolState()
    link = ShapeColorLink(brush, tools)  # noqa: F841 - mantém a regra viva

    half = QtGui.QColor(tools.options("shapes")["fill_color"])
    half.setAlpha(128)
    tools.update_options("shapes", {"fill_color": half})

    brush.set_color(QtGui.QColor(200, 10, 20))

    shapes = tools.options("shapes")
    assert shapes["stroke_color"] == QtGui.QColor(200, 10, 20)
    assert shapes["fill_color"].getRgb() == (200, 10, 20, 128)


def test_shape_colors_start_with_the_current_brush_color(qapp):
    brush, tools = BrushState(), ToolState()
    brush.set_color(QtGui.QColor(1, 2, 3))
    ShapeColorLink(brush, tools)
    assert tools.options("shapes")["stroke_color"] == QtGui.QColor(1, 2, 3)


class _RecordingBackend:
    def __init__(self):
        self.calls = []

    def set_brush_param(self, group, param, value):
        self.calls.append((group, param, value))


def test_smudge_options_reach_the_engine_and_other_tools_do_not(qapp):
    tools, backend = ToolState(), _RecordingBackend()
    sync = ToolEngineSync(tools, lambda: backend)  # noqa: F841

    tools.update_options("bucket", {"tolerance": 55})
    assert backend.calls == []

    tools.update_options("smudge", {"mix_ratio": 0.25})
    assert ("smudge", "mix_ratio", 0.25) in backend.calls
    assert {c[1] for c in backend.calls} == {"smudge_stretch", "color_pickup", "mix_ratio"}


def test_install_app_state_is_idempotent_and_keeps_the_links(qapp):
    registry = ServiceRegistry()
    first = install_app_state(registry, lambda: None)
    second = install_app_state(registry, lambda: None)
    assert first == second
    assert registry.get(ShapeColorLink) is first.shape_colors
    assert registry.get(ToolEngineSync) is first.tool_sync
