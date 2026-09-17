"""GuideType -- enum canonico para o tipo de regua/guia ativa.

Espelha 1:1 `engine/core/math/GuideSnapEngine.hpp::GuideType`, exposto ao
Python como `aladyn_engine_native.GuideType` em
`bridge/core/bindings/bind_math_brush.cpp`.

Antes desta classe, essa correspondencia vivia em duas listas mantidas a mao
que, por sorte, nunca divergiram, mas nada testava isso:

  - `gmap` (dict inline dentro de
    `GeometryToolController.sync_guides_to_engine`, em
    `geometry_tool_controller.py`) -- a UNICA conversao string->int que
    chegava ao motor nativo.
  - `GUIDE_TYPES` (`geometry_plugin/components/constants.py`) -- a lista que
    a UI usa para popular o combo de reguas.

Este modulo passa a ser a fonte unica: `GUIDE_TYPES` deriva de `GuideType` em
vez de duplicar a lista, e `sync_guides_to_engine` usa `GuideType.from_key`
em vez do dict solto. Ver `tests/test_canonical_enums_contract.py` para o
teste de contrato contra o modulo nativo compilado.
"""

from __future__ import annotations

from enum import IntEnum


class GuideType(IntEnum):
    """Espelha `math::GuideType` (engine/core/math/GuideSnapEngine.hpp)."""

    NONE = 0
    STRAIGHT = 1
    CURVE_RULER = 2
    CURVILINEAR = 3
    ONE_POINT = 4
    TWO_POINT = 5
    THREE_POINT = 6
    ISOMETRIC = 7

    @classmethod
    def from_key(cls, key: str) -> "GuideType":
        """Resolve a chave de string usada por `guide_state['type']`.

        Chave desconhecida cai em `NONE` -- mesmo comportamento de
        fallback que o antigo `gmap.get(..., 0)` tinha.
        """
        return _KEY_TO_TYPE.get(key, cls.NONE)

    @property
    def key(self) -> str:
        """A chave de string canonica usada por `guide_state['type']`."""
        return _TYPE_TO_KEY[self]


# Unica fonte de verdade para a correspondencia chave-de-UI <-> enum nativo.
_KEY_TO_TYPE = {
    "none": GuideType.NONE,
    "straight": GuideType.STRAIGHT,
    "curve_ruler": GuideType.CURVE_RULER,
    "curvilinear": GuideType.CURVILINEAR,
    "one_point": GuideType.ONE_POINT,
    "two_point": GuideType.TWO_POINT,
    "three_point": GuideType.THREE_POINT,
    "isometric": GuideType.ISOMETRIC,
}
_TYPE_TO_KEY = {v: k for k, v in _KEY_TO_TYPE.items()}

# Ordem estavel (mesma do enum nativo) para quem precisa iterar por indice,
# ex.: `GUIDE_TYPES = [t.key for t in GUIDE_TYPE_ORDER]` em constants.py.
GUIDE_TYPE_ORDER = tuple(GuideType)
