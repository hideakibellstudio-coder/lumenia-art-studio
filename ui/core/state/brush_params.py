"""Parâmetros canônicos do pincel exibidos pela UI (Lei do Rio nº 4: enum, não string solta).

Cada parâmetro tem UM tipo e UM valor padrão. Os valores padrão são os mesmos
que os sliders do painel de pincel mostram ao abrir; o preset inicial
("Pincel Redondo") os sobrescreve logo no primeiro ciclo de eventos.

Unidades (as mesmas que o motor recebe em `EngineBackend.set_brush_*`):

- SIZE ............... pixels do documento
- OPACITY ............ 0.0 – 1.0
- PRESSURE ........... 0.0 – 1.0 (pressão manual usada sem tablet)
- PRESSURE_CURVE ..... expoente > 0 da curva de pressão (1.0 = linear)
- STABILIZER ......... 0.0 – 0.98
- SPACING ............ fração do diâmetro entre dabs
- CONTRAST ........... 0.1 – 3.0 (contraste do grão; ≤ 1.0 também vira dureza)
- MIN_DENSITY_ACTIVE . liga a densidade mínima por pressão
- MIN_DENSITY_VALUE .. 0.0 – 1.0
- INVERT_HEIGHT ...... inverte a topografia da textura do pincel
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Any


class BrushParam(str, Enum):
    SIZE = "size"
    OPACITY = "opacity"
    PRESSURE = "pressure"
    PRESSURE_CURVE = "pressure_curve"
    STABILIZER = "stabilizer"
    SPACING = "spacing"
    CONTRAST = "contrast"
    MIN_DENSITY_ACTIVE = "min_density_active"
    MIN_DENSITY_VALUE = "min_density_value"
    INVERT_HEIGHT = "invert_height"


BRUSH_PARAM_DEFAULTS: dict[BrushParam, float | bool] = {
    BrushParam.SIZE: 60.0,
    BrushParam.OPACITY: 1.0,
    BrushParam.PRESSURE: 0.5,
    BrushParam.PRESSURE_CURVE: 1.0,
    BrushParam.STABILIZER: 0.35,
    BrushParam.SPACING: 0.10,
    BrushParam.CONTRAST: 1.0,
    BrushParam.MIN_DENSITY_ACTIVE: False,
    BrushParam.MIN_DENSITY_VALUE: 0.0,
    BrushParam.INVERT_HEIGHT: False,
}

_BOOL_PARAMS = {BrushParam.MIN_DENSITY_ACTIVE, BrushParam.INVERT_HEIGHT}


def coerce_param(param: BrushParam, value: Any) -> float | bool:
    """Converte `value` para o tipo do parâmetro ou levanta ValueError.

    Não fixa faixas: quem limita a faixa é o widget que edita o valor (o mesmo
    comportamento de antes desta camada existir). Só recusa o que o motor
    nunca poderia receber: tipo errado, NaN e infinito.
    """
    if param in _BOOL_PARAMS:
        if not isinstance(value, bool):
            raise ValueError(f"{param.value} espera bool, recebeu {value!r}")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{param.value} espera número, recebeu {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{param.value} recebeu valor não finito: {value!r}")
    if param is BrushParam.PRESSURE_CURVE and number <= 0.0:
        raise ValueError("pressure_curve precisa ser positivo")
    return number


def quick_params_from_preset(data: dict) -> dict[BrushParam, float]:
    """Extrai de um preset os parâmetros que o painel mostra nos sliders rápidos.

    Mesmo mapeamento que o BrushSettingsPanel aplicava à mão antes de 2026-09-24
    (`_on_preset_changed`); agora vive num lugar só e é testado.
    """
    params: dict[BrushParam, float] = {}
    if "brush_size" in data:
        params[BrushParam.SIZE] = float(data["brush_size"])
    if "opacity" in data:
        params[BrushParam.OPACITY] = float(data["opacity"])
    if "stabilizer_weight" in data or "stabilizer" in data:
        params[BrushParam.STABILIZER] = float(data.get("stabilizer_weight", data.get("stabilizer", 0.35)))
    if "spacing_factor" in data:
        params[BrushParam.SPACING] = float(data["spacing_factor"])
    if "brush_grain_contrast" in data:
        params[BrushParam.CONTRAST] = float(data["brush_grain_contrast"])
    elif "hardness" in data:
        params[BrushParam.CONTRAST] = float(data["hardness"])
    return params
