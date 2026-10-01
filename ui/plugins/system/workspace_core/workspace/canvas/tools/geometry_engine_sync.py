"""geometry_engine_sync — guias e simetria do canvas → motor (escritor único).

Recebem o backend e o estado (não o controlador). Todos os métodos usados
estão no contrato `EngineBackend` (com implementação padrão segura); até
2026-09-24 cada um era conferido com `hasattr` antes de chamar.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Optional

from PySide6 import QtCore

from ui.core.engine.backend_protocols import GeometryProtocol
from ui.core.geometry.guide_type import GuideType
from ui.core.geometry.symmetry_mode import SymmetryMode

_SNAP_MODES = {"auto": 0, "v": 1, "h": 2, "d": 3}


def push_symmetry(backend: Optional[GeometryProtocol], sym: Mapping[str, Any]) -> None:
    if backend is None:
        return
    mode = sym["mode"]
    angle = math.pi / 2.0 if mode == "mirror_v" else (0.0 if mode == "mirror_h" else math.radians(sym["angle"]))
    backend.set_symmetry_config(
        int(SymmetryMode.from_key(mode)), sym["cx"], sym["cy"], angle,
        sym.get("segments", 6), sym.get("stop_at_center", False),
    )


def push_guides(backend: Optional[GeometryProtocol], guide: Mapping[str, Any]) -> None:
    if backend is None:
        return
    point = QtCore.QPointF
    p0, p1 = guide.get("p0", point(0, 0)), guide.get("p1", point(100, 100))
    p2, p3 = guide.get("p2", point(200, 200)), guide.get("p3", point(300, 300))
    vp_a, vp_b = guide.get("vpA", point(400, 300)), guide.get("vpB", point(-1000, 300))
    vp_c = guide.get("vpC", point(400, -2000))
    backend.set_guide_config(
        int(GuideType.from_key(guide["type"])), p0.x(), p0.y(), p1.x(), p1.y(), p2.x(), p2.y(), p3.x(), p3.y(),
        vp_a.x(), vp_a.y(), vp_b.x(), vp_b.y(), vp_c.x(), vp_c.y(),
        guide.get("cx", 400.0), guide.get("cy", 300.0),
        guide.get("fov", 130.0), guide.get("pitch", 0.0),
        guide.get("yaw", 0.0), guide.get("snap_radius", 32.0),
    )
    # Campos usados só pela grade curvilínea (Fase C2b).
    backend.set_curvilinear_guide_config(
        guide.get("base_radius", 400.0), guide.get("density", 30.0),
        guide.get("show_v", True), guide.get("show_h", True), guide.get("show_d", True),
        guide.get("show_ground", False), guide.get("show_ceiling", False),
        guide.get("show_ground_verticals", False), guide.get("show_ceiling_verticals", False),
        guide.get("show_straight_verticals", False),
        _SNAP_MODES.get(guide.get("snap_mode", "auto"), 0), guide.get("snap_sensitivity", 3.0),
    )
