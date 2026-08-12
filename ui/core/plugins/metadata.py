from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List

class PluginType(Enum):
    SYSTEM = auto()      # Plugins estruturais de infraestrutura
    UI = auto()          # Docks, painéis ou abas adicionais
    BRUSH = auto()       # Dinâmicas e pontas de pincel
    FILTER = auto()      # Processamento de imagem e filtros
    TOOL = auto()        # Ferramentas extras de pintura
    IO = auto()          # Importadores e exportadores de arquivos

@dataclass
class PluginMetadata:
    id: str
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType = PluginType.UI
    dependencies: List[str] = field(default_factory=list)
    icon: Optional[str] = None
