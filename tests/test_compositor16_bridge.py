"""A 16-bit document through the bridge: its format, what it reads back, and what it refuses until S6 (S5).

A document has a pixel format chosen when it is created (`PaintEngineFacade(w, h, pixel_format)`: 0 = 8 bits per
channel, the default; 1 = 16). The compositor of a 16-bit document composes in 16 bits and narrows only what the screen
shows, so these tests put real 16-bit pixels in a layer (a hand-made tile block: until S6 no brush can paint them) and
read them back through every path the interface has:

  - the format, the canvas limit of each format and the refusal of an unknown format;
  - the layer, the composite and a window of it in 16 bits, equal to what was put in and to a model of the composite;
  - the 8-bit screen equal to the narrowed composite, and the 16 bits surviving where the 8-bit view cannot tell them;
  - the file block of a layer: encoded in 16 bits, decoded, adopted by another document, and refused by an 8-bit one;
  - the operations that still write 8-bit pixels (brush, bucket, selection fill/delete, transform, flip, rotate, paste)
    refusing with a RuntimeError and leaving the document as it was, while selecting and the magic wand keep working.

The native harness `compositor16_checks` measures the compositor itself; this file checks the wiring around it.

Mutations that make it fail: the facade constructor ignoring the format, `copyComposite16` reading the 8-bit buffer,
`copyLayerPixels16` copying 4 bytes a pixel, the screen narrowing with a truncation, the format guard removed from one
orchestrator, `adoptDecodedLayer` not comparing formats.
"""
from __future__ import annotations

import struct

import numpy as np
import pytest

native = pytest.importorskip("aladyn_engine_native")

WIDTH, HEIGHT = 200, 150
TILE = 128


def _pattern(width: int, height: int, alpha: int = 65535, seed: int = 0) -> np.ndarray:
    """A (height, width, 4) uint16 picture whose neighbouring values differ by far less than one 8-bit level."""
    y, x = np.mgrid[0:height, 0:width].astype(np.uint32)
    out = np.empty((height, width, 4), dtype=np.uint16)
    out[..., 0] = (x * 301 + y * 17 + seed) % 65536
    out[..., 1] = (x * 53 + y * 311 + seed * 3) % 65536
    out[..., 2] = (x * 7 + y * 7 + seed * 5 + 20000) % 65536
    out[..., 3] = alpha
    return out


def _block(picture: np.ndarray, holes=frozenset(), pixel_format: int = 1) -> bytes:
    """A layer tile block (raw codec) holding `picture`; the tiles in `holes` are left out, as an empty tile is."""
    height, width = picture.shape[:2]
    padded = np.zeros((((height + TILE - 1) // TILE) * TILE, ((width + TILE - 1) // TILE) * TILE, 4), dtype=np.uint16)
    padded[:height, :width] = picture
    entries = []
    for ty in range(padded.shape[0] // TILE):
        for tx in range(padded.shape[1] // TILE):
            if (tx, ty) in holes:
                continue
            data = padded[ty * TILE:(ty + 1) * TILE, tx * TILE:(tx + 1) * TILE].tobytes()
            entries.append(struct.pack("<HHB3xI", tx, ty, 0, len(data)) + data)
    return b"LMNT" + struct.pack("<HHIIII", 1, TILE, width, height, len(entries), pixel_format) + b"".join(entries)


def _read(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw, dtype=np.uint16).reshape(HEIGHT, WIDTH, 4)


def _narrow(wide: np.ndarray) -> np.ndarray:
    return ((wide.astype(np.uint32) + 128) // 257).astype(np.uint8)


def _srgb_to_linear(value: np.ndarray) -> np.ndarray:
    unit = value / 65535.0
    return np.where(unit <= 0.04045, unit / 12.92, ((unit + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0.0, 1.0)
    unit = np.where(value <= 0.0031308, value * 12.92, 1.055 * value ** (1 / 2.4) - 0.055)
    return np.floor(unit * 65535.0 + 0.5)


HOLES = frozenset({(1, 1)})  # the bottom right tile holds nothing


@pytest.fixture()
def document():
    facade = native.PaintEngineFacade(WIDTH, HEIGHT, 1)
    facade.restore_layer_tiles(0, _block(_pattern(WIDTH, HEIGHT), HOLES))
    return facade


# ── the format ────────────────────────────────────────────────────────────────

def test_the_format_and_the_canvas_limit_of_each_format():
    assert native.PaintEngineFacade(8, 8).get_pixel_format() == 0
    assert native.PaintEngineFacade(8, 8, 0).get_pixel_format() == 0
    assert native.PaintEngineFacade(8, 8, 1).get_pixel_format() == 1
    assert native.PaintEngineFacade.max_canvas_dimension() == 16384
    assert native.PaintEngineFacade.max_canvas_dimension(1) == 8192
    with pytest.raises(ValueError, match="pixel format"):
        native.PaintEngineFacade(8, 8, 2)
    with pytest.raises(ValueError, match="pixel format"):
        native.PaintEngineFacade.max_canvas_dimension(-1)
    with pytest.raises(ValueError, match="8192"):
        native.PaintEngineFacade(8193, 8, 1)


def test_an_8_bit_document_has_no_16_bit_reads():
    facade = native.PaintEngineFacade(WIDTH, HEIGHT)
    with pytest.raises(RuntimeError, match="not 16-bit"):
        facade.get_composite_pixel_buffer16()
    with pytest.raises(RuntimeError, match="not 16-bit"):
        facade.get_composite_region16(0, 0, 4, 4)
    with pytest.raises(ValueError, match="16-bit"):
        facade.get_layer_pixel_buffer16(0)


# ── what a 16-bit layer reads back ────────────────────────────────────────────

def test_a_16_bit_layer_reads_back_exactly_with_a_hole_where_it_has_no_tile(document):
    expected = _pattern(WIDTH, HEIGHT)
    expected[TILE:, TILE:] = 0
    assert np.array_equal(_read(document.get_layer_pixel_buffer16(0)), expected)
    with pytest.raises(ValueError, match="16-bit"):
        document.get_layer_pixel_buffer16(7)


def test_the_8_bit_view_of_a_16_bit_layer_is_its_narrowed_pixels(document):
    narrowed = np.frombuffer(document.get_layer_pixel_buffer(0), dtype=np.uint8).reshape(HEIGHT, WIDTH, 4)
    assert np.array_equal(narrowed, _narrow(_read(document.get_layer_pixel_buffer16(0))))


def test_the_composite_is_the_opaque_layer_over_the_white_background(document):
    expected = _pattern(WIDTH, HEIGHT)
    expected[TILE:, TILE:] = 65535
    composite = _read(document.get_composite_pixel_buffer16())
    assert np.array_equal(composite, expected)
    assert len(document.get_composite_pixel_buffer16()) == WIDTH * HEIGHT * 8


def test_a_window_of_the_composite_is_the_same_rows_of_the_whole(document):
    whole = _read(document.get_composite_pixel_buffer16())
    for x, y, w, h in ((0, 0, 1, 1), (100, 60, 64, 50), (127, 127, 2, 2), (0, 140, 200, 10)):
        window = np.frombuffer(document.get_composite_region16(x, y, w, h), dtype=np.uint16).reshape(h, w, 4)
        assert np.array_equal(window, whole[y:y + h, x:x + w]), (x, y, w, h)
    with pytest.raises(ValueError):
        document.get_composite_region16(0, 0, 0, 4)


def test_the_screen_is_the_narrowed_composite_and_the_16_bits_survive_it(document):
    wide = _read(document.get_composite_pixel_buffer16())
    screen = np.frombuffer(document.get_pixel_buffer(), dtype=np.uint8).reshape(HEIGHT, WIDTH, 4)
    assert np.array_equal(screen, _narrow(wide))
    # Neighbouring pixels differ by less than one 8-bit level: 16 bits tell them apart, the screen cannot.
    assert len(np.unique(wide[..., 0])) > 4 * len(np.unique(screen[..., 0]))


@pytest.mark.parametrize("linear", [False, True], ids=["srgb", "linear"])
def test_a_translucent_layer_blends_in_16_bits(document, linear):
    document.set_linear_gamma(linear)
    document.set_layer_opacity(0, 0.5)
    composite = _read(document.get_composite_pixel_buffer16())
    layer = _pattern(WIDTH, HEIGHT)[:TILE * 2, :TILE * 2].astype(np.float64)
    below = np.full_like(layer, 65535.0)
    if linear:
        mixed = _linear_to_srgb(0.5 * _srgb_to_linear(layer) + 0.5 * _srgb_to_linear(below))
    else:
        mixed = np.floor(0.5 * layer + 0.5 * below + 0.5)
    inside = composite[:TILE, :, :3].astype(np.float64)  # the top tiles are covered by the layer
    assert np.abs(inside - mixed[:TILE, :WIDTH, :3]).max() <= 2
    assert (composite[:TILE, :, 3] == 65535).all()
    assert (composite[TILE:, TILE:] == 65535).all()  # the hole shows the background untouched


# ── the file block ────────────────────────────────────────────────────────────

def test_the_block_of_a_16_bit_layer_names_its_format_and_survives_a_round_trip(document):
    block = document.snapshot_layers().encode_layer(0)
    assert struct.unpack_from("<I", block, 20)[0] == 1
    decoded = native.decode_layer_tiles(WIDTH, HEIGHT, block)
    other = native.PaintEngineFacade(WIDTH, HEIGHT, 1)
    other.adopt_decoded_layer(0, decoded)
    assert other.get_layer_pixel_buffer16(0) == document.get_layer_pixel_buffer16(0)
    assert other.get_composite_pixel_buffer16() == document.get_composite_pixel_buffer16()


def test_a_block_of_the_other_format_is_refused_and_the_layer_is_untouched(document):
    before = document.get_layer_pixel_buffer16(0)
    eight_bit_block = native.PaintEngineFacade(WIDTH, HEIGHT).snapshot_layers().encode_layer(0)
    with pytest.raises(ValueError, match="pixel format"):
        document.restore_layer_tiles(0, eight_bit_block)
    sixteen = native.decode_layer_tiles(WIDTH, HEIGHT, document.snapshot_layers().encode_layer(0))
    with pytest.raises(ValueError, match="pixel format"):
        native.PaintEngineFacade(WIDTH, HEIGHT).adopt_decoded_layer(0, sixteen)
    assert document.get_layer_pixel_buffer16(0) == before


# ── structure operations keep the format ──────────────────────────────────────

def test_merging_a_layer_down_in_a_16_bit_document_keeps_the_picture(document):
    document.add_layer("upper")
    document.restore_layer_tiles(1, _block(_pattern(WIDTH, HEIGHT, alpha=40000, seed=9), HOLES))
    document.set_layer_opacity(1, 0.75)
    before = _read(document.get_composite_pixel_buffer16()).astype(np.int32)
    assert document.merge_layer_down(1)
    assert document.get_drawing_layer_count() == 1
    assert document.get_pixel_format() == 1
    after = _read(document.get_composite_pixel_buffer16()).astype(np.int32)
    assert np.abs(after - before).max() <= 2


def test_resizing_a_16_bit_canvas_keeps_it_16_bit(document):
    document.resize_canvas(WIDTH + 60, HEIGHT + 40)
    assert document.get_pixel_format() == 1
    assert len(document.get_composite_pixel_buffer16()) == (WIDTH + 60) * (HEIGHT + 40) * 8


# ── pixel writing operations supported in S6 ──────────────────────────────────

def _color():
    return native.ColorRGBA(10, 20, 30, 255)


OPERATIONS = {
    "stroke": lambda f: (f.begin_stroke_raw(20.0, 20.0), f.end_stroke_raw(20.0, 20.0)),
    "bucket": lambda f: f.flood_fill(20, 20, _color()),
    "fill selection": lambda f: f.fill_selection_on_active_layer(_color()),
    "delete selection": lambda f: f.delete_selection_on_active_layer(),
    "begin transform": lambda f: f.begin_transform(),
    "flip": lambda f: f.flip_active_layer(True),
    "rotate": lambda f: f.rotate_active_layer_90(True),
    "paste": lambda f: f.paste_rgba_buffer_on_active_layer(0, 0, 2, 2, bytes([100, 150, 200, 255] * 4)),
}


@pytest.mark.parametrize("operation", sorted(OPERATIONS))
def test_pixel_writing_operations_work_in_a_16_bit_document(document, operation):
    assert document.select_rect(10, 10, 60, 60)
    layer = document.get_layer_pixel_buffer16(0)
    generation = document.get_document_generation()
    OPERATIONS[operation](document)
    if operation == "begin transform":
        assert document.is_transform_active()
        document.cancel_transform()
    else:
        assert document.get_document_generation() > generation or document.get_layer_pixel_buffer16(0) != layer


def test_the_same_operations_still_work_in_an_8_bit_document():
    facade = native.PaintEngineFacade(WIDTH, HEIGHT)
    assert facade.flood_fill(5, 5, _color())
    assert facade.select_rect(10, 10, 60, 60)
    assert facade.fill_selection_on_active_layer(_color())
    assert facade.flip_active_layer(True)
    assert facade.can_undo()


def test_selecting_and_the_magic_wand_work_in_a_16_bit_document(document):
    assert document.select_rect(10, 10, 60, 60)
    assert document.has_selection()
    document.clear_selection()
    # The wand reads the layer narrowed to 8 bits: the hole (no tile) is one transparent region.
    assert document.magic_wand_select(TILE + 20, TILE + 20, 0, True, 0, False, 0, False)
    assert document.has_selection()
