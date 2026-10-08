"""One-time import of the data the Alpha installer kept beside the executable.

Up to 0.2.0 an installed Lumenia wrote its plugins and logs to `<install>\\data`
(`%LOCALAPPDATA%\\Programs\\Lumenia` for a per-user install). Installed builds now
write to `%APPDATA%\\Lumenia` (`runtime_paths.writable_data_dir`). On the first
start, whatever exists in the old folder and not in the new one is copied over;
nothing is overwritten or deleted, and a marker keeps it from running twice.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

MARKER = ".legacy-data-imported"
logger = logging.getLogger(__name__)


def legacy_candidates(app_root: Path) -> list[Path]:
    """The `data` folders an older installer may have left behind."""
    candidates = [app_root / "data"]
    for variable, *parts in (("LOCALAPPDATA", "Programs", "Lumenia"), ("ProgramFiles", "Lumenia")):
        base = os.environ.get(variable)
        if base:
            candidates.append(Path(base).joinpath(*parts, "data"))
    return candidates


def import_legacy_data(target: Path, candidates: list[Path]) -> list[Path]:
    """Copies files missing in `target` from the first existing candidate; returns what was copied."""
    if (target / MARKER).exists():
        return []
    copied: list[Path] = []
    resolved_target = target.resolve()
    for source in candidates:
        if not source.is_dir() or source.resolve() == resolved_target:
            continue
        for item in sorted(source.rglob("*")):
            destination = target / item.relative_to(source)
            if item.is_file() and not destination.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination)
                copied.append(destination)
        logger.info("Dados da versão anterior importados de %s (%d arquivos).", source, len(copied))
        break
    target.mkdir(parents=True, exist_ok=True)
    (target / MARKER).write_text("ok\n", encoding="utf-8")
    return copied
