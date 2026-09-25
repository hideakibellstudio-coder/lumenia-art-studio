"""Deterministic paths for source execution and a standalone Windows bundle."""

from __future__ import annotations

import os
from pathlib import Path
import sys

from ui.infrastructure.app_info import APP_NAME


def is_packaged() -> bool:
    """Return whether this module is running inside a frozen/compiled bundle."""
    return bool(getattr(sys, "frozen", False) or globals().get("__compiled__"))


def app_root() -> Path:
    """Return the repository root in development or the portable bundle root."""
    if is_packaged():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def writable_data_dir() -> Path:
    """Prefer portable data beside the executable, then fall back to APPDATA."""
    if not is_packaged():
        return app_root()
    portable = app_root() / "data"
    try:
        portable.mkdir(parents=True, exist_ok=True)
        probe = portable / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return portable
    except OSError:
        fallback = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
