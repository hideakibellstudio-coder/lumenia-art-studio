"""Contrato da barra secundária (ui/plugins/system/workspace_core/workspace/secondary_tool_bar).

A barra é moldura + uma view por ferramenta e orientação; cada view é view do
ToolState. Até 2026-09-24 a barra tinha três mixins de handlers, nove funções
`build_*_panels(toolbar)` e cada opção existia duas vezes (`_h`/`_v`), copiada
de uma para a outra à mão.
"""

import pytest
from PySide6 import QtCore, QtGui

from ui.plugins.system.workspace_core.workspace.secondary_tool_bar import SecondaryToolBar
from ui.core.plugins.registry import ServiceRegistry
from ui.core.state import install_app_state
from ui.core.tools import ToolCommand

H, V = QtCore.Qt.Horizontal, QtCore.Qt.Vertical


@pytest.fixture
def bar(qapp):
    state = install_app_state(ServiceRegistry(), lambda: None)
    toolbar = SecondaryToolBar(state.tools, state.brush)
    yield toolbar, state
    toolbar.deleteLater()


def test_both_orientations_show_the_same_state_without_knowing_each_other(bar):
    toolbar, state = bar
    toolbar.option_view("bucket", H).slider_tol.setValue(45)
    assert state.tools.options("bucket")["tolerance"] == 45
    vertical = toolbar.option_view("bucket", V)
    assert vertical.slider_tol.value() == 45 and vertical.lbl_tol_val.text() == "45%"

    state.tools.update_options("wand", {"tolerance": 12, "mode": 2})
    for orientation in (H, V):
        wand = toolbar.option_view("wand", orientation)
        assert wand.slider_tol.value() == 12 and wand.cbo_mode.currentIndex() == 2


def test_rect_ellipse_and_lasso_have_separate_options(bar):
    toolbar, state = bar
    toolbar.option_view("ellipse_select", H).slider_feather.setValue(9)
    assert state.tools.options("ellipse_select")["feather_px"] == 9
    assert state.tools.options("rect_select")["feather_px"] == 0
    assert state.tools.options("lasso")["feather_px"] == 0


def test_shape_extra_parameter_shows_the_stored_value_of_the_shape_type(bar):
    toolbar, state = bar
    state.tools.update_options("shapes", {"star_points": 9})
    state.tools.set_active_tool("shape_star")
    view = toolbar.option_view("shapes", V)
    assert not view.slider_extra.isHidden()
    assert view.slider_extra.value() == 9

    state.tools.set_active_tool("shape_line")
    assert view.slider_extra.isHidden()


def test_shape_colors_and_eyedrop_swatch_follow_the_brush_color(bar):
    toolbar, state = bar
    state.brush.set_color(QtGui.QColor(10, 200, 30))
    assert state.tools.options("shapes")["stroke_color"] == QtGui.QColor(10, 200, 30)
    assert toolbar.option_view("eyedrop", H).lbl_hex.text() == "#0AC81E"


def test_fill_opacity_keeps_color_alpha_and_fraction_together(bar):
    toolbar, state = bar
    toolbar.option_view("shapes", H).slider_opacity.setValue(50)
    shapes = state.tools.options("shapes")
    assert shapes["fill_opacity"] == 0.5
    assert shapes["fill_color"].alpha() == 127
    assert toolbar.option_view("shapes", V).slider_opacity.value() == 50


def test_smudge_preset_fills_the_three_values_and_both_combos_agree(bar):
    toolbar, state = bar
    toolbar.option_view("smudge", V).cbo_preset.setCurrentIndex(2)
    assert state.tools.options("smudge") == {"smudge_stretch": 0.5, "color_pickup": 0.5, "mix_ratio": 0.4}
    assert toolbar.option_view("smudge", H).cbo_preset.currentIndex() == 2


def test_text_alignment_is_exclusive_and_clicking_the_active_one_keeps_it(bar):
    toolbar, state = bar
    view = toolbar.option_view("text", H)
    view.align_buttons["center"].click()
    assert state.tools.options("text")["align"] == "center"
    view.align_buttons["center"].click()
    assert view.align_buttons["center"].isChecked()
    assert [b.isChecked() for b in toolbar.option_view("text", V).align_buttons.values()] == [False, True, False]


def test_buttons_emit_tool_commands_instead_of_reaching_the_canvas(bar):
    toolbar, _state = bar
    commands = []
    toolbar.commandRequested.connect(commands.append)
    toolbar.option_view("lasso", V).btn_deselect.click()
    toolbar.option_view("transform", H).btn_commit.click()
    toolbar.option_view("text", V).btn_cancel.click()
    assert commands == [ToolCommand.DESELECT, ToolCommand.TRANSFORM_COMMIT, ToolCommand.TEXT_CANCEL]


def test_bar_shows_only_for_tools_with_options_and_shrinks_with_its_content(bar):
    toolbar, state = bar
    state.tools.set_active_tool("shape_star")
    assert toolbar.isVisible()
    wide = toolbar.width()
    state.tools.set_active_tool("shape_ellipse")
    assert toolbar.width() < wide, "sem o parâmetro extra a barra deve encolher"
    state.tools.set_active_tool("brush")
    assert not toolbar.isVisible()
