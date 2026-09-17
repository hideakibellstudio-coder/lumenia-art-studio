"""Contrato dos enums canonicos de Simetria e Reguas -- o motor define, a
interface consome.

Mesmo racional de `test_brush_param_contract.py`: antes de `GuideType` e
`SymmetryMode` existirem (`ui/core/geometry/`), a correspondencia
string-de-UI -> int-do-motor vivia solta em dois dicts inline dentro de
`GeometryToolController` (`gmap`/`m_map`), sem nada comparando essa
correspondencia contra o modulo nativo compilado. Isto e' esse algo.
"""

from __future__ import annotations

import pytest

from ui.core.geometry.guide_type import GuideType
from ui.core.geometry.symmetry_mode import SymmetryMode

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)


@pytest.mark.parametrize("member", list(GuideType))
def test_guide_type_matches_native(member):
    native_member = getattr(native.GuideType, member.name.title().replace("_", ""), None)
    assert native_member is not None, f"native.GuideType não tem {member.name}"
    assert int(native_member) == int(member)


def test_guide_type_covers_every_native_member():
    native_names = set(native.GuideType.__members__)
    python_count = len(list(GuideType))
    assert len(native_names) == python_count, (
        f"native.GuideType tem {len(native_names)} membros, "
        f"GuideType (Python) tem {python_count} -- fora de sincronia"
    )


@pytest.mark.parametrize("member", list(SymmetryMode))
def test_symmetry_mode_matches_native(member):
    native_member = getattr(native.SymmetryMode, member.name.title().replace("_", ""), None)
    assert native_member is not None, f"native.SymmetryMode não tem {member.name}"
    assert int(native_member) == int(member)


def test_symmetry_mode_covers_every_native_member():
    native_names = set(native.SymmetryMode.__members__)
    python_count = len(list(SymmetryMode))
    assert len(native_names) == python_count, (
        f"native.SymmetryMode tem {len(native_names)} membros, "
        f"SymmetryMode (Python) tem {python_count} -- fora de sincronia"
    )


@pytest.mark.parametrize("key,expected", [
    ("none", GuideType.NONE), ("straight", GuideType.STRAIGHT),
    ("curve_ruler", GuideType.CURVE_RULER), ("curvilinear", GuideType.CURVILINEAR),
    ("one_point", GuideType.ONE_POINT), ("two_point", GuideType.TWO_POINT),
    ("three_point", GuideType.THREE_POINT), ("isometric", GuideType.ISOMETRIC),
])
def test_guide_type_from_key(key, expected):
    assert GuideType.from_key(key) == expected


def test_guide_type_from_key_unknown_falls_back_to_none():
    assert GuideType.from_key("nao-existe") == GuideType.NONE


@pytest.mark.parametrize("key,expected", [
    ("none", SymmetryMode.NONE), ("mirror", SymmetryMode.MIRROR),
    ("mirror_v", SymmetryMode.MIRROR), ("mirror_h", SymmetryMode.MIRROR),
    ("double_mirror", SymmetryMode.DOUBLE_MIRROR), ("radial", SymmetryMode.RADIAL),
    ("kaleidoscope", SymmetryMode.KALEIDOSCOPE),
])
def test_symmetry_mode_from_key(key, expected):
    assert SymmetryMode.from_key(key) == expected


def test_symmetry_mode_from_key_unknown_falls_back_to_none():
    assert SymmetryMode.from_key("nao-existe") == SymmetryMode.NONE
