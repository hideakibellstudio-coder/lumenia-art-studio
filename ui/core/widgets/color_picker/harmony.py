"""Harmonias de cor na roda (complementar, análogas, tríade...) -- 2026-09-23.

O painel se chamava "Cores & Harmonias" sem ter harmonia nenhuma. As regras
giram o matiz na mesma roda HSV que o painel desenha e mantêm saturação e
valor da cor base -- o artista escolhe a partir dali.
"""
from __future__ import annotations

from enum import StrEnum

from PySide6 import QtGui


class HarmonyRule(StrEnum):
    NONE = "none"
    COMPLEMENTARY = "complementary"
    ANALOGOUS = "analogous"
    TRIADIC = "triadic"
    SPLIT_COMPLEMENTARY = "split_complementary"
    SQUARE = "square"

    @classmethod
    def coerce(cls, value: object) -> "HarmonyRule":
        try:
            return cls(value)
        except ValueError:
            return cls.NONE


# Deslocamentos de matiz (graus) das cores parceiras; a base é sempre 0°.
_DESLOCAMENTOS: dict[HarmonyRule, tuple[int, ...]] = {
    HarmonyRule.NONE: (),
    HarmonyRule.COMPLEMENTARY: (180,),
    HarmonyRule.ANALOGOUS: (-30, 30),
    HarmonyRule.TRIADIC: (120, 240),
    HarmonyRule.SPLIT_COMPLEMENTARY: (150, 210),
    HarmonyRule.SQUARE: (90, 180, 270),
}


def harmony_hues(rule: HarmonyRule, hue: float) -> list[float]:
    """Matizes (0..1) das parceiras de `hue` segundo a regra."""
    return [(hue + graus / 360.0) % 1.0 for graus in _DESLOCAMENTOS[HarmonyRule.coerce(rule)]]


def harmony_colors(rule: HarmonyRule, hue: float, saturation: float, value: float) -> list[QtGui.QColor]:
    """Cores parceiras com a mesma saturação e valor da base."""
    return [QtGui.QColor.fromHsvF(h, saturation, value, 1.0) for h in harmony_hues(rule, hue)]
