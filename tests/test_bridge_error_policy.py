"""Política de erros da ponte (`bridge/infrastructure/README.md`).

O motor só lança `std::invalid_argument` para entrada inválida, e o pybind11 a
traduz para `ValueError`; buffer que não bate com as dimensões também é
`ValueError` (`BufferContract.hpp`). Os bindings não repetem a tradução com
`try/catch` — até 2026-09-25 `transform_rgba_for_profile` repetia.
"""
from __future__ import annotations

from pathlib import Path

import pytest

native = pytest.importorskip("aladyn_engine_native")
ROOT = Path(__file__).resolve().parents[1]


def test_invalid_input_from_the_engine_is_a_value_error():
    facade = native.PaintEngineFacade(16, 16)
    with pytest.raises(ValueError, match="multiple of four"):
        facade.transform_rgba_for_profile(b"abc", 0)


def test_buffer_that_does_not_match_the_raster_is_a_value_error():
    facade = native.PaintEngineFacade(16, 16)
    with pytest.raises(ValueError):
        facade.paste_rgba_buffer_on_active_layer(0, 0, 4, 4, b"\x00" * 10)


def test_bindings_do_not_translate_errors_by_hand():
    bindings = sorted((ROOT / "bridge" / "core" / "bindings").glob("*.cpp"))
    assert bindings
    offenders = [path.name for path in bindings if "catch (" in path.read_text(encoding="utf-8")]
    assert offenders == []
