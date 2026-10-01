from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List

class PluginType(Enum):
    """Tipos de plugin que o carregador sabe tratar. BRUSH, FILTER, TOOL e IO foram
    declarados sem ponto de extensão e saíram em 2026-10-01 (ARCcC 4.4.9: nada de
    mecanismo para possibilidade que não existe); entram junto da feature que os
    carregar de verdade (ferramenta, filtro ou formato feito por plugin)."""

    SYSTEM = auto()      # Plugins estruturais de infraestrutura
    UI = auto()          # Docks, painéis ou abas adicionais

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
