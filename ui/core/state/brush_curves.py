"""Curvas Bézier do pincel: tipos canônicos (Lei do Rio nº 4: enum, não string solta).

Três curvas de quatro pontos de controle cada, em coordenadas normalizadas (0 a 1):
a pressão que dimensiona a ponta, a pressão que dá o fluxo e a velocidade que
dimensiona a ponta. O valor é do `BrushState`; só o `BrushEngineSync` o escreve no
motor (antes de 2026-10-01 a janela de curvas escrevia direto: um segundo escritor).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class BrushCurve(str, Enum):
    # O valor é o `curve_type` que o contrato do motor (`set_curve_control_points`) recebe.
    PRESSURE_SIZE = "pressure_size"
    PRESSURE_FLOW = "pressure_flow"
    VELOCITY_SIZE = "velocity_size"


LINEAR_POINTS: tuple[tuple[float, float], ...] = ((0.0, 0.0), (0.33, 0.33), (0.66, 0.66), (1.0, 1.0))


@dataclass(frozen=True)
class CurveSetting:
    """Os quatro pontos de controle e se a curva está ligada."""

    points: tuple[tuple[float, float], ...]
    enabled: bool

    def __post_init__(self) -> None:
        if len(self.points) != 4:
            raise ValueError(f"a curva precisa de 4 pontos de controle, recebeu {len(self.points)}")
        for x, y in self.points:
            if not (math.isfinite(x) and math.isfinite(y) and 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                raise ValueError(f"ponto de controle fora do quadrado unitário: {(x, y)!r}")


# O que a janela de curvas mostrava ao abrir: tamanho e fluxo ligados, velocidade desligada.
_DEFAULT_ENABLED = {
    BrushCurve.PRESSURE_SIZE: True,
    BrushCurve.PRESSURE_FLOW: True,
    BrushCurve.VELOCITY_SIZE: False,
}


def default_curve(curve: BrushCurve) -> CurveSetting:
    return CurveSetting(LINEAR_POINTS, _DEFAULT_ENABLED[BrushCurve(curve)])
