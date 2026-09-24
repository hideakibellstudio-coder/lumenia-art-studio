"""Menu Janela: cada item abre o painel registrado com o mesmo PanelId.

Até 2026-09-24 o menu pedia "brush_plugin", "color_plugin", "layers_plugin" e
"navigator_plugin", ids que nenhum plugin registrava: 4 dos 5 itens (e
Alt+B/C/L/N) não faziam nada. E a marca do item não acompanhava a gaveta.
"""
from ui.core.plugins.panel_ids import PANEL_TITLES, PanelId


def _docks(ws):
    return (ws.left_dock, ws.right_dock)


def _active(ws):
    return set().union(*(dock.active_panel_ids for dock in _docks(ws)))


def test_every_window_menu_item_opens_its_panel(qapp):
    from tests.main_window_fixture import main_window_com_workspace
    win = main_window_com_workspace()
    ws = win.workspace
    menu = win.menu_bar.window_menu
    registered = {pid for dock in _docks(ws) for pid, _title in dock.panel_titles()}
    for panel_id in PANEL_TITLES:
        if panel_id not in registered:
            continue
        action = menu._panel_actions[str(panel_id)]
        action.trigger()
        qapp.processEvents()
        assert panel_id in _active(ws), f"menu Janela não abriu {panel_id}"
        assert action.isChecked()
        action.trigger()
        qapp.processEvents()
        assert panel_id not in _active(ws)
        assert not action.isChecked()


def test_menu_mark_follows_panel_opened_from_the_sidebar(qapp):
    from tests.main_window_fixture import main_window_com_workspace
    win = main_window_com_workspace()
    ws = win.workspace
    action = win.menu_bar.window_menu._panel_actions[str(PanelId.LAYERS)]
    ws.right_dock.toggle_panel(PanelId.LAYERS)
    qapp.processEvents()
    assert action.isChecked()
    ws.right_dock.close_drawer()
    qapp.processEvents()
    assert not action.isChecked()


def test_panel_id_prints_as_its_value():
    assert str(PanelId.LAYERS) == "layers"
    assert f"{PanelId.BRUSH}" == "brush_settings"
    assert PanelId.NAVIGATOR == "navigator"
