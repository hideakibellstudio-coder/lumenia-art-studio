"""
ui.core.engine.commands — Comandos de Motor como Dataclasses Puras
==================================================================
Substituem as classes PyO3 (ex.: `engine_core.DrawCommand`) como contratos
movimentados entre canvas, dispatcher e plugins.

Vantagens:
  - A casca e os plugins NÃO dependem de um binário de motor compilado;
  - Qualquer backend pode consumir os mesmos comandos;
  - Os nomes/atributos espelham exatamente o contrato original do PyO3 para
    facilitar a migração de backends (WGPU/Rust etc.).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DrawCommand:
    x: float
    y: float
    pressure: float
    timestamp: float


@dataclass(frozen=True)
class StartStrokeCommand:
    x: float
    y: float
    pressure: float


@dataclass(frozen=True)
class EndStrokeCommand:
    pass


@dataclass(frozen=True)
class ClearCommand:
    pass


@dataclass(frozen=True)
class SetBrushColorCommand:
    r: float
    g: float
    b: float


@dataclass(frozen=True)
class SetBrushSizeCommand:
    size: float


@dataclass(frozen=True)
class SetBrushOpacityCommand:
    opacity: float


@dataclass(frozen=True)
class SetBrushSpacingCommand:
    spacing: float


__all__ = [
    "DrawCommand",
    "StartStrokeCommand",
    "EndStrokeCommand",
    "ClearCommand",
    "SetBrushColorCommand",
    "SetBrushSizeCommand",
    "SetBrushOpacityCommand",
    "SetBrushSpacingCommand",
]