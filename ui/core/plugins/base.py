from abc import ABC, abstractmethod
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget
from typing import Optional
from ui.core.plugins.metadata import PluginMetadata
from ui.core.plugins.context import PluginContext

class BasePlugin(ABC):
    """
    Interface/Classe abstrata unificada para todos os plugins do Lumenia.
    """
    def __init__(self):
        self.context: Optional[PluginContext] = None

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Retorna os metadados tipados e estruturados do plugin."""
        pass

    def is_system_plugin(self) -> bool:
        """
        Se True, o plugin é de uso estrutural do sistema:
        - Não pode ser desativado pelo usuário.
        - Se falhar na inicialização, interrompe o boot.
        """
        return False

    def get_priority(self) -> int:
        """Prioridade de carregamento (maior valor = inicializado primeiro)."""
        return 0

    def initialize(self, context: PluginContext):
        """Injeta o contexto do sistema e inicializa o plugin."""
        self.context = context

    def activate(self) -> None:
        """Acionado após inicialização bem-sucedida (registro de serviços)."""
        pass

    def deactivate(self) -> None:
        """Acionado no desligamento ou desativação do plugin (remoção de serviços)."""
        pass

    def shutdown(self) -> None:
        """Liberação final de recursos alocados pelo plugin."""
        pass

    def get_icon(self) -> QIcon:
        return QIcon()

    # UI Opcional para as configurações do plugin
    def has_settings_ui(self) -> bool:
        return False

    def open_settings_ui(self, parent_widget) -> None:
        pass


# ── Service Interfaces ──────────────────────────────────────────────

class BrushDynamicsService(ABC):
    @abstractmethod
    def process_stroke_point(self, x: float, y: float, pressure: float, timestamp: float) -> tuple[float, float, float]:
        """
        Recebe as coordenadas da tela e pressão brutas e retorna (x, y, pressão) modificados.
        Permite que plugins criem dinâmicas de pressão customizadas, estabilizadores ou snaps.
        """
        pass
