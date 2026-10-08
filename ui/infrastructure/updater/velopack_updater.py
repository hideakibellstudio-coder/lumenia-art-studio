"""The only place that talks to Velopack: look for, download and apply an update.

Velopack installs the program per user (`%LocalAppData%\\Lumenia`, no UAC), keeps
the running version in `current\\`, downloads only the bytes that changed (delta
packages) and swaps the folder when the program closes, keeping the old version
if anything fails. In development, or in a copy not installed by Velopack, there
is nothing to update and `available` is False.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FoundUpdate:
    version: str
    notes_markdown: str
    handle: Any  # velopack.UpdateInfo: given back to download/apply, never read elsewhere


def _velopack() -> Any:
    try:
        import velopack
    except ImportError:
        return None
    return velopack


class VelopackUpdater:
    def __init__(self, repository_url: str, channel: str) -> None:
        self._repository_url = repository_url
        self._channel = channel
        self._manager: Any = None

    def _ensure_manager(self) -> Any:
        if self._manager is None:
            velopack = _velopack()
            if velopack is None:
                return None
            source = velopack.GithubSource(self._repository_url, None, self._channel != "stable")
            options = velopack.UpdateOptions(False, 10, self._channel)
            try:
                self._manager = velopack.UpdateManager(source, options)
            except Exception as exc:  # not installed by Velopack (development, portable copy)
                logger.info("Atualização indisponível nesta cópia: %s", exc)
                return None
        return self._manager

    @property
    def available(self) -> bool:
        return self._ensure_manager() is not None

    def current_version(self) -> str:
        manager = self._ensure_manager()
        return manager.get_current_version() if manager is not None else ""

    def check(self) -> Optional[FoundUpdate]:
        manager = self._ensure_manager()
        if manager is None:
            return None
        info = manager.check_for_updates()
        if not info:
            return None
        target = info.TargetFullRelease
        return FoundUpdate(version=target.Version, notes_markdown=target.NotesMarkdown or "", handle=info)

    def download(self, update: FoundUpdate, progress: Callable[[int], None] | None = None) -> None:
        manager = self._ensure_manager()
        if manager is not None:
            manager.download_updates(update.handle, progress)

    def apply_on_exit(self, update: FoundUpdate, restart: bool) -> None:
        """Velopack's updater waits for this process to end, swaps `current\\` and, if asked, starts
        the new version. Closing is the program's job (it asks about unsaved documents first)."""
        manager = self._ensure_manager()
        if manager is not None:
            manager.wait_exit_then_apply_updates(update.handle, True, restart)
