"""The screen shows what a full composition would show, however little of it was composed (S3, Compositor foundation).

The composite buffer used to be recomposed whole, or in the box of the layer, at every layer operation: reordering,
duplicating or merging layers of a 4096² canvas took 0.5 s (1 s before the blend kernel) to redraw a window of it.
Now an operation only marks the 128x128 tiles it changed as stale (`CompositeProjection`) and whoever reads pixels
- the screen, the zoomed-out pyramid, the bucket and the wand over all layers, the full buffer - recomposes the stale
tiles of the area it reads. These tests pin that this is invisible:

- the sequences of `composite_sequences.py` (random layer, filter, stroke, paste, fill, transform, history, profile and
  resize operations) show the same pixels as the engine did before the projection (a golden recorded with it);
- after every few operations, what a lazy reader sees (only windows read, stale tiles piling up) equals a total
  recomposition, for the picture and for the pyramid: this one catches a dirty region that is too small, which a
  golden recorded with an eager engine cannot (the engine it was recorded with had one: releasing the clipping of a
  layer left the layers clipped above it with the old base);
- windows read alone equal the same windows of a twin engine that composed everything;
- the bucket, the wand and a stroke over stale tiles read and write what they would on a composed canvas;
- and the point of it: an operation composes nothing, a small window costs a small part of a full read, and
  `refresh_display`, which the screen calls at every camera event, composes nothing.

The projection and the Compositor's stale-tile rules have a native harness (tests/native/composite_projection_checks.cpp)
run by tests/test_composite_projection_native.py.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import numpy as np
import pytest

from tests import composite_sequences as seq

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

GOLDEN = json.loads((Path(__file__).parent / "golden" / "composite_projection_golden.json").read_text(encoding="utf-8"))
RED, GREEN, BLUE = (200, 40, 40, 255), (30, 200, 60, 255), (30, 40, 220, 255)


def _solid(color, width: int, height: int) -> bytes:
    return bytes(color) * (width * height)


def _engine(width: int = 200, height: int = 150, layers: int = 3):
    engine = native.PaintEngineFacade(width, height)
    while engine.get_drawing_layer_count() < layers:
        engine.add_layer("layer", -1)
    return engine


def _paste(engine, index: int, x: int, y: int, w: int, h: int, color) -> None:
    engine.select_layer(index)
    engine.paste_rgba_buffer_on_active_layer(x, y, w, h, _solid(color, w, h), 0, 1.0)


def _pixels(engine, x: int, y: int, w: int = 1, h: int = 1) -> bytes:
    return bytes(engine.get_display_region(x, y, w, h))


# -- the same pixels as before the projection -------------------------------------------------------------

def test_the_sequences_show_the_pixels_the_engine_showed_before_the_projection():
    different = [int(seed) for seed, expected in GOLDEN.items() if seq.sequence_digest(int(seed)) != expected]
    assert len(GOLDEN) == 300
    assert not different, f"sequences that now show other pixels: {different[:10]}"


# -- a lazy reader equals a total recomposition -------------------------------------------------------------

def test_what_a_lazy_reader_sees_equals_a_total_recomposition():
    failures = {seed: found for seed in range(400) if (found := seq.lazy_differs_from_total(seed))}
    assert not failures, f"(step, what) per seed: {dict(list(failures.items())[:10])}"


def test_releasing_the_clipping_of_a_base_updates_the_layers_clipped_above_it():
    # layer 2 is clipped to layer 1, which has nothing under the green square, so the square is hidden. Clipping
    # layer 1 to layer 0 makes layer 0 the base of layer 2: the square shows over the red. Only layer 1's own
    # area was recomposed before, and layer 1 (a square in tile 2,1; the square is in tile 0,0) does not reach it.
    engine = _engine(300, 200)
    _paste(engine, 0, 10, 10, 100, 100, RED)
    _paste(engine, 1, 260, 140, 30, 30, BLUE)
    _paste(engine, 2, 20, 20, 60, 60, GREEN)
    engine.set_layer_clipping_mask(2, True)
    hidden = _pixels(engine, 50, 50)
    assert hidden == bytes(RED), "the square is hidden while its base has nothing under it"
    engine.set_layer_clipping_mask(1, True)
    shown = _pixels(engine, 50, 50)
    assert shown != hidden, "the square shows over layer 0 once layer 0 is its base"
    assert shown == bytes(GREEN)
    seq.recompose_everything(engine)
    assert _pixels(engine, 50, 50) == shown


# -- windows read alone ----------------------------------------------------------------------------------

def test_windows_read_alone_equal_the_same_windows_of_a_twin_that_composed_everything():
    mismatches = []
    for seed in range(120):
        lazy, lazy_ops = seq.build(seed)
        twin, twin_ops = seq.build(seed)
        reads = random.Random(seed ^ 0x5EED)
        for step in range(seq.STEPS):
            seq.operate(lazy, lazy_ops)
            seq.operate(twin, twin_ops)
            twin.get_pixel_buffer()   # the twin composes everything; the lazy engine only what its windows touch
            width, height = twin.get_width(), twin.get_height()
            for _ in range(2):
                x, y = reads.randint(0, width - 1), reads.randint(0, height - 1)
                w, h = reads.randint(1, width - x), reads.randint(1, height - y)
                if _pixels(lazy, x, y, w, h) != _pixels(twin, x, y, w, h):
                    mismatches.append((seed, step, "window"))
            level = reads.randint(1, 3)
            levelw, levelh = twin.get_lod_size(level)
            x, y = reads.randint(0, levelw - 1), reads.randint(0, levelh - 1)
            w, h = reads.randint(1, levelw - x), reads.randint(1, levelh - y)
            if bytes(lazy.get_display_lod_region(level, x, y, w, h)) != bytes(twin.get_display_lod_region(level, x, y, w, h)):
                mismatches.append((seed, step, f"pyramid level {level}"))
        if bytes(lazy.get_pixel_buffer()) != bytes(twin.get_pixel_buffer()):
            mismatches.append((seed, "end", "whole"))
    assert not mismatches, mismatches[:10]


def test_a_pyramid_window_composes_the_tiles_it_covers_at_full_size():
    # A window of level L covers [x * 2^L, (x + w) * 2^L) of the canvas: on a canvas of 5x5 tiles a window of the
    # smallest level far from the origin sits in other tiles than the same numbers read as canvas pixels.
    for level in (1, 2, 3):
        lazy, twin = _engine(640, 640), _engine(640, 640)
        for engine in (lazy, twin):
            _paste(engine, 0, 0, 0, 640, 640, RED)
            _paste(engine, 1, 300, 300, 300, 300, BLUE)
            _paste(engine, 2, 450, 380, 150, 200, GREEN)
            engine.get_display_pixel_buffer_lod(level)
            engine.set_layer_opacity(1, 0.5)
            engine.reorder_layer(2, 1)
        twin.get_pixel_buffer()
        width, height = twin.get_lod_size(level)
        x, y, w, h = width * 3 // 4 - 8, height * 2 // 3 - 8, 16, 16
        assert bytes(lazy.get_display_lod_region(level, x, y, w, h)) == bytes(twin.get_display_lod_region(level, x, y, w, h))
        # and the same window on the whole canvas: tiles the window does not cover are not needed
        assert bytes(lazy.get_display_region(x << level, y << level, w << level, h << level)) == \
            bytes(twin.get_display_region(x << level, y << level, w << level, h << level))


# -- the bucket, the wand and a stroke over stale tiles ------------------------------------------------------

def _changed_composition(engine) -> None:
    """Edits that change the composition and are not read: the tiles they touch are stale."""
    engine.set_layer_opacity(0, 0.5)
    engine.set_layer_blend_mode(1, 3)
    engine.reorder_layer(0, 2)


def _red_with_a_blue_square():
    """The composition has a blue square on red; hiding layer 1 makes it all red, and nothing reads it."""
    engine = _engine(300, 200, layers=2)
    _paste(engine, 0, 0, 0, 300, 200, RED)
    _paste(engine, 1, 60, 40, 80, 60, BLUE)
    engine.get_pixel_buffer()
    engine.set_layer_visibility(1, False)
    return engine


def _after_hiding_the_square(act):
    """What the document looks like after `act` on an engine that has not composed the hidden square away yet,
    and on a twin that has."""
    lazy, twin = _red_with_a_blue_square(), _red_with_a_blue_square()
    seq.recompose_everything(twin)
    for engine in (lazy, twin):
        engine.select_layer(0)
        act(engine)
    return bytes(lazy.get_pixel_buffer()), bytes(twin.get_pixel_buffer())


def test_the_bucket_over_all_layers_reads_the_composition_not_a_stale_one():
    # on the composition the square is gone and the whole canvas is one red area: the bucket fills all of it
    lazy, twin = _after_hiding_the_square(lambda e: e.flood_fill(70, 50, native.ColorRGBA(10, 200, 90, 255), 5, True, 0, True))
    assert lazy == twin
    assert _pixels_of(twin, 5, 5) == bytes((10, 200, 90, 255)), "the fill reached outside the old square"


def test_the_wand_over_all_layers_reads_the_composition_not_a_stale_one():
    def select_and_fill(engine):
        engine.magic_wand_select(70, 50, 5, True, 0, False, 0, True)
        engine.fill_selection_on_active_layer(native.ColorRGBA(10, 200, 90, 255))
    lazy, twin = _after_hiding_the_square(select_and_fill)
    assert lazy == twin
    assert _pixels_of(twin, 5, 5) == bytes((10, 200, 90, 255)), "the selection did not reach outside the old square"


def _pixels_of(buffer: bytes, x: int, y: int, width: int = 300) -> bytes:
    return buffer[(y * width + x) * 4:(y * width + x) * 4 + 4]


def test_the_bucket_and_the_wand_on_the_active_layer_ignore_the_stale_composition():
    # "all layers" off: the region comes from the layer itself, which was never stale
    lazy, twin = _after_hiding_the_square(lambda e: e.flood_fill(70, 50, native.ColorRGBA(10, 200, 90, 255), 5, True, 0, False))
    assert lazy == twin


def test_a_stroke_on_a_stale_canvas_shows_its_ink_while_it_is_drawn_and_ends_equal():
    for seed in range(20):
        lazy, _ = seq.build(seed)
        twin, _ = seq.build(seed)
        for engine in (lazy, twin):
            _changed_composition(engine)
        seq.recompose_everything(twin)
        width, height = lazy.get_width(), lazy.get_height()
        ends = []
        for engine in (lazy, twin):
            engine.select_layer(engine.get_drawing_layer_count() - 1)
            engine.get_brush_profile().brush_size = 24.0
            engine.begin_stroke_raw(width * 0.2, height * 0.5, 0.8, 0.0)
            for step in range(1, 9):
                engine.update_stroke_raw(width * 0.2 + step * width * 0.07, height * 0.5, 0.8, step * 0.01)
            ends.append(_pixels(engine, 0, 0, width, height))   # mid-stroke, with the scratch ink on screen
            engine.end_stroke_raw()
        assert ends[0] == ends[1], f"seed {seed}: the picture under a stroke differs"
        assert bytes(lazy.get_pixel_buffer()) == bytes(twin.get_pixel_buffer()), f"seed {seed}: after the stroke"


def test_a_new_engine_reads_a_composed_canvas():
    engine = native.PaintEngineFacade(300, 200)
    first = bytes(engine.get_pixel_buffer())
    seq.recompose_everything(engine)
    assert first == bytes(engine.get_pixel_buffer())


def test_the_color_profile_and_the_pyramid_follow_the_stale_tiles():
    for profile in (1, 2):
        lazy, twin = _engine(300, 200), _engine(300, 200)
        for engine in (lazy, twin):
            _paste(engine, 0, 5, 5, 250, 150, RED)
            _paste(engine, 1, 60, 40, 150, 100, BLUE)
            engine.set_color_profile(profile)
            engine.get_display_pixel_buffer_lod(2)
            engine.set_layer_opacity(1, 0.4)
        seq.recompose_everything(twin)
        assert bytes(lazy.get_display_lod_region(1, 20, 10, 100, 60)) == bytes(twin.get_display_lod_region(1, 20, 10, 100, 60))
        assert bytes(lazy.get_display_region(0, 0, 300, 200)) == bytes(twin.get_display_region(0, 0, 300, 200))
        assert bytes(lazy.get_display_pixel_buffer()) == bytes(twin.get_display_pixel_buffer())


# -- the point: nothing is composed until something reads ----------------------------------------------------

def _best_ms(action, runs: int = 3) -> float:
    best = float("inf")
    for _ in range(runs):
        started = time.perf_counter()
        action()
        best = min(best, (time.perf_counter() - started) * 1000.0)
    return best


@pytest.fixture(scope="module")
def heavy_engine():
    """2048² with 6 translucent, fully painted layers: a full composition takes tens of milliseconds."""
    rng = np.random.default_rng(7)
    engine = _engine(2048, 2048, layers=6)
    for index in range(6):
        pixels = rng.integers(0, 256, size=(2048, 2048, 4), dtype=np.uint8)
        pixels[..., 3] = 255 if index == 0 else 160
        engine.select_layer(index)
        engine.paste_rgba_buffer_on_active_layer(0, 0, 2048, 2048, pixels.tobytes(), 0, 1.0)
        engine.set_layer_opacity(index, 0.6 if index else 1.0)
    engine.get_pixel_buffer()
    return engine


def _reorder_twice(engine) -> None:
    engine.reorder_layer(5, 1)
    engine.reorder_layer(1, 5)


def test_an_operation_composes_nothing_and_a_small_window_costs_a_small_part_of_a_full_read(heavy_engine):
    def operation_then(read):
        return lambda: (_reorder_twice(heavy_engine), read())
    full = _best_ms(operation_then(heavy_engine.get_pixel_buffer))
    operation = _best_ms(lambda: _reorder_twice(heavy_engine))
    window = _best_ms(operation_then(lambda: heavy_engine.get_display_region(300, 300, 64, 64)))
    pyramid = _best_ms(operation_then(lambda: heavy_engine.get_display_lod_region(3, 40, 40, 32, 32)))
    assert operation * 20 < full, f"two layer operations took {operation:.2f} ms against {full:.1f} ms of a full read"
    assert window * 8 < full, f"a 64x64 window took {window:.2f} ms against {full:.1f} ms of a full read"
    assert pyramid * 8 < full, f"a pyramid window took {pyramid:.2f} ms against {full:.1f} ms of a full read"


def test_refresh_display_composes_nothing_and_the_next_read_is_still_right(heavy_engine):
    full = _best_ms(lambda: (_reorder_twice(heavy_engine), heavy_engine.get_pixel_buffer()))
    refresh = _best_ms(lambda: (_reorder_twice(heavy_engine), heavy_engine.refresh_display()))
    assert refresh * 20 < full, f"refresh_display took {refresh:.2f} ms against {full:.1f} ms of a full read"
    window = _pixels(heavy_engine, 700, 900, 50, 50)
    seq.recompose_everything(heavy_engine)
    assert window == _pixels(heavy_engine, 700, 900, 50, 50)
