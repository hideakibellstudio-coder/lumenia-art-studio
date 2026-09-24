"""New Document Dialog package."""
from .preset_catalog import PRESET_CATEGORIES, BACKGROUND_COLORS, PAPER_TEXTURES, COLOR_PROFILES, estimate_ram_usage_mb
from .preset_card import PresetCard

__all__ = [
    "PRESET_CATEGORIES",
    "BACKGROUND_COLORS",
    "PAPER_TEXTURES",
    "COLOR_PROFILES",
    "estimate_ram_usage_mb",
    "PresetCard",
]
