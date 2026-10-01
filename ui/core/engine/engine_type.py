"""EngineType -- the canonical id of a brush engine.

Mirrors `aladyn::engine::brush::EngineType`
(engine/core/brush/BrushProfile.hpp). Until 2026-10-01 these ids travelled as
bare numbers with the enumerator in a comment: the pen's eraser tip asked for id
6 ("Eraser" said the comment) and got Smudge, because Eraser is 3. A literal
cannot be wrong in a way anyone sees; a member name can only be right or missing.

The contract with the native enum (same members, same values) is
`tests/test_engine_type_contract.py`, which also bars a numeric literal in `ui/`.
"""

from enum import IntEnum


class EngineType(IntEnum):
    BRUSH = 0
    PENCIL = 1
    INKER = 2
    ERASER = 3
    MARKER = 4
    BLUR = 5
    SMUDGE = 6
    WATERCOLOR = 7
    OIL_IMPASTO = 8
