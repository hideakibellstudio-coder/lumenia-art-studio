"""Persistence of the active document across the backend boundary (S1.2).

The snapshot that a background save reads, the restoration of a layer from a block of
tiles, and the batch that lets opening a file composite once instead of dozens of times.
"""
from __future__ import annotations

from typing import Any, Optional

from ui.core.engine.errors import EngineContextError

from .aladyn_base import AladynBackendBase


class AladynPersistenceMixin(AladynBackendBase):
    def snapshot_layers(self) -> Optional[Any]:
        return self._facade.snapshot_layers() if self._facade else None

    def restore_layer_tiles(self, index: int, data: bytes) -> None:
        if not self._facade:
            raise EngineContextError("sem documento ativo no motor para restaurar a camada")
        self._facade.restore_layer_tiles(int(index), bytes(data))

    def begin_batch(self) -> None:
        if self._facade:
            self._facade.begin_batch()

    def end_batch(self) -> None:
        if self._facade:
            self._facade.end_batch()
