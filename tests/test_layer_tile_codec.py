"""A layer as a block of tiles: what the .lmn file stores, and what a background save reads (S1.2).

The editable document was a ZIP of full-canvas RGBA layers: 330 MB of raw pixels to deflate
for a 4K document with ten layers (2.1 s on the interface thread, 609 MB more memory), and
the same 330 MB read, pasted and compared on opening (2.1 s more). Now only the painted
tiles are stored, each in LZ4, and the save reads a copy-on-write snapshot, so it can run
on another thread while the artist keeps painting.

These tests pin the block's contract: it round-trips every visible pixel; it holds only
what is painted; a snapshot is not changed by what is painted afterwards, even from another
thread; and a block that is malformed is refused whole, never half-applied.
"""

from __future__ import annotations

import random
import struct
import threading

import numpy as np
import pytest

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

HEADER = struct.Struct("<4sHHIIII")
ENTRY = struct.Struct("<HHB3sI")
TILE_BYTES = 128 * 128 * 4


def _stroke(engine, rng: random.Random, kind: int = 2, size: float = 24.0, steps: int = 20) -> None:
    engine.set_engine_type(kind)
    profile = engine.get_brush_profile()
    profile.brush_size, profile.opacity, profile.hardness = size, 1.0, 0.4
    profile.base_color = native.ColorRGBA(rng.randrange(256), rng.randrange(256), rng.randrange(256), 255)
    width, height = engine.get_width(), engine.get_height()
    x, y = rng.uniform(0, width), rng.uniform(0, height)
    engine.begin_stroke_raw(x, y, 0.9)
    for step in range(1, steps):
        engine.update_stroke_raw(x + step * rng.uniform(-9, 14), y + step * rng.uniform(-9, 14), 0.9, step * 0.01)
    engine.end_stroke_raw()


def _painted(width=301, height=203, strokes=6, seed=1):
    engine = native.PaintEngineFacade(width, height)
    rng = random.Random(seed)
    for _ in range(strokes):
        _stroke(engine, rng)
    return engine


def _layer(engine, index=0) -> np.ndarray:
    return np.frombuffer(engine.get_layer_pixel_buffer(index), dtype=np.uint8).reshape(engine.get_height(), engine.get_width(), 4)


def _same_visible(a: np.ndarray, b: np.ndarray) -> bool:
    """Equal where it matters: the RGB of a fully transparent pixel is not data."""
    differs = (a != b).any(axis=2) & ~((a[:, :, 3] == 0) & (b[:, :, 3] == 0))
    return not bool(differs.any())


def _restored(blob: bytes, width: int, height: int) -> np.ndarray:
    target = native.PaintEngineFacade(width, height)
    target.restore_layer_tiles(0, blob)
    return _layer(target)


def _tile_count(blob: bytes) -> int:
    return HEADER.unpack_from(blob)[5]


# -- the round trip -------------------------------------------------------------

@pytest.mark.parametrize("width, height", [(301, 203), (128, 128), (129, 1), (1, 1), (640, 130)])
def test_every_visible_pixel_survives_the_block(width, height):
    engine = _painted(width, height, seed=width)
    blob = engine.snapshot_layers().encode_layer(0)
    assert _same_visible(_restored(blob, width, height), _layer(engine))


@pytest.mark.parametrize("kind", range(9))
def test_each_brush_engine_round_trips(kind):
    engine = native.PaintEngineFacade(260, 190)
    rng = random.Random(kind)
    engine.paste_rgba_buffer_on_active_layer(0, 0, 260, 190, bytes(
        b for _ in range(260 * 190) for b in (rng.randrange(256), rng.randrange(256), rng.randrange(256), 255)), 0, 1.0)
    _stroke(engine, rng, kind=kind)
    assert _same_visible(_restored(engine.snapshot_layers().encode_layer(0), 260, 190), _layer(engine))


def test_a_fully_opaque_noise_layer_comes_back_byte_for_byte():
    """The worst case for LZ4: nothing compresses, the raw codec takes over, and nothing is lost."""
    width, height = 300, 260
    rng = random.Random(9)
    noise = bytes(b for _ in range(width * height) for b in (rng.randrange(256), rng.randrange(256), rng.randrange(256), 255))
    engine = native.PaintEngineFacade(width, height)
    engine.paste_rgba_buffer_on_active_layer(0, 0, width, height, noise, 0, 1.0)
    blob = engine.snapshot_layers().encode_layer(0)
    assert _restored(blob, width, height).tobytes() == _layer(engine).tobytes()


def test_restoring_replaces_what_the_layer_had():
    engine = _painted(seed=2)
    blob = engine.snapshot_layers().encode_layer(0)
    target = _painted(seed=3)  # a different picture in the same layer
    target.restore_layer_tiles(0, blob)
    assert _same_visible(_layer(target), _layer(engine))


# -- what is stored ---------------------------------------------------------------

def test_only_the_painted_tiles_are_in_the_block():
    engine = native.PaintEngineFacade(1280, 1280)  # 10 x 10 tiles
    engine.set_engine_type(2)
    engine.get_brush_profile().brush_size = 10.0
    engine.begin_stroke_raw(20.0, 20.0, 0.9)
    engine.update_stroke_raw(40.0, 30.0, 0.9, 0.01)
    engine.end_stroke_raw()
    blob = engine.snapshot_layers().encode_layer(0)
    assert _tile_count(blob) == 1
    assert len(blob) < HEADER.size + ENTRY.size + TILE_BYTES // 4  # one tile, compressed: far from the 6.5 MB layer


def test_a_blank_layer_is_just_a_header():
    blob = native.PaintEngineFacade(4000, 3000).snapshot_layers().encode_layer(0)
    assert len(blob) == HEADER.size and _tile_count(blob) == 0


def test_the_tiles_are_in_order_and_the_block_ends_exactly_after_the_last_one():
    engine = _painted(640, 420, strokes=12, seed=5)
    blob = engine.snapshot_layers().encode_layer(0)
    count = _tile_count(blob)
    assert count > 3
    offset, previous = HEADER.size, -1
    for _ in range(count):
        tx, ty, codec, _reserved, stored = ENTRY.unpack_from(blob, offset)
        key = ty * 5 + tx  # 640 px = 5 tiles per row
        assert key > previous and codec in (0, 1)
        previous = key
        offset += ENTRY.size + stored
    assert offset == len(blob)


# -- the snapshot ---------------------------------------------------------------

def test_what_is_painted_after_the_snapshot_is_not_in_it():
    engine = _painted(seed=7)
    before = _layer(engine).copy()
    snapshot = engine.snapshot_layers()
    rng = random.Random(70)
    for _ in range(5):
        _stroke(engine, rng, size=40.0)
    engine.clear_layer(0)
    assert not _same_visible(_layer(engine), before), "the live layer must have changed for the test to mean anything"
    assert _same_visible(_restored(snapshot.encode_layer(0), 301, 203), before)


def test_a_snapshot_encoded_on_another_thread_is_not_disturbed_by_painting_on_this_one():
    engine = _painted(640, 480, strokes=10, seed=8)
    expected = _layer(engine).copy()
    snapshot = engine.snapshot_layers()
    results, errors = [], []

    def save():
        try:
            for _ in range(6):
                results.append(snapshot.encode_layer(0))
        except Exception as exc:  # noqa: BLE001 -- the test reports it
            errors.append(exc)

    worker = threading.Thread(target=save)
    worker.start()
    rng = random.Random(80)
    while worker.is_alive():
        _stroke(engine, rng, size=50.0, steps=30)
    worker.join()
    assert not errors, errors
    assert len(set(results)) == 1, "the same snapshot must encode to the same bytes while the document changes"
    assert _same_visible(_restored(results[0], 640, 480), expected)


def test_the_snapshot_is_cheap_because_it_shares_the_tiles():
    engine = native.PaintEngineFacade(2000, 2000)
    rng = random.Random(4)
    engine.paste_rgba_buffer_on_active_layer(0, 0, 2000, 2000, bytes(b for _ in range(2000 * 2000) for b in (rng.randrange(256), 7, 9, 255)), 0, 1.0)
    shared_before = engine.get_cow_shared_tiles_count()
    snapshot = engine.snapshot_layers()
    assert engine.get_cow_shared_tiles_count() > shared_before, "the snapshot copied the pixels instead of sharing the tiles"
    assert snapshot.layer_count == 1 and snapshot.width == 2000 and snapshot.height == 2000


def test_groups_and_filters_have_no_pixels():
    engine = native.PaintEngineFacade(64, 64)
    group = engine.add_group("g")
    filter_layer = engine.add_filter_layer("f", 2)
    snapshot = engine.snapshot_layers()
    assert snapshot.layer_count == 3
    assert snapshot.has_pixels(0) and not snapshot.has_pixels(group) and not snapshot.has_pixels(filter_layer)
    for index in (group, filter_layer, 3, -1):
        with pytest.raises(ValueError):
            snapshot.encode_layer(index)
    with pytest.raises(ValueError):
        engine.restore_layer_tiles(filter_layer, _painted(64, 64).snapshot_layers().encode_layer(0))


def test_a_tile_that_was_compressed_in_memory_is_not_lost_by_the_snapshot():
    """copyFrom shared the buffer of a compressed tile, which does not exist: the copy came out blank."""
    engine = _painted(seed=11)
    expected = _layer(engine).copy()
    engine.clear_history()  # the undo steps hold the tiles too, and a shared tile is not compressed
    engine.select_layer(engine.add_layer("active"))  # only layers that are not the active one are compressed
    assert engine.compress_inactive_layers() > 0, "no tile was compressed: the test would not reach the bug"
    assert _same_visible(_restored(engine.snapshot_layers().encode_layer(0), 301, 203), expected)


# -- a block that is not valid ------------------------------------------------------

def _good_blob():
    return _painted(301, 203, strokes=8, seed=6).snapshot_layers().encode_layer(0)


def _with(blob: bytes, offset: int, data: bytes) -> bytes:
    return blob[:offset] + data + blob[offset + len(data):]


def _corruptions():
    blob = _good_blob()
    count = _tile_count(blob)
    assert count >= 3
    first_entry = HEADER.size
    first_stored = ENTRY.unpack_from(blob, first_entry)[4]
    second_entry = first_entry + ENTRY.size + first_stored
    yield "empty", b""
    yield "shorter than the header", blob[: HEADER.size - 1]
    yield "wrong magic", _with(blob, 0, b"XXXX")
    yield "unknown version", _with(blob, 4, struct.pack("<H", 2))
    yield "wrong tile size", _with(blob, 6, struct.pack("<H", 64))
    yield "other canvas width", _with(blob, 8, struct.pack("<I", 302))
    yield "other canvas height", _with(blob, 12, struct.pack("<I", 100))
    yield "more tiles than the canvas", _with(blob, 16, struct.pack("<I", 1000))
    yield "reserved header field", _with(blob, 20, struct.pack("<I", 1))
    yield "count too high for the data", _with(blob, 16, struct.pack("<I", count + 1))
    yield "count too low: bytes after the last tile", _with(blob, 16, struct.pack("<I", count - 1))
    yield "truncated in a record", blob[: first_entry + 5]
    yield "truncated in the data", blob[:-3]
    yield "trailing bytes", blob + b"\0"
    yield "tile outside the canvas", _with(blob, first_entry, struct.pack("<H", 99))
    yield "tile row outside the canvas", _with(blob, first_entry + 2, struct.pack("<H", 99))
    yield "unknown codec", _with(blob, first_entry + 4, bytes([7]))
    yield "reserved record field", _with(blob, first_entry + 5, bytes([1]))
    yield "zero bytes stored", _with(blob, first_entry + 8, struct.pack("<I", 0))
    yield "huge stored size", _with(blob, first_entry + 8, struct.pack("<I", 0xFFFFFFF0))
    yield "tiles repeated", _with(blob, second_entry, blob[first_entry:first_entry + 4])
    yield "tiles out of order", _with(blob, first_entry, struct.pack("<HH", 2, 1))
    yield "lz4 data that does not decode", _with(blob, first_entry + ENTRY.size, bytes([0xFF]) * 8)


@pytest.mark.parametrize("name", [name for name, _ in _corruptions()])
def test_a_malformed_block_is_refused_and_the_layer_is_left_alone(name):
    bad = dict(_corruptions())[name]
    target = _painted(301, 203, seed=21)
    before = _layer(target).tobytes()
    with pytest.raises(ValueError):
        target.restore_layer_tiles(0, bad)
    assert _layer(target).tobytes() == before


def test_a_block_from_another_canvas_size_is_refused():
    blob = _good_blob()
    with pytest.raises(ValueError):
        native.PaintEngineFacade(128, 128).restore_layer_tiles(0, blob)


# -- composition in a batch ------------------------------------------------------------

def _two_layer_scene():
    engine = _painted(200, 150, seed=33)
    engine.add_layer("top")
    engine.select_layer(1)
    _stroke(engine, random.Random(34))
    return engine


def _change_properties(engine) -> None:
    engine.set_layer_opacity(1, 0.4)
    engine.set_layer_blend_mode(1, 2)
    engine.set_layer_visibility(0, False)
    engine.set_layer_visibility(0, True)
    engine.set_layer_name(1, "renamed")


def test_a_batch_composites_once_at_the_end_and_gives_the_same_picture():
    plain, batched = _two_layer_scene(), _two_layer_scene()
    _change_properties(plain)
    stale = bytes(batched.get_pixel_buffer())
    batched.begin_batch()
    _change_properties(batched)
    assert bytes(batched.get_pixel_buffer()) == stale, "the canvas was recomposited inside the batch"
    batched.end_batch()
    assert bytes(batched.get_pixel_buffer()) == bytes(plain.get_pixel_buffer())
    assert bytes(batched.get_pixel_buffer()) != stale


def test_batches_nest_and_an_unmatched_end_is_an_error():
    engine = _two_layer_scene()
    stale = bytes(engine.get_pixel_buffer())
    engine.begin_batch()
    engine.begin_batch()
    engine.set_layer_opacity(1, 0.2)
    engine.end_batch()
    assert bytes(engine.get_pixel_buffer()) == stale, "the inner end_batch composited"
    engine.end_batch()
    assert bytes(engine.get_pixel_buffer()) != stale
    with pytest.raises(RuntimeError):
        engine.end_batch()


def test_a_batch_with_nothing_to_composite_leaves_the_canvas_alone():
    engine = _two_layer_scene()
    before = bytes(engine.get_pixel_buffer())
    engine.begin_batch()
    engine.end_batch()
    assert bytes(engine.get_pixel_buffer()) == before


def test_restoring_tiles_inside_a_batch_composites_at_the_end():
    source = _painted(200, 150, seed=40)
    blob = source.snapshot_layers().encode_layer(0)
    target = native.PaintEngineFacade(200, 150)
    target.begin_batch()
    target.restore_layer_tiles(0, blob)
    assert bytes(target.get_pixel_buffer()) != bytes(source.get_pixel_buffer())
    target.end_batch()
    assert bytes(target.get_pixel_buffer()) == bytes(source.get_pixel_buffer())


# -- decoded away from the document ------------------------------------------------------------

def test_a_layer_decoded_on_another_thread_is_adopted_with_the_same_pixels():
    source = _painted(301, 203, seed=50)
    blob = source.snapshot_layers().encode_layer(0)
    decoded = []
    worker = threading.Thread(target=lambda: decoded.append(native.decode_layer_tiles(301, 203, blob)))
    worker.start()
    worker.join()
    assert decoded[0].width == 301 and decoded[0].height == 203
    target = native.PaintEngineFacade(301, 203)
    target.adopt_decoded_layer(0, decoded[0])
    assert _same_visible(_layer(target), _layer(source))
    assert bytes(target.get_pixel_buffer()) == bytes(source.get_pixel_buffer()), "the canvas is recomposited on adoption"


def test_a_decoded_layer_can_be_adopted_only_once():
    blob = _painted(130, 130, seed=51).snapshot_layers().encode_layer(0)
    decoded = native.decode_layer_tiles(130, 130, blob)
    native.PaintEngineFacade(130, 130).adopt_decoded_layer(0, decoded)
    with pytest.raises(RuntimeError):
        native.PaintEngineFacade(130, 130).adopt_decoded_layer(0, decoded)


def test_a_decoded_layer_of_another_canvas_size_or_for_a_layer_without_pixels_is_refused():
    blob = _painted(130, 130, seed=52).snapshot_layers().encode_layer(0)
    decoded = native.decode_layer_tiles(130, 130, blob)
    with pytest.raises(ValueError):
        native.PaintEngineFacade(131, 130).adopt_decoded_layer(0, decoded)
    engine = native.PaintEngineFacade(130, 130)
    group = engine.add_group("g")
    with pytest.raises(ValueError):
        engine.adopt_decoded_layer(group, decoded)
    engine.adopt_decoded_layer(0, decoded)  # the refusals must not have used it up


@pytest.mark.parametrize("width, height", [(0, 10), (10, 0), (-1, 10), (16385, 10), (2**31 - 1, 10)])
def test_an_illegal_canvas_size_is_refused_before_anything_is_allocated(width, height):
    with pytest.raises(ValueError):
        native.decode_layer_tiles(width, height, b"LMNT" + bytes(20))


def test_a_malformed_block_is_refused_at_decode_not_at_adoption():
    blob = _painted(130, 130, seed=53).snapshot_layers().encode_layer(0)
    with pytest.raises(ValueError):
        native.decode_layer_tiles(130, 130, blob[:-4])
    with pytest.raises(ValueError):
        native.decode_layer_tiles(131, 130, blob)
