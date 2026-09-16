import math
from ui.core.plugins.base import BasePlugin, BrushDynamicsService
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.registry import ServiceRegistry

class RainbowDynamics(BasePlugin, BrushDynamicsService):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="rainbow_dynamics",
            name="Dinâmica de Ondas e Pressão",
            version="1.0.0",
            author="Lumenia Team",
            description=(
                "Modula o traço adicionando uma ondulação senoidal (onda) no eixo Y "
                "e oscila a pressão do pincel em tempo real usando o relógio do sistema."
            ),
            plugin_type=PluginType.BRUSH,
            dependencies=[]
        )

    def activate(self) -> None:
        # Acessa o logger criado dinamicamente pelo contexto para testes
        if self.context:
            logger = self.context.get_logger("rainbow_dynamics")
            logger.info("RainbowDynamics ativado com sucesso!")
        
        ServiceRegistry.instance().register_service(BrushDynamicsService, self)

    def deactivate(self) -> None:
        ServiceRegistry.instance().unregister_service(BrushDynamicsService, self)

    def process_stroke_point(self, x: float, y: float, pressure: float, timestamp: float) -> tuple[float, float, float]:
        t = timestamp if timestamp > 0 else (x * 0.01)
        wave = math.sin(t * 8.0) * 12.0
        modulated_pressure = 0.55 + math.sin(t * 12.0) * 0.45
        return x, y + wave, modulated_pressure
