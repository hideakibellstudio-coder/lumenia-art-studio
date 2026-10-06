"""The 8-bit document keeps its bytes when the engine learns 16 bits per channel (S4).

A document now has a pixel format. The 16-bit one is a second path; the 8-bit one, which every
file the artist has already saved uses, must not change by a single byte. This pins the layer block
(`.lmn` tile data) of four synthetic canvases by length and SHA-256, taken from the engine before the
format existed, and the header bytes that tell the formats apart: the field that used to be reserved
(always 0) is now the pixel format id, 0 for 8 bits, so an old block is a valid new one.
"""

from __future__ import annotations

import hashlib
import struct

import numpy as np
import pytest

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

HEADER = struct.Struct("<4sHHIIII")
PIXEL_FORMAT_OFFSET = 20


def _content(seed: int, width: int, height: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 256, size=(height, width, 4), dtype=np.uint8)
    pixels[..., 3] = np.where(rng.random((height, width)) < 0.35, 0, pixels[..., 3])  # holes, some with colour under alpha 0
    pixels[: height // 3, : width // 2, 3] = 255  # an opaque block: the raw path on noise
    pixels[height // 2:, width // 3:, :3] = np.linspace(0, 255, width - width // 3, dtype=np.uint8)[None, :, None]  # smooth: LZ4
    return pixels


def _block(seed: int, width: int, height: int) -> bytes:
    engine = native.PaintEngineFacade(width, height)
    engine.paste_rgba_buffer_on_active_layer(0, 0, width, height, _content(seed, width, height).tobytes(), 0, 1.0)
    return engine.snapshot_layers().encode_layer(0)


# Taken from the engine at the end of S3, before PixelFormat existed.
PINNED = [
    (1, 301, 203, 215295, "aa4801402a628af3f43689284d956db62edf49f45215b4c45100fbb33a3c1ec5"),
    (2, 128, 128, 57507, "269fb1f7d315efe88ad7948099e48b5d34d0ee9f80e3e669d6af1d8e0cf7a23a"),
    (3, 640, 130, 292884, "c2b4c20fb1550d82ea969ce77496fd8ec45c99a14ad07d8dceeda1957e1b0784"),
    (4, 129, 1, 778, "094e2ecd15cec935e10df690ba42d1411f70db78513ae1c8f58719adf9c12031"),
]


@pytest.mark.parametrize(("seed", "width", "height", "length", "digest"), PINNED)
def test_an_8bit_layer_block_is_byte_identical_to_the_one_before_16_bits(seed, width, height, length, digest):
    blob = _block(seed, width, height)
    assert len(blob) == length
    assert hashlib.sha256(blob).hexdigest() == digest


def test_an_8bit_block_names_its_format_in_the_field_that_used_to_be_reserved():
    blob = _block(2, 128, 128)
    assert struct.unpack_from("<I", blob, PIXEL_FORMAT_OFFSET)[0] == 0
    magic, version, tile_size, width, height, _count, pixel_format = HEADER.unpack_from(blob, 0)
    assert (magic, version, tile_size, width, height, pixel_format) == (b"LMNT", 1, 128, 128, 128, 0)


def test_a_block_with_the_8bit_id_is_read_back_pixel_for_pixel():
    pixels = _content(7, 200, 150)
    source = native.PaintEngineFacade(200, 150)
    source.paste_rgba_buffer_on_active_layer(0, 0, 200, 150, pixels.tobytes(), 0, 1.0)
    blob = source.snapshot_layers().encode_layer(0)

    target = native.PaintEngineFacade(200, 150)
    target.restore_layer_tiles(0, blob)
    restored = np.frombuffer(target.get_layer_pixel_buffer(0), dtype=np.uint8).reshape(150, 200, 4)
    visible = pixels[..., 3] != 0
    assert (restored[visible] == pixels[visible]).all()
    assert (restored[~visible][:, 3] == 0).all()


def test_a_16bit_block_is_refused_by_an_8bit_document_and_leaves_it_alone():
    engine = native.PaintEngineFacade(128, 128)
    engine.paste_rgba_buffer_on_active_layer(0, 0, 128, 128, _content(3, 128, 128).tobytes(), 0, 1.0)
    before = engine.get_layer_pixel_buffer(0)
    blob = bytearray(engine.snapshot_layers().encode_layer(0))
    struct.pack_into("<I", blob, PIXEL_FORMAT_OFFSET, 1)
    with pytest.raises(ValueError):
        engine.restore_layer_tiles(0, bytes(blob))
    assert engine.get_layer_pixel_buffer(0) == before
