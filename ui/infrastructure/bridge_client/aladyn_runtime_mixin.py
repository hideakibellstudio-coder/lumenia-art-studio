"""Serviços do processo no motor nativo: a licença e o minidump de queda.

São do usuário, não do documento: funções do módulo `aladyn_engine_native`, sem
facade. Sem motor carregado, a licença é "unsupported" e não há dump.
"""

from __future__ import annotations

from .aladyn_base import AladynBackendBase

UNSUPPORTED = {"state": "unsupported"}


class AladynRuntimeMixin(AladynBackendBase):
    def license_apply(self, token: str) -> dict[str, str]:
        if self._native is None:
            return dict(UNSUPPORTED)
        return dict(self._native.license_apply(str(token)))

    def license_status(self) -> dict[str, str]:
        if self._native is None:
            return dict(UNSUPPORTED)
        return dict(self._native.license_status())

    def license_clear(self) -> None:
        if self._native is not None:
            self._native.license_clear()

    def install_crash_handler(self, directory: str) -> bool:
        return bool(self._native is not None and self._native.install_crash_handler(str(directory)))

    def write_diagnostic_dump(self, path: str) -> bool:
        return bool(self._native is not None and self._native.write_diagnostic_dump(str(path)))
