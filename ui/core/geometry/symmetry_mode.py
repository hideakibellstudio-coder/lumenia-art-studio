"""SymmetryMode -- enum canonico para o modo de simetria ativo.

Espelha 1:1 `engine/core/math/SymmetryEngine.hpp::SymmetryMode`, exposto ao
Python como `aladyn_engine_native.SymmetryMode` em
`bridge/core/bindings/bind_math_brush.cpp`.

O motor nativo nao distingue espelho vertical de horizontal -- ambos sao
`SymmetryMode::Mirror`, e a orientacao vem do angulo (`sym_state['angle']`,
convertido em `sync_symmetry_to_engine`: 90 graus para vertical, 0 para
horizontal). A UI, porem, oferece "Espelho Vertical" e "Espelho Horizontal"
como opcoes distintas no combo (ver `SYM_TYPES` em
`geometry_plugin/components/constants.py`), entao a chave de string continua
distinguindo `mirror_v`/`mirror_h` mesmo colapsando para o mesmo enum nativo.
`mirror` (sem sufixo) tambem existe como chave legada equivalente.

Antes desta classe essa correspondencia vivia solta em `m_map` (dict inline
dentro de `GeometryToolController.sync_symmetry_to_engine`, em
`geometry_tool_controller.py`) -- a unica conversao string->int que chegava
ao motor nativo para simetria. Ver `tests/test_canonical_enums_contract.py`
para o teste de contrato contra o modulo nativo compilado.
"""

from __future__ import annotations

from enum import IntEnum


class SymmetryMode(IntEnum):
    """Espelha `math::SymmetryMode` (engine/core/math/SymmetryEngine.hpp)."""

    NONE = 0
    MIRROR = 1
    DOUBLE_MIRROR = 2
    RADIAL = 3
    KALEIDOSCOPE = 4

    @classmethod
    def from_key(cls, key: str) -> "SymmetryMode":
        """Resolve a chave de string usada por `sym_state['mode']`.

        Chave desconhecida cai em `NONE` -- mesmo comportamento de
        fallback que o antigo `m_map.get(..., 0)` tinha.
        """
        return _KEY_TO_MODE.get(key, cls.NONE)


# Unica fonte de verdade para a correspondencia chave-de-UI <-> enum nativo.
# "mirror_v"/"mirror_h" colapsam para o mesmo MIRROR nativo (a orientacao e'
# resolvida separadamente, via angulo); "mirror" e' a chave legada
# equivalente sem orientacao explicita.
_KEY_TO_MODE = {
    "none": SymmetryMode.NONE,
    "mirror": SymmetryMode.MIRROR,
    "mirror_v": SymmetryMode.MIRROR,
    "mirror_h": SymmetryMode.MIRROR,
    "double_mirror": SymmetryMode.DOUBLE_MIRROR,
    "radial": SymmetryMode.RADIAL,
    "kaleidoscope": SymmetryMode.KALEIDOSCOPE,
}
