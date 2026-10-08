"""The user's license during a session: applied to the engine, saved when accepted, announced.

The engine is the only judge (`engine/infrastructure/licensing/`). This service
hands it the saved token at start, saves a new token only when the engine
accepted it, and emits `statusChanged` so the views follow.
"""

from __future__ import annotations

import logging
from typing import Optional, Protocol

from PySide6 import QtCore

from ui.core.engine.backend_protocols import RoleProvider, RuntimeServicesProtocol
from ui.core.licensing.license_status import LicenseState, LicenseStatus

logger = logging.getLogger(__name__)


class TokenStore(Protocol):
    """Where the token lives between sessions (`ui.infrastructure.licensing.LicenseStore`)."""

    def read(self) -> str: ...
    def write(self, token: str) -> None: ...
    def clear(self) -> None: ...


class LicenseService(QtCore.QObject):
    statusChanged = QtCore.Signal(object)  # LicenseStatus

    def __init__(self, engine: RoleProvider[RuntimeServicesProtocol], store: TokenStore,
                 parent: Optional[QtCore.QObject] = None) -> None:
        super().__init__(parent)
        self._engine = engine
        self._store = store
        self._status = LicenseStatus()

    @property
    def status(self) -> LicenseStatus:
        return self._status

    def restore(self) -> LicenseStatus:
        """Applies the saved token. One the engine now refuses (expired, revoked, a build newer
        than its update period) stays on disk: the dialog shows why, and a renewal replaces it."""
        token = self._store.read()
        if not token:
            return self._status
        engine = self._engine()
        if engine is None:
            self._set(LicenseStatus(state=LicenseState.UNSUPPORTED))
            return self._status
        status = LicenseStatus.from_engine(engine.license_apply(token))
        if not status.is_licensed:
            logger.warning("Licença salva não aceita pelo motor: %s", status.state.value)
        self._set(status)
        return self._status

    def activate(self, token: str) -> LicenseStatus:
        """Gives `token` to the engine; saves it and switches the session only if it was accepted."""
        engine = self._engine()
        if engine is None:
            return LicenseStatus(state=LicenseState.UNSUPPORTED)
        status = LicenseStatus.from_engine(engine.license_apply(token.strip()))
        if status.is_licensed:
            self._store.write(token)
            self._set(status)
        return status

    def deactivate(self) -> None:
        self._store.clear()
        engine = self._engine()
        if engine is not None:
            engine.license_clear()
        self._set(LicenseStatus())

    def _set(self, status: LicenseStatus) -> None:
        if status != self._status:
            self._status = status
            self.statusChanged.emit(status)
