"""Contrato canônico e validação das opções expostas pelas ferramentas."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any

from PySide6.QtGui import QColor


Validator = Callable[[Any], Any | None]


def _bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _int_between(low: int, high: int) -> Validator:
    def validate(value: Any) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value if low <= value <= high else None

    return validate


def _choice(*values: int) -> Validator:
    allowed = set(values)

    def validate(value: Any) -> int | None:
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return value if value in allowed else None

    return validate


def _sample_size(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value if 0 < len(value) <= 80 else None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value if 0 < len(value) <= 255 else None


def _color(value: Any) -> QColor | None:
    if not isinstance(value, QColor) or not value.isValid():
        return None
    return QColor(value)


def _ratio(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) and 0.0 <= numeric <= 1.0 else None


# Every entry reflects a value actually consumed by its corresponding controller.
TOOL_SETTING_DEFAULTS: dict[str, dict[str, Any]] = {
    "bucket": {
        "tolerance": 20,
        "expand_px": 1,
        "contiguous": True,
        "sample_all": True,
    },
    "eyedrop": {
        "sample_size": "1x1 Ponto Único",
        "sample_radius": 0,
        "sample_all": True,
        "show_loupe": True,
    },
    "wand": {
        "tolerance": 20,
        "expand_px": 0,
        "contiguous": True,
        "aa": True,
        "sample_all": True,
        "mode": 0,
    },
    "rect_select": {"feather_px": 0, "aa": True, "mode": 0},
    "ellipse_select": {"feather_px": 0, "aa": True, "mode": 0},
    "lasso": {"lasso_type": "freehand", "feather_px": 0, "aa": True, "mode": 0},
    "transform": {"interp_mode": 2, "lock_aspect": False, "distort": False},
    "smudge": {"smudge_stretch": 0.8, "color_pickup": 0.7, "mix_ratio": 0.5},
    "shapes": {
        "shape_type": "shape_line",
        "draw_mode": "both",
        "stroke_width": 4,
        "stroke_color": QColor(0, 0, 0, 255),
        "fill_color": QColor(0, 0, 0, 255),
        "fill_opacity": 1.0,
        "corner_radius": 0,
        "polygon_sides": 5,
        "star_points": 5,
        "star_inner_ratio": 0.5,
    },
    "text": {
        "font_family": "Segoe UI",
        "font_size": 36,
        "bold": False,
        "italic": False,
        "underline": False,
        "align": "left",
        "color": QColor(0, 0, 0, 255),
    },
}


_TOOL_SETTING_VALIDATORS: dict[str, dict[str, Validator]] = {
    "bucket": {
        "tolerance": _int_between(0, 100),
        "expand_px": _int_between(-10, 10),
        "contiguous": _bool,
        "sample_all": _bool,
    },
    "eyedrop": {
        "sample_size": _sample_size,
        "sample_radius": _choice(0, 1, 2, 5),
        "sample_all": _bool,
        "show_loupe": _bool,
    },
    "wand": {
        "tolerance": _int_between(0, 100),
        "expand_px": _int_between(-10, 10),
        "contiguous": _bool,
        "aa": _bool,
        "sample_all": _bool,
        "mode": _choice(0, 1, 2, 3),
    },
    "rect_select": {"feather_px": _int_between(0, 50), "aa": _bool, "mode": _choice(0, 1, 2, 3)},
    "ellipse_select": {"feather_px": _int_between(0, 50), "aa": _bool, "mode": _choice(0, 1, 2, 3)},
    "lasso": {
        "lasso_type": lambda value: value if value in {"freehand", "polygonal"} else None,
        "feather_px": _int_between(0, 50),
        "aa": _bool,
        "mode": _choice(0, 1, 2, 3),
    },
    "transform": {"interp_mode": _choice(0, 1, 2), "lock_aspect": _bool, "distort": _bool},
    "smudge": {"smudge_stretch": _ratio, "color_pickup": _ratio, "mix_ratio": _ratio},
    "shapes": {
        "shape_type": lambda value: value if value in {
            "shape_line", "shape_rect", "shape_ellipse", "shape_polygon", "shape_star"
        } else None,
        "draw_mode": lambda value: value if value in {"both", "stroke", "fill"} else None,
        "stroke_width": _int_between(1, 100),
        "stroke_color": _color,
        "fill_color": _color,
        "fill_opacity": _ratio,
        "corner_radius": _int_between(0, 100),
        "polygon_sides": _int_between(3, 16),
        "star_points": _int_between(3, 16),
        "star_inner_ratio": _ratio,
    },
    "text": {
        "font_family": _text,
        "font_size": _int_between(6, 288),
        "bold": _bool,
        "italic": _bool,
        "underline": _bool,
        "align": lambda value: value if value in {"left", "center", "right"} else None,
        "color": _color,
    },
}


# Accept persisted events emitted by previous versions, but never propagate them.
_LEGACY_KEYS: dict[str, dict[str, str]] = {
    "bucket": {"expansion": "expand_px"},
    "rect_select": {"feather": "feather_px", "anti_alias": "aa"},
    "ellipse_select": {"feather": "feather_px", "anti_alias": "aa"},
    "lasso": {"feather": "feather_px", "anti_alias": "aa"},
}


def default_tool_settings(tool_id: str) -> dict[str, Any]:
    """Return an independent default mapping for a supported tool."""
    return {
        key: QColor(value) if isinstance(value, QColor) else value
        for key, value in TOOL_SETTING_DEFAULTS.get(tool_id, {}).items()
    }


def normalize_tool_settings(
    tool_id: str,
    updates: Mapping[str, Any] | None,
    current: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge valid updates into the canonical settings for ``tool_id``.

    Invalid values and unknown keys are ignored, preserving the current value or
    the declared default. This keeps UI events, restored state and programmatic
    calls within the exact ranges accepted by the tool controllers.
    """
    validators = _TOOL_SETTING_VALIDATORS.get(tool_id)
    if validators is None:
        return {}

    result = default_tool_settings(tool_id)
    for source in (current, updates):
        if not isinstance(source, Mapping):
            continue
        canonical = dict(source)
        for legacy, target in _LEGACY_KEYS.get(tool_id, {}).items():
            if legacy in canonical and target not in canonical:
                canonical[target] = canonical[legacy]
        for key, validate in validators.items():
            if key not in canonical:
                continue
            value = validate(canonical[key])
            if value is not None:
                result[key] = value
    return result


__all__ = ["TOOL_SETTING_DEFAULTS", "default_tool_settings", "normalize_tool_settings"]
