"""
ui.core.widgets.tool_options_widgets — Widgets de Configurações Específicas por Ferramenta
==========================================================================================
Re-exporta os painéis de propriedades específicos por ferramenta do pacote tool_options:
  - ToolHeaderLabel, ModernOptionCheckBox, ModernOptionSlider
  - Conta-Gotas (EyedropOptionsWidget)
  - Balde de Tinta (BucketOptionsWidget)
  - Varinha Mágica (WandOptionsWidget)
  - Transformações (TransformOptionsWidget)
  - Seleção (SelectionOptionsWidget)
  - Formas Vetoriais (ShapesOptionsWidget)
"""

from .tool_options.base import ToolHeaderLabel, ModernOptionCheckBox, ModernOptionSlider
from .tool_options.eyedrop_options import EyedropOptionsWidget
from .tool_options.bucket_wand_options import BucketOptionsWidget, WandOptionsWidget
from .tool_options.transform_selection_options import TransformOptionsWidget, SelectionOptionsWidget
from .tool_options.shapes_options import ShapesOptionsWidget

__all__ = [
    "ToolHeaderLabel",
    "ModernOptionCheckBox",
    "ModernOptionSlider",
    "EyedropOptionsWidget",
    "BucketOptionsWidget",
    "WandOptionsWidget",
    "TransformOptionsWidget",
    "SelectionOptionsWidget",
    "ShapesOptionsWidget",
]
