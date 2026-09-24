"""Telas de opções de ferramenta ligadas ao ToolState.

Porta de entrada da pasta:
- `ToolOptionsView`: base de toda tela de opções de ferramenta (aqui e na
  barra secundária do workspace). Contrato em `bound_view.py`.
- Páginas do painel de pincel: `EyedropOptionsWidget`, `BucketOptionsWidget`,
  `WandOptionsWidget`, `TransformOptionsWidget`, `SelectionOptionsWidget`,
  `ShapesOptionsWidget`.
- `SAMPLE_RADII`: raios de amostragem do conta-gotas, na ordem do combo.
- `ToolHeaderLabel`, `ModernOptionCheckBox`: peças visuais das páginas.
"""

from .base import ModernOptionCheckBox, ToolHeaderLabel
from .bound_view import ToolOptionsView
from .bucket_wand_options import BucketOptionsWidget, WandOptionsWidget
from .eyedrop_options import SAMPLE_RADII, EyedropOptionsWidget
from .shapes_options import ShapesOptionsWidget
from .transform_selection_options import SelectionOptionsWidget, TransformOptionsWidget

__all__ = [
    "SAMPLE_RADII",
    "BucketOptionsWidget",
    "EyedropOptionsWidget",
    "ModernOptionCheckBox",
    "SelectionOptionsWidget",
    "ShapesOptionsWidget",
    "ToolHeaderLabel",
    "ToolOptionsView",
    "TransformOptionsWidget",
    "WandOptionsWidget",
]
