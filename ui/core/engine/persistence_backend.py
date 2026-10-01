"""PersistenceBackend — o que gravar e abrir um documento pedem ao motor (S1.2).

Um contrato estreito, do tamanho do que `save_capture`, `restore` e `document_loader` usam, em
vez de mais seis métodos no `EngineBackend` (que já tem o tamanho da fachada do motor). Quem
implementa (`AladynBackend`) cumpre por estrutura; quem consome declara que precisa só disto.
"""
from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class PersistenceBackend(Protocol):
    def snapshot_layers(self) -> Optional[Any]:
        """As camadas do documento ativo congeladas (custa o número de tiles); legível de outra thread."""

    def restore_layer_tiles(self, index: int, data: bytes) -> None:
        """Troca os pixels da camada `index` do documento ativo por um bloco de tiles (ValueError se malformado)."""

    def decode_layer_tiles(self, width: int, height: int, data: bytes) -> Any:
        """Decodifica um bloco fora de qualquer documento, em qualquer thread; `adopt_decoded_layer` o usa."""

    def adopt_decoded_layer(self, index: int, decoded: Any) -> None:
        """Coloca na camada `index` do documento ativo os pixels já decodificados, em tempo constante."""

    def begin_batch(self) -> None:
        """Abre um lote: o canvas não é recomposto até o `end_batch` que o fecha."""

    def end_batch(self) -> None:
        """Fecha um lote; o último compõe uma vez."""
