"""Deterministic paths for source execution and a standalone Windows bundle.

Installed builds keep the user's data (logs, plugins, crash reports) in
`%APPDATA%\\Lumenia`, outside the program folder. Until 2026-10-08 they kept it in
`data\\` beside the executable; with updates delivered by Velopack that folder is
`current\\`, replaced on every update, so the data would vanish with each version.
A portable copy (a `portable.flag` file beside the executable, or one level up)
still keeps its data beside itself, so it travels on a USB stick.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

from ui.infrastructure.app_info import APP_NAME

PORTABLE_MARKER = "portable.flag"


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


def is_portable() -> bool:
    """A packaged copy the user marked as portable (its data stays beside the executable)."""
    root = app_root()
    return is_packaged() and ((root / PORTABLE_MARKER).is_file() or (root.parent / PORTABLE_MARKER).is_file())


def user_data_dir() -> Path:
    """`%APPDATA%\\Lumenia` (the same folder as config.json); `~/Lumenia` without APPDATA."""
    return Path(os.environ.get("APPDATA", Path.home())) / APP_NAME


def writable_data_dir() -> Path:
    """Where the program writes: the repository in development, beside the executable when
    portable, the user's data folder when installed."""
    if not is_packaged():
        return app_root()
    target = app_root() / "data" if is_portable() else user_data_dir()
    target.mkdir(parents=True, exist_ok=True)
    return target
