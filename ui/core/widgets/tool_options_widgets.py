"""
ui.core.widgets.tool_options_widgets — Widgets de Configurações Específicas por Ferramenta
==========================================================================================
Re-exporta os painéis de propriedades específicos por ferramenta do pacote tool_options:
  - ToolHeaderLabel, ModernOptionCheckBox
  - Conta-Gotas (EyedropOptionsWidget)
  - Balde de Tinta (BucketOptionsWidget)
  - Varinha Mágica (WandOptionsWidget)
  - Transformações (TransformOptionsWidget)
  - Seleção (SelectionOptionsWidget)
  - Formas Vetoriais (ShapesOptionsWidget)

Nota: Para sliders compactos use CompactSlider de plugins.ui.brush_plugin.compact_slider,
ou LabeledSlider de ui.core.widgets.slider.labeled_slider.
"""

from .tool_options.base import ToolHeaderLabel, ModernOptionCheckBox
from .tool_options.eyedrop_options import EyedropOptionsWidget
from .tool_options.bucket_wand_options import BucketOptionsWidget, WandOptionsWidget
from .tool_options.transform_selection_options import TransformOptionsWidget, SelectionOptionsWidget
from .tool_options.shapes_options import ShapesOptionsWidget

__all__ = [
    "ToolHeaderLabel",
    "ModernOptionCheckBox",
    "EyedropOptionsWidget",
    "BucketOptionsWidget",
    "WandOptionsWidget",
    "TransformOptionsWidget",
    "SelectionOptionsWidget",
    "ShapesOptionsWidget",
]
