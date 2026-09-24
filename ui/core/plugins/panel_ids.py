"""PanelId — ids canônicos dos painéis de plugins (Lei do rio nº 4).

O id com que o plugin registra o painel (`WorkspaceService.add_panel`) é o
mesmo que o menu Janela pede e que as docas usam para traduzir o título. Até
2026-09-24 eram três listas de strings soltas que não batiam: o menu pedia
"brush_plugin", "color_plugin", "layers_plugin" e "navigator_plugin" (os
painéis eram "brush_settings", "color_wheel", "layers" e "navigator"), então
4 dos 5 itens do menu Janela e os atalhos Alt+B/C/L/N não faziam nada; e a
tradução do título da doca procurava "brush".
"""
from __future__ import annotations

from enum import Enum


class PanelId(str, Enum):
    BRUSH = "brush_settings"
    COLOR = "color_wheel"
    LAYERS = "layers"
    NAVIGATOR = "navigator"
    GEOMETRY = "geometry"
    TELEMETRY = "telemetry"
    RECORDING = "recording"

    def __str__(self) -> str:  # "layers", não "PanelId.LAYERS" (logs, mime, f-strings)
        return self.value


# Título traduzível de cada painel: (chave de tradução, texto padrão).
# Usado pelo menu Janela e pelas docas (tooltip e cabeçalho da gaveta).
PANEL_TITLES: dict[PanelId, tuple[str, str]] = {
    PanelId.BRUSH: ("menu.window.brush_panel", "Pincel & Ferramentas"),
    PanelId.COLOR: ("menu.window.color_wheel", "Cores & Harmonias"),
    PanelId.LAYERS: ("menu.window.layers_panel", "Camadas"),
    PanelId.NAVIGATOR: ("menu.window.navigator", "Navegador do Canvas"),
    PanelId.GEOMETRY: ("menu.window.geometry_guides", "Guias de Perspectiva"),
    PanelId.TELEMETRY: ("menu.window.telemetry_panel", "Painel de Telemetria"),
}
