"""LayerBlendMode -- enum canonico para o modo de mesclagem de camadas.

Espelha 1:1 `engine/core/document/blending/LayerBlendMode.hpp::LayerBlendMode`. O motor
(`engine/core/document/blending/BlendEquations.hpp`) implementa os 13 modos
por completo, incluindo ColorDodge/ColorBurn/Difference/Exclusion/Add, e o
binding pybind11 (`bridge/core/bindings/bind_math_brush.cpp`,
`py::enum_<document::LayerBlendMode>`) agora expõe os 13 (estendido na Fase
C5 -- antes só tinha Normal..Erase). Mesmo assim,
`PaintEngineFacade::setLayerBlendMode` recebe um `int` puro (ver `.pyi`:
`blend_mode_id: int`), não o enum nativo -- então este módulo continua
entregando um `int` (`int(LayerBlendMode.X)`) na fronteira com o motor,
nunca constrói `native.LayerBlendMode(...)`: mais simples, e imune a
qualquer binding futuro voltar a ficar incompleto. Achado e correção
registrados em `claude/verificacao-cruzada-planos-solidificacao.md` (Fase C5).

Antes desta classe, cada camada da pilha guardava sua própria tradução
string/int, e elas divergiam silenciosamente:

  - `local_layer.py` guardava o rótulo em português cru como valor
    (`"Atravessar"`/`"Normal"`).
  - `layer_manager.py::flatten_group` comparava contra quatro formas ao
    mesmo tempo: `("Atravessar", "PassThrough", "Pass-Through", 7)`.
  - `layers_plugin/header.py` populava o combo com uma lista própria de
    rótulos e um `legacy_map` para normalizar variantes antigas -- mas dois
    rótulos atuais (`"Multiplicar"`, `"Sobrepor"`) não batiam com nenhuma
    chave da tabela de conversão real, então selecioná-los na UI aplicava
    silenciosamente o modo Normal (bug confirmado, corrigido aqui).
  - `ui/core/dialogs/layer_properties_dialog.py` tinha sua PRÓPRIA tabela
    índice->rótulo, com só 8 entradas em ordem diferente da tabela real
    (`"Additive"` no índice 6, onde o motor tem Erase; `"Erase"` no índice
    7, onde o motor tem PassThrough) -- bug confirmado, corrigido aqui.
  - `ui/infrastructure/bridge_client/aladyn_layer_mixin.py` tinha a única tabela
    completa e correta (28 chaves EN+PT-BR -> os 13 índices certos), mas
    era a única fonte que sabia disso.

Este módulo consolida as cinco em uma só. Ver
`tests/test_layer_blend_mode_contract.py` para o teste de contrato contra o
módulo nativo compilado (limitado aos 7 valores que o binding expõe hoje).
"""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class LayerBlendMode(IntEnum):
    """Espelha `document::LayerBlendMode` (engine/core/document/blending/LayerBlendMode.hpp)."""

    NORMAL = 0
    MULTIPLY = 1
    SCREEN = 2
    OVERLAY = 3
    DARKEN = 4
    LIGHTEN = 5
    ERASE = 6
    PASS_THROUGH = 7
    COLOR_DODGE = 8
    COLOR_BURN = 9
    DIFFERENCE = 10
    EXCLUSION = 11
    ADD = 12

    @property
    def label(self) -> str:
        """Rótulo em português usado pelos combos da UI (fonte única)."""
        return _LABELS[self]

    @classmethod
    def from_label(cls, text: str) -> "LayerBlendMode":
        """Resolve um rótulo de UI (português atual, português legado, ou
        nome do enum nativo em inglês) para o modo canônico.

        Rótulo desconhecido cai em `NORMAL`, com um aviso logado -- nunca
        levanta, para não quebrar a UI por um typo num combo.
        """
        mode = _LABEL_TO_MODE.get(text)
        if mode is None:
            logger.warning("LayerBlendMode.from_label: rótulo desconhecido %r, usando NORMAL", text)
            return cls.NORMAL
        return mode

    @classmethod
    def coerce(cls, value: Any) -> "LayerBlendMode":
        """Normaliza qualquer forma histórica (enum, int, rótulo de string)
        para o modo canônico. Ponto único de entrada recomendado sempre que
        um `blend_mode` vem de fora (UI, documento carregado, motor)."""
        if isinstance(value, cls):
            return value
        if isinstance(value, bool):
            return cls.NORMAL
        if isinstance(value, int):
            try:
                return cls(value)
            except ValueError:
                logger.warning("LayerBlendMode.coerce: índice desconhecido %r, usando NORMAL", value)
                return cls.NORMAL
        if isinstance(value, str):
            return cls.from_label(value)
        return cls.NORMAL


# Rótulo em português exibido nos combos -- fonte única (layers_plugin/header.py
# e layer_properties_dialog.py derivam daqui em vez de manter listas próprias).
_LABELS = {
    LayerBlendMode.NORMAL: "Normal",
    LayerBlendMode.MULTIPLY: "Multiplicar",
    LayerBlendMode.SCREEN: "Divisão",
    LayerBlendMode.OVERLAY: "Sobrepor",
    LayerBlendMode.DARKEN: "Escurecer",
    LayerBlendMode.LIGHTEN: "Clarear",
    LayerBlendMode.ERASE: "Borracha",
    LayerBlendMode.PASS_THROUGH: "Atravessar",
    LayerBlendMode.COLOR_DODGE: "Subexposição",
    LayerBlendMode.COLOR_BURN: "Superexposição",
    LayerBlendMode.DIFFERENCE: "Diferença",
    LayerBlendMode.EXCLUSION: "Exclusão",
    LayerBlendMode.ADD: "Adicionar",
}

# Toda forma de string já observada no código ou em documentos salvos,
# apontando para o modo canônico. União de:
#   - nomes do enum nativo (bind_math_brush.cpp)
#   - a tabela de 28 chaves de aladyn_layer_mixin.py (a única completa e correta)
#   - os rótulos atuais de layers_plugin/header.py, incluindo os dois que
#     não batiam com nenhuma chave anterior ("Multiplicar", "Sobrepor")
#   - as variantes antigas do legacy_map de header.py
_LABEL_TO_MODE = {
    # Nomes nativos (inglês, PascalCase, como o enum C++/pybind expõe)
    "Normal": LayerBlendMode.NORMAL,
    "Multiply": LayerBlendMode.MULTIPLY,
    "Screen": LayerBlendMode.SCREEN,
    "Overlay": LayerBlendMode.OVERLAY,
    "Darken": LayerBlendMode.DARKEN,
    "Lighten": LayerBlendMode.LIGHTEN,
    "Erase": LayerBlendMode.ERASE,
    "PassThrough": LayerBlendMode.PASS_THROUGH,
    "Pass-Through": LayerBlendMode.PASS_THROUGH,
    "ColorDodge": LayerBlendMode.COLOR_DODGE,
    "Color Dodge": LayerBlendMode.COLOR_DODGE,
    "ColorBurn": LayerBlendMode.COLOR_BURN,
    "Color Burn": LayerBlendMode.COLOR_BURN,
    "Difference": LayerBlendMode.DIFFERENCE,
    "Exclusion": LayerBlendMode.EXCLUSION,
    "Add": LayerBlendMode.ADD,
    "Additive": LayerBlendMode.ADD,
    # Português -- rótulos atuais da UI (header.py._all_blend_modes)
    "Atravessar": LayerBlendMode.PASS_THROUGH,
    "Multiplicar": LayerBlendMode.MULTIPLY,
    "Divisão": LayerBlendMode.SCREEN,
    "Sobrepor": LayerBlendMode.OVERLAY,
    "Escurecer": LayerBlendMode.DARKEN,
    "Clarear": LayerBlendMode.LIGHTEN,
    "Subexposição": LayerBlendMode.COLOR_DODGE,
    "Superexposição": LayerBlendMode.COLOR_BURN,
    "Diferença": LayerBlendMode.DIFFERENCE,
    "Exclusão": LayerBlendMode.EXCLUSION,
    "Adicionar": LayerBlendMode.ADD,
    "Borracha": LayerBlendMode.ERASE,
    # Português -- variantes legadas (legacy_map antigo de header.py, e
    # rótulos usados em versões anteriores do diálogo de propriedades)
    "Multiplicação": LayerBlendMode.MULTIPLY,
    "Sobreposição": LayerBlendMode.OVERLAY,
    "Subexposição (Dodge)": LayerBlendMode.COLOR_DODGE,
    "Superexposição (Burn)": LayerBlendMode.COLOR_BURN,
    "Adicionar (Add)": LayerBlendMode.ADD,
}

# Ordem de exibição do combo de camadas (Atravessar logo após Normal --
# preserva o comportamento existente de layers_plugin/header.py, que insere
# essa opção dinamicamente só quando a camada ativa é um grupo).
DISPLAY_ORDER = (
    LayerBlendMode.NORMAL,
    LayerBlendMode.PASS_THROUGH,
    LayerBlendMode.MULTIPLY,
    LayerBlendMode.SCREEN,
    LayerBlendMode.OVERLAY,
    LayerBlendMode.DARKEN,
    LayerBlendMode.LIGHTEN,
    LayerBlendMode.COLOR_DODGE,
    LayerBlendMode.COLOR_BURN,
    LayerBlendMode.DIFFERENCE,
    LayerBlendMode.EXCLUSION,
    LayerBlendMode.ADD,
    LayerBlendMode.ERASE,
)
