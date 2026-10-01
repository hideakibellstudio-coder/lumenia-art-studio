"""DocumentLoader — lê e decodifica um arquivo `.lmn` fora da thread da interface (S1.2).

Abrir tem duas metades, como salvar. A primeira (`load_document`) só lê o arquivo e decodifica os
blocos de tiles de cada camada em objetos do motor que não pertencem a nenhum documento: é onde
está quase todo o tempo (CRC, descompressão), e roda numa thread de fundo. A segunda,
`restore_document`, na thread da interface, cria as camadas, adota os pixels já decodificados
(tempo constante), aplica as propriedades e compõe uma vez.

Antes de 2026-10-01 tudo rodava na thread da interface: 2,0 s num 4K de dez camadas (0,06 s depois
do formato v3, mas 1,2 s quando todas as camadas estão pintadas).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from PySide6 import QtCore

from .background_queue import BackgroundQueue
from .schema import DocumentFormatError
from .serializer import DocumentSerializer


@dataclass(frozen=True)
class LoadedDocument:
    path: str
    manifest: dict[str, Any]
    payloads: dict[str, bytes]   # o que não é bloco de tiles já decodificado (v1/v2: RGBA cru; seleção; textura; ICC)
    prepared: dict[str, Any]     # nome do payload de tiles -> camada decodificada pelo motor


def load_document(path: str | Path, backend) -> LoadedDocument:
    """Lê, valida e decodifica. Roda em qualquer thread: só usa `backend.decode_layer_tiles`."""
    manifest, payloads = DocumentSerializer.read(path)
    prepared: dict[str, Any] = {}
    for record in manifest["layers"]:
        name = record.get("tiles_payload")
        if not name:
            continue
        try:
            prepared[name] = backend.decode_layer_tiles(manifest["width"], manifest["height"], payloads.pop(name))
        except ValueError as exc:
            raise DocumentFormatError(f"camada {record['uid']}: {exc}") from exc
    return LoadedDocument(str(path), manifest, payloads, prepared)


class DocumentLoader(QtCore.QObject):
    idle = QtCore.Signal()  # a fila esvaziou

    def __init__(self, parent: Optional[QtCore.QObject] = None, loader: Callable[..., LoadedDocument] = load_document) -> None:
        super().__init__(parent)
        self._loader = loader
        self._queue = BackgroundQueue(self)
        self._queue.idle.connect(self.idle)

    def submit(
        self,
        path: str,
        backend,
        on_done: Callable[[LoadedDocument], None],
        on_error: Callable[[str, Exception], None],
    ) -> None:
        """Enfileira a leitura de `path`. Os callbacks voltam na thread de quem chamou."""
        self._queue.submit(
            lambda: self._loader(path, backend),
            on_done=on_done,
            on_error=lambda exc: on_error(path, exc),
            label=f"leitura de '{path}'",
        )

    def is_busy(self) -> bool:
        return self._queue.is_busy()

    def wait_idle(self, timeout_ms: int = 120_000) -> bool:
        return self._queue.wait_idle(timeout_ms)
