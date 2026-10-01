"""
ui.core.document.local_layer — Modelo de Camada Local do Lumenia
================================================================
Representa uma camada, grupo ou camada de filtro dentro do LocalLayerManager.
"""

from __future__ import annotations

from PySide6 import QtGui

from ui.core.document.layer_blend_mode import LayerBlendMode
from ui.core.document import layer_properties
from ui.infrastructure.i18n import tr


def default_layer_name(number: int) -> str:
    """Nome de camada nova sem nome dado pelo usuário, no idioma atual ("Camada 3", "Layer 3")."""
    return tr("layers.default_name", "Camada {n}", n=number)


class LocalLayer:
    """Uma camada, grupo ou camada de filtro: propriedades e a última miniatura do motor."""

    visible: bool
    locked: bool
    opacity: float
    blend_mode: LayerBlendMode
    alpha_locked: bool
    clipping_mask: bool
    collapsed: bool

    def __init__(self, uid: int, name: str, parent_uid=None, is_group=False, is_filter=False):
        self.uid = uid
        self.id = uid  # Compatibilidade com camada.id
        self.name = name
        self.parent_uid = parent_uid
        self.is_group = is_group
        self.is_filter = is_filter

        # As propriedades vêm de LAYER_PROPERTIES (ui/core/document/layer_properties.py); as anotações
        # da classe existem para quem lê o código e para o editor.
        for prop in layer_properties.TABLE.all:
            if not prop.in_constructor:
                setattr(self, prop.name, prop.default_for(is_group))

        # Miniatura com os pixels reais, vinda do motor (quem pede é o painel de
        # camadas). Até 2026-09-24 o modelo pintava aqui um marcador com as cores
        # do tema lendo `ThemeManager._themes` (privado): aparência é da view,
        # e o delegate do painel já desenha grupo, filtro e camada sem miniatura.
        self.thumb: QtGui.QPixmap | None = None
