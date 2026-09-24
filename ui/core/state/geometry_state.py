"""GeometryState — guias e simetria do documento ativo, uma cópia só.

Editam: as alças do canvas, o menu (Grade, Réguas), o seletor do painel de
geometria e o diálogo avançado. Mostram: o canvas e o painel. Quem leva ao
motor e ao documento é o controlador de geometria do canvas (escritor único,
`GeometryToolController.sync_*_to_engine`).

Até 2026-09-24 o painel guardava uma cópia própria (`panel.state`) e a
empurrava inteira para o canvas a cada mudança. Medido: a simetria do
documento A vazava para o B ao escolher uma régua no B; o painel mostrava o
documento anterior; mudar os segmentos no diálogo desfazia o ângulo
arrastado no canvas; ângulo 0 no diálogo era ignorado.

`guide` e `symmetry` são `SyncedDict`: toda escrita emite o sinal
(`batch()`/`update()` emitem uma vez só).
"""
from __future__ import annotations

import copy
from typing import Any, Mapping

from PySide6 import QtCore

from ui.core.geometry.synced_dict import SyncedDict

# Campos da simetria editados pelo diálogo; `hidden` vale para guia e simetria.
SYMMETRY_FIELDS = frozenset({"segments", "angle", "stop_at_center", "locked"})
# Campos da aba de perspectiva curvilínea do diálogo.
CURVILINEAR_FIELDS = frozenset({
    "yaw", "pitch", "fov", "density", "aspect_ratio", "show_ring", "show_straight_verticals",
    "show_v", "show_vps", "show_h", "show_letterbox", "show_d", "show_cube", "show_ground",
    "show_ceiling", "show_ground_verticals", "show_ceiling_verticals",
})
# Modos com eixo livre: saindo de 0° vão para 90°.
_AXIS_MODES = frozenset({"mirror", "double_mirror", "radial", "kaleidoscope"})


def default_symmetry() -> dict[str, Any]:
    return {
        "mode": "none", "cx": 400.0, "cy": 300.0, "angle": 90.0,
        "segments": 6, "stop_at_center": False, "locked": False,
        "hidden": False, "snap_increment": 15,
    }


def default_guide() -> dict[str, Any]:
    point = QtCore.QPointF
    return {
        "type": "none",
        "p0": point(100, 300), "p1": point(700, 300),
        "p2": point(300, 150), "p3": point(500, 450),
        "vpA": point(100, 300), "vpB": point(700, 300), "vpC": point(400, 50),
        "cx": 400.0, "cy": 300.0, "base_radius": 350.0,
        "yaw": 0.0, "pitch": 0.0, "fov": 130.0, "density": 30.0,
        "show_ring": True, "show_v": True, "show_h": True, "show_d": True,
        "show_vps": False, "show_cube": False, "show_ground": False, "show_ground_verticals": False,
        "show_ceiling": False, "show_ceiling_verticals": False, "show_straight_verticals": False,
        "show_letterbox": False, "aspect_ratio": "16:9", "snap_mode": "auto",
        "hidden": False, "snap_radius": 32.0, "snap_dynamic": True, "show_hint": True,
        "snap_sensitivity": 3.0,
    }


class GeometryState(QtCore.QObject):
    guideChanged = QtCore.Signal()
    symmetryChanged = QtCore.Signal()

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.guide = SyncedDict(default_guide(), on_change=self.guideChanged.emit)
        self.symmetry = SyncedDict(default_symmetry(), on_change=self.symmetryChanged.emit)
        self._document_size = (800.0, 600.0)

    # ── Edição ────────────────────────────────────────────────────────────

    def set_guide_type(self, guide_type: str) -> None:
        if self.guide["type"] != guide_type:
            self.guide["type"] = guide_type

    def set_symmetry_mode(self, mode: str) -> None:
        """Espelho vertical fica em 90°, horizontal em 0°; modo de eixo livre sai de 0° para 90°."""
        changes: dict[str, Any] = {"mode": mode}
        if mode == "mirror_v":
            changes["angle"] = 90.0
        elif mode == "mirror_h":
            changes["angle"] = 0.0
        elif mode in _AXIS_MODES and self.symmetry["angle"] == 0.0:
            changes["angle"] = 90.0
        self._write(self.symmetry, changes)

    def apply_advanced(self, fields: Mapping[str, Any]) -> None:
        """Campos editados no diálogo avançado, cada um no seu dicionário.

        Editar a perspectiva sem régua liga a curvilínea; editar a simetria
        sem simetria liga a radial (o usuário mexeu numa aba que não teria
        efeito nenhum).
        """
        edited = set(fields)
        if edited & CURVILINEAR_FIELDS and self.guide["type"] == "none":
            self.set_guide_type("curvilinear")
        if edited & SYMMETRY_FIELDS and self.symmetry["mode"] == "none":
            self.set_symmetry_mode("radial")
        self._write(self.symmetry, {k: v for k, v in fields.items() if k in SYMMETRY_FIELDS or k == "hidden"})
        self._write(self.guide, {k: v for k, v in fields.items() if k not in SYMMETRY_FIELDS})

    def has_free_axis(self) -> bool:
        """Simetria com eixo de ângulo livre (o painel oferece "resetar ângulo")."""
        return self.symmetry["mode"] in _AXIS_MODES

    def fields(self) -> dict[str, Any]:
        """Visão plana (guia + campos de simetria) que o diálogo avançado mostra."""
        flat = dict(self.guide)
        flat.update({key: self.symmetry[key] for key in SYMMETRY_FIELDS})
        return flat

    # ── Posição no documento ──────────────────────────────────────────────

    def center_on_document(self, width: float, height: float) -> None:
        """Centro da simetria e das guias no meio do documento, proporcional ao tamanho."""
        self._center(width, height)
        self.symmetryChanged.emit()
        self.guideChanged.emit()

    def center_pivot(self) -> None:
        """"Centralizar pivô no canvas": o mesmo, no documento ativo."""
        self.center_on_document(*self._document_size)

    def load(self, width: float, height: float, guide: Mapping[str, Any], symmetry: Mapping[str, Any]) -> None:
        """Troca de documento: padrões, centro do documento e o que ele guardou.

        Começa dos padrões para campo omitido não vazar de outra aba.
        """
        self.guide.reset(default_guide(), sync=False)
        self.symmetry.reset(default_symmetry(), sync=False)
        self._center(width, height)
        self.guide.update(copy.deepcopy(dict(guide)), sync=False)
        self.symmetry.update(copy.deepcopy(dict(symmetry)), sync=False)
        self.guideChanged.emit()
        self.symmetryChanged.emit()

    def _center(self, width: float, height: float) -> None:
        w, h = max(1.0, float(width)), max(1.0, float(height))
        self._document_size = (w, h)
        cx, cy = w / 2.0, h / 2.0
        point = QtCore.QPointF
        self.symmetry.update({"cx": cx, "cy": cy}, sync=False)
        self.guide.update({
            "cx": cx, "cy": cy, "base_radius": min(w, h) * 0.42,
            "p0": point(cx - w * 0.35, cy), "p1": point(cx + w * 0.35, cy),
            "p2": point(cx - w * 0.15, cy - h * 0.18), "p3": point(cx + w * 0.15, cy - h * 0.18),
            "vpA": point(cx - w * 0.55, cy), "vpB": point(cx + w * 0.55, cy),
            "vpC": point(cx, cy - h * 0.65),
        }, sync=False)

    @staticmethod
    def _write(target: SyncedDict, changes: Mapping[str, Any]) -> None:
        """Escreve só o que mudou; nada mudou, nada emite."""
        changed = {k: v for k, v in changes.items() if target.get(k) != v}
        if changed:
            target.update(changed)
