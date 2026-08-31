"""
ui.utils — Funções Utilitárias Puras da Camada de Apresentação (ARCcC).
======================================================================
Funções puras sem dependência de estado global ou referências a motores nativos.
"""

from __future__ import annotations
import math
from typing import Tuple


def clamp(val: float, min_val: float, max_val: float) -> float:
    """Restringe um valor numérico entre os limites especificados."""
    return max(min_val, min(val, max_val))


def lerp(a: float, b: float, t: float) -> float:
    """Interpolação linear entre a e b com fator t."""
    return a + (b - a) * t


__all__ = ["clamp", "lerp"]
