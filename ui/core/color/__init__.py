"""
ui.core.color — Subsistema de Gestão Profissional de Cor e LittleCMS.
=====================================================================
Fornece gerenciamento de perfis ICC, transformações colorimétricas LittleCMS,
simulação de prova de impressão (Soft-Proofing) e catálogo unificado de perfis.
"""

from .icc_profile import ICCProfileInfo
from .proofing import SoftProofConfig, RenderingIntent
from .cms_engine import ColorManagementEngine, get_cms_engine
from .catalog import ColorProfileCatalog, get_color_catalog

__all__ = [
    "ICCProfileInfo",
    "SoftProofConfig",
    "RenderingIntent",
    "ColorManagementEngine",
    "get_cms_engine",
    "ColorProfileCatalog",
    "get_color_catalog",
]
