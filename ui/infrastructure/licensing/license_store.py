"""The license token on disk (`license.lic` in the user's data folder).

Written atomically: a crash in the middle of a write never leaves half a license.
Knows nothing about what the token means; the engine judges it.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

LICENSE_FILE = "license.lic"


class LicenseStore:
    def __init__(self, directory: Path) -> None:
        self._path = directory / LICENSE_FILE

    @property
    def path(self) -> Path:
        return self._path

    def read(self) -> str:
        try:
            return self._path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return ""

    def write(self, token: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(prefix=".license.", dir=self._path.parent)
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(token.strip() + "\n")
            os.replace(temporary, self._path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def clear(self) -> None:
        self._path.unlink(missing_ok=True)
