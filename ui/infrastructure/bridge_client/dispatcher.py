"""
EngineDispatcher — Pipeline de Despacho Engine-Agnóstico
==========================================================
Processa o pipeline de dinâmicas (plugins BrushDynamicsService) e despacha o
comando final para o backend de motor ativo no EngineRegistry.

Sem backend registrado (casca pura / motor arquivado), os eventos são
descartados com log de debug — a interface segue 100% funcional.
"""

import logging

from ui.core.engine.registry import EngineRegistry
from ui.core.plugins.registry import ServiceRegistry
from ui.core.plugins.base import BrushDynamicsService
from ui.core.plugins.contracts import (
    DrawCommand, StartStrokeCommand, EndStrokeCommand, ClearCommand,
    SetBrushColorCommand, SetBrushSizeCommand, SetBrushOpacityCommand, SetBrushSpacingCommand
)

logger = logging.getLogger(__name__)


class EngineDispatcher:
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # Nenhum motor concreto aqui — o despacho vai para o EngineRegistry.
        self._backend = None

    @property
    def backend(self):
        if self._backend is None:
            self._backend = EngineRegistry.instance().get_backend()
        return self._backend

    def dispatch(self, event):
        modified_event = event

        # 1. Processa dinâmicas através dos plugins ativos
        if isinstance(event, DrawCommand):
            x, y, pressure = event.x, event.y, event.pressure
            dynamics_services = ServiceRegistry.instance().get_services(BrushDynamicsService)
            for service in dynamics_services:
                try:
                    x, y, pressure = service.process_stroke_point(x, y, pressure, event.timestamp)
                except Exception as e:
                    logger.error(f"Erro no plugin de dinâmica ao processar ponto: {e}")
            modified_event = DrawCommand(x=x, y=y, pressure=pressure, timestamp=event.timestamp)

        elif isinstance(event, StartStrokeCommand):
            x, y, pressure = event.x, event.y, event.pressure
            dynamics_services = ServiceRegistry.instance().get_services(BrushDynamicsService)
            for service in dynamics_services:
                try:
                    x, y, pressure = service.process_stroke_point(x, y, pressure, 0.0)
                except Exception as e:
                    logger.error(f"Erro no plugin de dinâmica no início do traço: {e}")
            modified_event = StartStrokeCommand(x=x, y=y, pressure=pressure)

        # 2. Despacha o evento para o backend de motor ativo (assíncrono no backend)
        backend = self.backend
        if backend is None:
            logger.debug("[EngineDispatcher] Sem backend de motor — evento descartado (casca pura).")
            return

        try:
            backend.dispatch(modified_event)
        except Exception as e:
            logger.error(f"Erro ao despachar evento para o motor: {e}")
