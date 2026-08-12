"""
ui.core.engine — Contratos de Motor (Shell Engine-Agnóstica)
============================================================
Esta é a camada de contrato que desacopla a interface (casca) de QUALQUER
motor. A UI conversa exclusivamente com estas abstrações:

    EngineBackend  — contrato do motor (render, brush, viewport, dispatch)
    commands       — dataclasses puras dos comandos de traço/pincel
    EngineRegistry — registro do backend ativo (plugado por plugins de sistema)

Regra de dependência: módulos de motor (ex.: ui/engine_backends/*) implementam
EngineBackend e são registrados via EngineRegistry. A casca nunca importa um
motor concreto diretamente.
"""

from ui.core.engine.backend import EngineBackend, PointerEvent
from ui.core.engine.registry import EngineRegistry
from ui.core.engine.errors import (
    EngineUnavailableError,
    EngineNotInitializedError,
)

__all__ = [
    "EngineBackend",
    "PointerEvent",
    "EngineRegistry",
    "EngineUnavailableError",
    "EngineNotInitializedError",
]