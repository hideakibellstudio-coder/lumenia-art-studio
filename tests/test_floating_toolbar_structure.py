"""
Testes de Regressão e Contrato para a Decomposição da Fase 2 da Camada 5 (ARCcC v2)
====================================================================================
Valida o desacoplamento de ToolbarLivePreview, ToolToggleCard e FloatingToolbarSettingsDialog.
"""


from ui.core.screens.floating_toolbar_components import (
    ToolbarLivePreview,
    ToolToggleCard,
)
from ui.core.screens.floating_toolbar_settings_dialog import (
    FloatingToolbarSettingsDialog,
    ToolbarLivePreview as ReExportedToolbarLivePreview,
    ToolToggleCard as ReExportedToolToggleCard,
    load_floating_toolbar_settings,
)



def test_toolbar_live_preview_contract(qapp):
    """Valida o componente isolado ToolbarLivePreview."""
    preview = ToolbarLivePreview()
    assert preview.height() == 54

    # Teste de atualização de ferramentas
    tools = ["brush", "eraser", "lasso"]
    preview.set_tools(tools)
    assert preview._active_tools == tools
    assert preview.layout.count() >= 4  # handle + 3 ferramentas

    # Re-exportação
    assert ReExportedToolbarLivePreview is ToolbarLivePreview


def test_tool_toggle_card_contract(qapp):
    """Valida o componente isolado ToolToggleCard."""
    card = ToolToggleCard("brush", is_active=True)
    assert card.tool_id == "brush"
    assert card.is_active is True
    assert card.switch.isChecked() is True

    # Sinais e alternância
    signal_received = []
    card.toggled.connect(lambda tid, active: signal_received.append((tid, active)))

    card._on_toggled(False)
    assert card.is_active is False
    assert len(signal_received) == 1
    assert signal_received[0] == ("brush", False)

    card.set_active_state(True)
    assert card.is_active is True
    assert card.switch.isChecked() is True

    # Re-exportação
    assert ReExportedToolToggleCard is ToolToggleCard


def test_floating_toolbar_settings_dialog_integration(qapp):
    """Valida a integração completa do FloatingToolbarSettingsDialog."""
    dlg = FloatingToolbarSettingsDialog()
    try:
        assert len(dlg._cards) > 0
        assert isinstance(dlg.live_preview, ToolbarLivePreview)
        assert hasattr(dlg, "search_box")
        assert hasattr(dlg, "combo_speed")

        # Testa filtro de ferramentas
        dlg.search_box.setText("brush")
        dlg._filter_tools()

        # Testa configurações salvas
        cfg = load_floating_toolbar_settings()
        assert "tools" in cfg
        assert "active" in cfg
    finally:
        dlg.close()
