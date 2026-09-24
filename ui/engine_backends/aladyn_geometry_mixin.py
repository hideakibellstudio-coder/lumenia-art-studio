"""AladynGeometryMixin — Integração com Guias, Réguas e Simetria C++ do ALADYN ENGINE."""

from __future__ import annotations
from typing import Any
from PySide6 import QtGui
from .native_fallback import nativo_tem


class AladynGeometryMixin:
    """Mixin com chamadas nativas de simetria, guias e snap de régua para AladynBackend."""

    def set_symmetry_config(
        self, mode: int, cx: float, cy: float, angle_rad: float, segments: int = 6, stop_at_center: bool = False
    ) -> None:
        """Configura a simetria ativa no motor nativo C++."""
        if self._facade:
            self._facade.set_symmetry_config(
                int(mode), float(cx), float(cy), float(angle_rad), int(segments), bool(stop_at_center)
            )

    def clear_symmetry(self) -> None:
        """Desativa a simetria ativa no motor C++."""
        if self._facade:
            self._facade.clear_symmetry()

    def set_guide_config(
        self, guide_type: int, p0x: float = 0.0, p0y: float = 0.0, p1x: float = 100.0, p1y: float = 100.0,
        p2x: float = 200.0, p2y: float = 200.0, p3x: float = 300.0, p3y: float = 300.0,
        vp_ax: float = 400.0, vp_ay: float = 300.0, vp_bx: float = -1000.0, vp_by: float = 300.0,
        vp_cx: float = 400.0, vp_cy: float = -2000.0, cx: float = 0.0, cy: float = 0.0,
        fov: float = 130.0, pitch: float = 0.0, yaw: float = 0.0, snap_radius: float = 32.0,
    ) -> None:
        """Configura a régua / guia de perspectiva no motor nativo C++."""
        if self._facade:
            self._facade.set_guide_config(
                int(guide_type), float(p0x), float(p0y), float(p1x), float(p1y),
                float(p2x), float(p2y), float(p3x), float(p3y),
                float(vp_ax), float(vp_ay), float(vp_bx), float(vp_by),
                float(vp_cx), float(vp_cy), float(cx), float(cy),
                float(fov), float(pitch), float(yaw), float(snap_radius)
            )

    def clear_guide(self) -> None:
        """Desativa as réguas ativas no motor C++."""
        if self._facade:
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
        if self._facade:
            res = self._facade.snap_point(float(raw_x), float(raw_y), float(last_x), float(last_y), bool(has_last))
            if res and len(res) >= 2:
                return (float(res[0]), float(res[1]))
        return (float(raw_x), float(raw_y))

    # ── Curvilinear (6P fisheye) — Fase C2b ─────────────────────────────
    # API sem estado: o motor não guarda curva travada nem ponto de início
    # de traço — quem chama (GeometryToolController) continua dono do ciclo
    # de vida da interação, exatamente como já faz hoje. Aqui só cruzamos a
    # fronteira PyBind11: cada curva vai e volta como um bloco de 11 doubles
    # (ver PaintEngineFacade::encodeCurvilinearCurve, do lado C++).

    def set_curvilinear_guide_config(
        self, base_radius: float = 400.0, density: float = 30.0,
        show_v: bool = True, show_h: bool = True, show_d: bool = True,
        show_ground: bool = False, show_ceiling: bool = False,
        show_ground_verticals: bool = False, show_ceiling_verticals: bool = False,
        show_straight_verticals: bool = False,
        snap_mode: int = 0, snap_sensitivity: float = 3.0,
    ) -> None:
        """Completa os campos de guia usados apenas pelo Curvilinear no motor C++."""
        if self._facade and nativo_tem(self._facade, "set_curvilinear_guide_config", "a grade curvilínea ignora densidade/raio/visibilidade"):
            self._facade.set_curvilinear_guide_config(
                float(base_radius), float(density),
                bool(show_v), bool(show_h), bool(show_d),
                bool(show_ground), bool(show_ceiling),
                bool(show_ground_verticals), bool(show_ceiling_verticals),
                bool(show_straight_verticals),
                int(snap_mode), float(snap_sensitivity),
            )

    def get_curvilinear_candidates(self, click_x: float, click_y: float) -> list[float]:
        """Curvas candidatas (V/H/D) passando por (click_x, click_y), vindas do motor C++."""
        if self._facade and nativo_tem(self._facade, "get_curvilinear_candidates", "o snap curvilíneo fica sem curvas candidatas"):
            res = self._facade.get_curvilinear_candidates(float(click_x), float(click_y))
            if res:
                return [float(v) for v in res]
        return []

    def snap_curvilinear(
        self, raw_x: float, raw_y: float, start_x: float, start_y: float,
        candidates: list[float], locked_index: int = -1,
        is_stroking: bool = False, zoom: float = 1.0,
    ) -> tuple[float, float, int]:
        """Snap curvilíneo sem estado via C++: devolve (x, y, novo_locked_index)."""
        if self._facade and nativo_tem(self._facade, "snap_curvilinear", "o traço não gruda na guia curvilínea"):
            res = self._facade.snap_curvilinear(
                float(raw_x), float(raw_y), float(start_x), float(start_y),
                list(candidates), int(locked_index), bool(is_stroking), float(zoom),
            )
            if res and len(res) >= 3:
                return (float(res[0]), float(res[1]), int(res[2]))
        return (float(raw_x), float(raw_y), -1)

    # ── Perspectiva (1P/2P/3P/Isometric) ─ Fase C3.1 ─────────────────────────
    # Porte fiel de snap_ray_perspective (geometry_snapping_engine.py) para o
    # motor C++, com o mesmo contrato sem-estado do Curvilinear acima:
    # has_locked_dir/locked_dir_x/y entram, novo estado sai.

    def snap_perspective(
        self, raw_x: float, raw_y: float, start_x: float, start_y: float,
        has_locked_dir: bool = False, locked_dir_x: float = 0.0, locked_dir_y: float = 0.0,
        zoom: float = 1.0,
    ) -> tuple[float, float, bool, float, float]:
        """Snap de perspectiva (1P/2P/3P/Isometric) sem estado via C++.

        Devolve (x, y, tem_trava, trava_x, trava_y) -- os 3 ultimos devem ser
        persistidos pelo chamador e devolvidos na proxima chamada.
        """
        if self._facade and nativo_tem(self._facade, "snap_perspective", "o traço não gruda na perspectiva"):
            res = self._facade.snap_perspective(
                float(raw_x), float(raw_y), float(start_x), float(start_y),
                bool(has_locked_dir), float(locked_dir_x), float(locked_dir_y), float(zoom),
            )
            if res and len(res) >= 5:
                return (float(res[0]), float(res[1]), bool(res[2]), float(res[3]), float(res[4]))
        return (float(raw_x), float(raw_y), False, 0.0, 0.0)
