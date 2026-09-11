"""
AladynColorMixin — Gerenciamento Atômico de Amostragem de Cor e Perfis ICC para o AladynBackend.
================================================================================================
Isola a amostragem de cores por Eyedropper (mesclado ou por camada) e os perfis de cor do motor C++.
"""

from __future__ import annotations
import logging

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
        profile_id = int(profile_id)
        available_ids = {int(profile["id"]) for profile in self.get_available_color_profiles()}
        if profile_id not in available_ids:
            raise ValueError("perfil de cor desconhecido")
        self._color_profile_id = profile_id
        if self._facade and hasattr(self._facade, "set_color_profile"):
            if self.get_color_profile() != int(profile_id):
                self._mark_document_dirty("color_profile")
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
        if self._facade and hasattr(self._facade, "get_available_color_profiles"):
            return [dict(profile) for profile in self._facade.get_available_color_profiles()]
        if self._native and hasattr(self._native, "get_available_color_profiles"):
            return self._native.get_available_color_profiles()
        return []

    def transform_rgba_for_profile(self, pixels: bytes, profile_id: int) -> bytes:
        """Aplica o transformador canônico do motor a uma prévia RGBA."""
        raw = bytes(pixels)
        if len(raw) % 4:
            raise ValueError("pixels RGBA devem ter grupos de quatro bytes")
        if self._facade and hasattr(self._facade, "transform_rgba_for_profile"):
            return bytes(self._facade.transform_rgba_for_profile(raw, int(profile_id)))
        if int(profile_id) != 0:
            raise RuntimeError("transformação de perfil indisponível sem o motor Aladyn")
        return raw
