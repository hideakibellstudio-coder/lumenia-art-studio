"""Serviços do processo no motor nativo: o minidump de queda.

São do usuário, não do documento: funções do módulo `aladyn_engine_native`, sem
facade. Sem motor carregado não há dump.
"""

from __future__ import annotations

from .aladyn_base import AladynBackendBase


class AladynRuntimeMixin(AladynBackendBase):
    def install_crash_handler(self, directory: str) -> bool:
        return bool(self._native is not None and self._native.install_crash_handler(str(directory)))

    def write_diagnostic_dump(self, path: str) -> bool:
        return bool(self._native is not None and self._native.write_diagnostic_dump(str(path)))
