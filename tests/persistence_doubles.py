"""Dublês da gravação: um motor que cumpre o que `capture_document` pede, sem o módulo nativo.

Até 2026-10-01 os testes de arquivo usavam um `_Backend` de duas linhas (um buffer RGBA fixo).
Desde o formato v3 a gravação lê um instantâneo das camadas (`snapshot_layers`) e a camada
vira um bloco de tiles; o dublê entrega blocos válidos e vazios (só o cabeçalho), o suficiente
para o leitor do arquivo, que valida a estrutura e não decodifica os tiles.
"""
from __future__ import annotations

import struct


def blank_tile_block(width: int, height: int) -> bytes:
    """Um bloco de tiles válido sem nenhum tile (engine/core/canvas/TileGridCodec.hpp)."""
    return struct.pack("<4sHHIIII", b"LMNT", 1, 128, width, height, 0, 0)


class SnapshotDouble:
    def __init__(self, raster: list[bool], width: int, height: int) -> None:
        self._raster, self._width, self._height = raster, width, height

    @property
    def layer_count(self) -> int:
        return len(self._raster)

    def has_pixels(self, index: int) -> bool:
        return 0 <= index < len(self._raster) and self._raster[index]

    def encode_layer(self, index: int) -> bytes:
        if not self.has_pixels(index):
            raise ValueError("layer has no pixels to encode")
        return blank_tile_block(self._width, self._height)


class BackendDouble:
    """O que a captura pergunta ao motor, respondido do próprio documento."""

    available = True

    def __init__(self, document) -> None:
        self._document = document

    def get_active_document_context(self) -> str:
        return self._document.uid

    def is_transform_active(self) -> bool:
        return False

    def snapshot_layers(self) -> SnapshotDouble:
        layers = self._document.layer_manager.layers
        return SnapshotDouble([not layer.is_group and not layer.is_filter for layer in layers],
                              self._document.width, self._document.height)

    def get_color_profile(self) -> int:
        return 0

    def get_active_profile_icc_bytes(self):
        return None

    def has_selection(self) -> bool:
        return False

    def get_selection_mask_buffer(self):
        return None

    def get_canvas_resource(self):
        return None

    def get_filter_type(self, _index: int) -> int:
        return -1

    def get_filter_params(self, _index: int) -> list[float]:
        return []
