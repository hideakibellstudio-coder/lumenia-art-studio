"""
AladynColorMixin — Gerenciamento Atômico de Amostragem de Cor e Perfis ICC para o AladynBackend.
================================================================================================
Isola a amostragem de cores por Eyedropper (mesclado ou por camada) e os perfis de cor do motor C++.
"""

from __future__ import annotations
import logging
from ui.core.engine.color_profiles_catalog import get_default_color_profiles

logger = logging.getLogger(__name__)


class AladynColorMixin:
    """Mixin responsável pela amostragem de cores e perfis de cor no AladynBackend."""

    def pick_color_merged(self, x: int, y: int, sample_radius: int = 0) -> tuple:
        if self._facade and hasattr(self._facade, "pick_color_merged"):
            return self._facade.pick_color_merged(int(x), int(y), int(sample_radius))
        return (0, 0, 0, 0)

    def pick_color_layer(self, layer_index: int, x: int, y: int, sample_radius: int = 0) -> tuple:
        if self._facade and hasattr(self._facade, "pick_color_layer"):
            return self._facade.pick_color_layer(int(layer_index), int(x), int(y), int(sample_radius))
        return (0, 0, 0, 0)

    def set_color_profile(self, profile_id: int) -> None:
        self._color_profile_id = int(profile_id)
        if self._facade and hasattr(self._facade, "set_color_profile"):
            self._facade.set_color_profile(int(profile_id))

    def get_color_profile(self) -> int:
        if self._facade and hasattr(self._facade, "get_color_profile"):
            return self._facade.get_color_profile()
        return getattr(self, "_color_profile_id", 0)

    def get_color_profile_name(self, profile_id: int) -> str:
        profiles = self.get_available_color_profiles()
        for p in profiles:
            if p.get("id") == int(profile_id):
                return p.get("name", "Padrão (sRGB)")
        return "Padrão (sRGB)"

    def get_available_color_profiles(self) -> list[dict]:
        if self._native and hasattr(self._native, "get_available_color_profiles"):
            return self._native.get_available_color_profiles()
        return get_default_color_profiles()
