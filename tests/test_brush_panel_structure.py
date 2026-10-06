"""BrushSettingsPanel e seus componentes como views do BrushState.

Até 2026-09-24 este arquivo testava "retrocompatibilidade": que o painel
expunha `qs_size`, `_quick_sliders`, `_tool_buttons`... para o workspace ler e
escrever os sliders por dentro. Esses acessos eram o espaguete; o contrato
agora é o BrushState, e é ele que se testa aqui.
"""

import pytest
from PySide6 import QtGui

from ui.plugins.panels.brush_plugin.components.quick_sliders_section import QuickSlidersSection
from ui.plugins.panels.brush_plugin.components.tool_selection_column import ToolSelectionColumn
from ui.plugins.panels.brush_plugin.panel import BrushSettingsPanel
from ui.core.state import BrushParam, BrushState, ToolState
from ui.core.widgets.compact_slider import CompactSlider


def test_tool_selection_column(qapp):
    col = ToolSelectionColumn()
    assert len(col.tool_buttons) >= 6
    assert "brush" in col.tool_buttons
    assert "eraser" in col.tool_buttons

    activated_tools = []
    col.toolActivated.connect(activated_tools.append)

    col.set_tool_active("eraser")
    assert col.tool_buttons["eraser"].isChecked()
    assert not col.tool_buttons["brush"].isChecked()

    col._on_btn_clicked("brush")
    assert "brush" in activated_tools
    assert col.tool_buttons["brush"].isChecked()


def test_quick_sliders_section_edits_and_shows_in_engine_units(qapp):
    sec = QuickSlidersSection()
    assert len(sec.all_sliders) == 9
    assert isinstance(sec.slider(BrushParam.SIZE), CompactSlider)
    assert isinstance(sec.slider(BrushParam.FLOW), CompactSlider)

    edited = []
    sec.paramEdited.connect(lambda p, v: edited.append((p, v)))

    sec.slider(BrushParam.SIZE).setValue(120)
    sec.slider(BrushParam.OPACITY).setValue(80)
    assert (BrushParam.SIZE, 120.0) in edited
    assert (BrushParam.OPACITY, 0.8) in edited
    sec.slider(BrushParam.FLOW).setValue(35)
    assert (BrushParam.FLOW, 0.35) in edited

    # show_value não emite (é o caminho estado -> view).
    edited.clear()
    sec.show_value(BrushParam.CONTRAST, 1.5)
    assert sec.slider(BrushParam.CONTRAST).value() == 15
    assert edited == []

    assert sec.slider(BrushParam.CONTRAST).isHidden()
    sec.set_pinned_visible("contrast", True)
    assert not sec.slider(BrushParam.CONTRAST).isHidden()


def test_panel_writes_to_state_and_follows_state(qapp):
    state = BrushState()
    panel = BrushSettingsPanel(state, ToolState())
    sliders = panel.sliders_section

    # Estado inicial aparece nos sliders.
    assert sliders.slider(BrushParam.SIZE).value() == int(state.value(BrushParam.SIZE))

    # Slider -> estado.
    sliders.slider(BrushParam.SIZE).setValue(45)
    assert state.value(BrushParam.SIZE) == 45.0

    # Estado (vindo de outro lugar) -> slider.
    state.set_value(BrushParam.OPACITY, 0.25)
    assert sliders.slider(BrushParam.OPACITY).value() == 25


def test_preset_choice_goes_through_state(qapp):
    state = BrushState()
    panel = BrushSettingsPanel(state, ToolState())
    selected = []
    state.presetSelected.connect(lambda tool, name, data: selected.append((tool, name)))

    state.select_preset("brush", "Teste", {
        "brush_size": 99,
        "opacity": 0.75,
        "stabilizer_weight": 0.42,
        "spacing_factor": 0.15,
        "brush_grain_contrast": 1.5,
    })

    assert selected == [("brush", "Teste")]
    assert panel.sliders_section.slider(BrushParam.SIZE).value() == 99
    assert panel.sliders_section.slider(BrushParam.OPACITY).value() == 75
    assert panel.preset_combo.active_preset == "Teste"


def test_tool_switch_restores_each_tools_preset(qapp):
    state = BrushState()
    tools = ToolState()
    panel = BrushSettingsPanel(state, tools)
    state.select_preset("brush", "Meu Pincel", {"brush_size": 33})
    tools.set_active_tool("eraser")
    assert state.preset("eraser") is not None  # padrão da categoria borracha
    assert panel.tool_column.tool_buttons["eraser"].isChecked()
    tools.set_active_tool("brush")
    assert panel.preset_combo.active_preset == "Meu Pincel"
    assert state.value(BrushParam.SIZE) == 33.0


def test_color_from_state_reaches_panel_widgets(qapp):
    state = BrushState()
    panel = BrushSettingsPanel(state, ToolState())
    state.set_color(QtGui.QColor(1, 2, 3))
    assert panel.stroke_preview._color == pytest.approx([1 / 255, 2 / 255, 3 / 255], abs=1e-6)
