"""Painéis que o workspace liga pelo id: contrato declarado e conferido.

O workspace conecta a troca de documento e a câmera aos painéis registrados
como `navigator` e `layers`. Até 2026-09-25 o que esses widgets precisavam ter
era implícito; agora está em `PANEL_CONTRACTS` (`ui/core/plugins/panel_ids.py`)
e `add_panel` recusa, antes de registrar, um widget que não cumpre.
"""
from __future__ import annotations

import pytest
from PySide6 import QtWidgets

from ui.core.plugins.panel_ids import PANEL_CONTRACTS, PanelId


def test_real_panels_fulfil_their_contracts(qapp):
    from ui.plugins.panels.layers_plugin.panel import LayersPanel
    from ui.plugins.panels.navigator_plugin.panel import NavigatorPanel

    panels = {PanelId.NAVIGATOR: NavigatorPanel(), PanelId.LAYERS: LayersPanel()}
    for panel_id, panel in panels.items():
        assert isinstance(panel, PANEL_CONTRACTS[panel_id]), panel_id
        panel.deleteLater()


@pytest.mark.parametrize("panel_id", [PanelId.NAVIGATOR, "layers"])
def test_add_panel_refuses_a_widget_without_the_contract(qapp, panel_id):
    from tests.main_window_fixture import main_window_com_workspace

    ws = main_window_com_workspace().workspace
    before = ws.panel(panel_id)
    impostor = QtWidgets.QWidget()
    with pytest.raises(TypeError, match="não cumpre"):
        ws.add_panel(panel_id, "Impostor", impostor)
    assert ws.panel(panel_id) is before, "o painel anterior continua registrado"
    impostor.deleteLater()
