"""The brush-engine id is a canonical enum, not a number with a comment (S0.1, D1).

Until 2026-10-01 the pen's eraser tip called `set_engine_type(6)  # ...::Eraser`.
Id 6 is Smudge; Eraser is 3. Nothing could tell: the id travelled as a bare
number and the enumerator lived in a comment, and the test written for it
pinned the same wrong number. Same family as the layer blend modes, the guide
types and the symmetry modes, which are already canonical enums (Lei do Rio 4).

Two guards here:
  * the Python enum has exactly the members and values of the native one;
  * no module in `ui/` hands a literal number to the engine-type contract.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from ui.core.engine.engine_type import EngineType

ROOT = pathlib.Path(__file__).resolve().parents[1]
UI = ROOT / "ui"

# A literal id where an `EngineType` member belongs.
LITERAL_ENGINE_ID = (
    re.compile(r"set_engine_type\(\s*\d"),
    re.compile(r"engine_type\s*(?:==|!=)\s*\d"),
    re.compile(r"[\"']engine_type[\"']\s*:\s*\d"),
    re.compile(r"\.get\(\s*[\"']engine_type[\"']\s*,\s*\d"),
    re.compile(r"_engine_type\s*=\s*\d"),
)


def _camel(name: str) -> str:
    """OIL_IMPASTO -> OilImpasto, the spelling of the native enumerators."""
    return name.title().replace("_", "")


@pytest.fixture(scope="module")
def native_enum():
    native = pytest.importorskip(
        "aladyn_engine_native", reason="native module not built in this environment"
    )
    return native.EngineType


@pytest.mark.parametrize("member", list(EngineType), ids=lambda m: m.name)
def test_every_member_has_the_native_value(member, native_enum):
    native_member = getattr(native_enum, _camel(member.name), None)
    assert native_member is not None, f"native EngineType has no {_camel(member.name)}"
    assert int(native_member) == member.value, (
        f"{member.name} is {member.value} here and {int(native_member)} in the engine"
    )


def test_the_native_enum_has_no_member_missing_here(native_enum):
    native_names = {name for name in native_enum.__members__}
    python_names = {_camel(member.name) for member in EngineType}
    assert native_names == python_names, (
        f"engine ids without a Python member: {sorted(native_names - python_names)}; "
        f"Python members without an engine id: {sorted(python_names - native_names)}"
    )


def test_the_eraser_is_not_the_smudge():
    """The bug itself, as a test: they are different engines with different ids."""
    assert EngineType.ERASER != EngineType.SMUDGE
    assert (EngineType.ERASER, EngineType.SMUDGE) == (3, 6)


def _literal_engine_ids() -> list[str]:
    found = []
    for path in sorted(UI.rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            code = line.split("#", 1)[0]
            if any(pattern.search(code) for pattern in LITERAL_ENGINE_ID):
                found.append(f"{path.relative_to(ROOT).as_posix()}:{number}: {line.strip()}")
    return found


def test_no_module_in_the_ui_uses_a_literal_engine_id():
    found = _literal_engine_ids()
    assert not found, "use EngineType, not a number with a comment:\n  " + "\n  ".join(found)
