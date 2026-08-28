"""AladynGeometryMixin — Integração com Guias, Réguas e Simetria C++ do ALADYN ENGINE."""

from __future__ import annotations
from typing import Any
from PySide6 import QtGui


class AladynGeometryMixin:
    """Mixin com chamadas nativas de simetria, guias e snap de régua para AladynBackend."""

    def set_symmetry_config(
        self, mode: int, cx: float, cy: float, angle_rad: float, segments: int = 6, stop_at_center: bool = False
    ) -> None:
        """Configura a simetria ativa no motor nativo C++."""
        if self._facade and hasattr(self._facade, "set_symmetry_config"):
            self._facade.set_symmetry_config(
                int(mode), float(cx), float(cy), float(angle_rad), int(segments), bool(stop_at_center)
            )

    def clear_symmetry(self) -> None:
        """Desativa a simetria ativa no motor C++."""
        if self._facade and hasattr(self._facade, "clear_symmetry"):
            self._facade.clear_symmetry()

    def set_guide_config(
        self, guide_type: int, p0x: float = 0.0, p0y: float = 0.0, p1x: float = 100.0, p1y: float = 100.0,
        p2x: float = 200.0, p2y: float = 200.0, p3x: float = 300.0, p3y: float = 300.0,
        vp_ax: float = 400.0, vp_ay: float = 300.0, vp_bx: float = -1000.0, vp_by: float = 300.0,
        vp_cx: float = 400.0, vp_cy: float = -2000.0, cx: float = 0.0, cy: float = 0.0,
        fov: float = 130.0, pitch: float = 0.0, yaw: float = 0.0, snap_radius: float = 32.0,
    ) -> None:
        """Configura a régua / guia de perspectiva no motor nativo C++."""
        if self._facade and hasattr(self._facade, "set_guide_config"):
            self._facade.set_guide_config(
                int(guide_type), float(p0x), float(p0y), float(p1x), float(p1y),
                float(p2x), float(p2y), float(p3x), float(p3y),
                float(vp_ax), float(vp_ay), float(vp_bx), float(vp_by),
                float(vp_cx), float(vp_cy), float(cx), float(cy),
                float(fov), float(pitch), float(yaw), float(snap_radius)
            )

    def clear_guide(self) -> None:
        """Desativa as réguas ativas no motor C++."""
        if self._facade and hasattr(self._facade, "clear_guide"):
            self._facade.clear_guide()

    def snap_point(
        self,
        raw_x: float,
        raw_y: float,
        last_x: float = 0.0,
        last_y: float = 0.0,
        has_last: bool = False,
    ) -> tuple[float, float]:
        """Calcula atração do cursor para réguas ativas via C++."""
        if self._facade and hasattr(self._facade, "snap_point"):
            res = self._facade.snap_point(float(raw_x), float(raw_y), float(last_x), float(last_y), bool(has_last))
            if res and len(res) >= 2:
                return (float(res[0]), float(res[1]))
        return (float(raw_x), float(raw_y))
