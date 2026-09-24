"""Contrato do ToolState: ferramenta ativa e opções de ferramenta (fonte única)."""

from __future__ import annotations

import pytest

from ui.core.state import ToolState, is_shape_tool, options_key
from ui.core.tool_settings import TOOL_SETTING_DEFAULTS, default_tool_settings


def test_starts_on_brush_with_default_options_for_every_configurable_tool():
    tools = ToolState()
    assert tools.active_tool == "brush"
    for key in TOOL_SETTING_DEFAULTS:
        assert tools.options(key) == default_tool_settings(key)
    assert tools.options("brush") == {}


def test_switching_tool_emits_once_with_previous_and_ignores_same_tool():
    tools = ToolState()
    seen = []
    tools.activeToolChanged.connect(lambda new, old: seen.append((new, old)))
    tools.set_active_tool("eraser")
    tools.set_active_tool("eraser")
    tools.set_active_tool("bucket")
    assert seen == [("eraser", "brush"), ("bucket", "eraser")]


def test_unknown_tool_is_rejected_without_changing_state():
    tools = ToolState()
    with pytest.raises(ValueError):
        tools.set_active_tool("martelo")
    assert tools.active_tool == "brush"


def test_options_are_normalized_merged_and_emitted_complete():
    tools = ToolState()
    seen = []
    tools.optionsChanged.connect(lambda key, opts: seen.append((key, opts)))

    tools.update_options("bucket", {"expansion": -3, "tolerance": 999})  # chave antiga + valor inválido
    assert seen == [("bucket", {**default_tool_settings("bucket"), "expand_px": -3})]

    seen.clear()
    tools.update_options("bucket", {"expand_px": -3})  # igual: não emite
    assert seen == []


def test_options_getter_returns_a_copy():
    tools = ToolState()
    opts = tools.options("wand")
    opts["tolerance"] = 99
    assert tools.options("wand")["tolerance"] == default_tool_settings("wand")["tolerance"]


def test_shape_tools_share_the_shapes_options_and_selecting_one_sets_the_type():
    assert options_key("shape_star") == "shapes"
    assert is_shape_tool("shapes") and is_shape_tool("shape_rect") and not is_shape_tool("bucket")

    tools = ToolState()
    order = []
    tools.optionsChanged.connect(lambda key, opts: order.append(("options", opts["shape_type"])))
    tools.activeToolChanged.connect(lambda new, old: order.append(("tool", new)))

    tools.set_active_tool("shape_star")
    # As opções mudam antes, para quem reage à troca já ler o tipo certo.
    assert order == [("options", "shape_star"), ("tool", "shape_star")]
    assert tools.options("shape_rect")["shape_type"] == "shape_star"


def test_tool_without_options_cannot_be_configured():
    with pytest.raises(ValueError):
        ToolState().update_options("brush", {"x": 1})
