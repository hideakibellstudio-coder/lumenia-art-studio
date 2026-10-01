"""The zoomed-out pyramid is refreshed only where the canvas changed, and never shows a stale pixel (D18).

Until 2026-10-01 the pyramid was rebuilt whole on every read once the active layer had
ever had a dirty tile (nothing cleared those flags): 2.6 / 10.3 / 12.9 ms per repaint at
1080p / 4K / 6000x4000, the default view of a large document. It now keeps the rectangle
the compositor wrote since the last read and refreshes just that, in each of the three levels.

The risk of an incremental cache is a stale pixel. So the oracle here is independent of the
pyramid: a numpy box filter over `get_display_pixel_buffer()`, checked after every operation
of a matrix (strokes, paste, fill, selection, transform, undo, layers, filters with reach,
pixelate, colour profile, resize...) and after random sequences of them, including sequences
that change the canvas several times between two reads.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

LEVELS = (1, 2, 3)
GAUSSIAN_BLUR, PIXELATE = 2, 6


# -- the oracle ---------------------------------------------------------------

def _halve(prev: np.ndarray) -> np.ndarray:
    """The box filter of the engine: (a + b + c + d + 2) >> 2 over each 2x2, edges clamped."""
    h, w = prev.shape[:2]
    nh, nw = max(1, h // 2), max(1, w // 2)
    ys0, xs0 = np.arange(nh) * 2, np.arange(nw) * 2
    ys1, xs1 = np.minimum(ys0 + 1, h - 1), np.minimum(xs0 + 1, w - 1)
    total = (prev[ys0][:, xs0].astype(np.uint32) + prev[ys0][:, xs1] + prev[ys1][:, xs0] + prev[ys1][:, xs1] + 2) >> 2
    return total.astype(np.uint8)


def _expected_levels(engine) -> dict[int, np.ndarray]:
    width, height = engine.get_width(), engine.get_height()
    level = np.frombuffer(engine.get_display_pixel_buffer(), dtype=np.uint8).reshape(height, width, 4)
    levels = {}
    for number in LEVELS:
        level = _halve(level)
        levels[number] = level
    return levels


def _actual_level(engine, number: int) -> np.ndarray:
    data, width, height, _scale = engine.get_display_pixel_buffer_lod(number)
    return np.frombuffer(data, dtype=np.uint8).reshape(height, width, 4)


def _assert_pyramid_is_current(engine, context: str) -> None:
    # The pyramid is read BEFORE the oracle asks for the full display buffer: with a colour profile that
    # request converts the whole canvas as a side effect, and an oracle that repairs the thing it checks
    # hides a pyramid that converted too little (a mutation that dropped 8 columns passed once).
    actual_levels = {number: _actual_level(engine, number) for number in LEVELS}
    expected = _expected_levels(engine)
    for number in LEVELS:
        actual = actual_levels[number]
        assert actual.shape == expected[number].shape, f"{context}: level {number} has the wrong size"
        if not np.array_equal(actual, expected[number]):
            wrong = np.argwhere(np.any(actual != expected[number], axis=2))
            raise AssertionError(
                f"{context}: level {number} shows {len(wrong)} stale pixels, the first at (x={wrong[0][1]}, y={wrong[0][0]})")


# -- the operations -----------------------------------------------------------

def _noise(width: int, height: int, rng: random.Random, alpha: int = 255) -> bytes:
    return bytes(b for _ in range(width * height) for b in (rng.randrange(256), rng.randrange(256), rng.randrange(256), alpha))


def _brush(engine, kind: int, size: float, color=(200, 40, 40)) -> None:
    engine.set_engine_type(kind)
    profile = engine.get_brush_profile()
    profile.brush_size, profile.opacity, profile.hardness = size, 1.0, 0.5
    profile.base_color = native.ColorRGBA(*color, 255)


def _stroke(engine, rng: random.Random, kind: int = 2, size: float = 14.0) -> bool:
    width, height = engine.get_width(), engine.get_height()
    _brush(engine, kind, size, (rng.randrange(256), rng.randrange(256), rng.randrange(256)))
    x, y = rng.uniform(0, width), rng.uniform(0, height)
    engine.begin_stroke_raw(x, y, 0.9)
    for step in range(1, 12):
        engine.update_stroke_raw(x + step * rng.uniform(-6, 12), y + step * rng.uniform(-6, 12), 0.9, step * 0.01)
    engine.end_stroke_raw()
    return True


def _paste(engine, rng: random.Random) -> bool:
    w, h = rng.randint(3, 40), rng.randint(3, 40)
    return engine.paste_rgba_buffer_on_active_layer(
        rng.randint(-5, engine.get_width() - 3), rng.randint(-5, engine.get_height() - 3), w, h, _noise(w, h, rng, 200), 0, 0.9)


def _fill(engine, rng: random.Random) -> bool:
    return engine.flood_fill(rng.randrange(engine.get_width()), rng.randrange(engine.get_height()),
                             native.ColorRGBA(rng.randrange(256), 30, 90, 255), 60, True, 1, True)


def _select_and_fill(engine, rng: random.Random) -> bool:
    engine.select_rect(rng.randint(0, 40), rng.randint(0, 40), rng.randint(5, 60), rng.randint(5, 60))
    changed = engine.fill_selection_on_active_layer(native.ColorRGBA(10, 200, 120, 255))
    engine.clear_selection()
    return changed


def _select_and_delete(engine, rng: random.Random) -> bool:
    engine.select_ellipse(rng.randint(10, 80), rng.randint(10, 80), rng.randint(5, 30), rng.randint(5, 30))
    changed = engine.delete_selection_on_active_layer()
    engine.clear_selection()
    return changed


def _transform(engine, rng: random.Random) -> bool:
    if not engine.begin_transform():
        return False
    return engine.commit_transform(rng.uniform(-30, 30), rng.uniform(-30, 30), rng.uniform(0.6, 1.4), rng.uniform(0.6, 1.4),
                                   rng.uniform(-40, 40), 50.0, 50.0, False, False, 2)


def _flip(engine, rng: random.Random) -> bool:
    return engine.flip_active_layer(rng.random() < 0.5)


def _rotate(engine, rng: random.Random) -> bool:
    return engine.rotate_active_layer_90(rng.random() < 0.5)


def _undo(engine, rng: random.Random) -> bool:
    return engine.undo()


def _redo(engine, rng: random.Random) -> bool:
    return engine.redo()


def _add_layer(engine, rng: random.Random) -> bool:
    index = engine.add_layer(f"l{rng.randrange(1000)}")
    engine.select_layer(index)
    _paste(engine, rng)
    return True


def _opacity(engine, rng: random.Random) -> bool:
    engine.set_layer_opacity(rng.randrange(engine.get_drawing_layer_count()), rng.uniform(0.1, 1.0))
    return True


def _blend(engine, rng: random.Random) -> bool:
    engine.set_layer_blend_mode(rng.randrange(engine.get_drawing_layer_count()), rng.randrange(0, 6))
    return True


def _visibility(engine, rng: random.Random) -> bool:
    index = rng.randrange(engine.get_drawing_layer_count())
    engine.set_layer_visibility(index, not engine.get_layer_info(index)["visible"])
    return True


def _reorder(engine, rng: random.Random) -> bool:
    count = engine.get_drawing_layer_count()
    return count > 1 and engine.reorder_layer(rng.randrange(count), rng.randrange(count))


def _duplicate(engine, rng: random.Random) -> bool:
    return engine.duplicate_layer(rng.randrange(engine.get_drawing_layer_count())) >= 0


def _merge_down(engine, rng: random.Random) -> bool:
    count = engine.get_drawing_layer_count()
    return count > 1 and engine.merge_layer_down(rng.randrange(1, count))


def _remove(engine, rng: random.Random) -> bool:
    count = engine.get_drawing_layer_count()
    return count > 1 and engine.remove_layer(rng.randrange(count))


def _clear_layer(engine, rng: random.Random) -> bool:
    engine.clear_layer(rng.randrange(engine.get_drawing_layer_count()))
    return True


def _blur_filter_then_paint(engine, rng: random.Random) -> bool:
    """A blur layer on top reaches beyond the stroke: the region written is larger than the stroke."""
    index = engine.add_filter_layer("blur", GAUSSIAN_BLUR)
    engine.set_filter_params(index, [rng.uniform(2.0, 9.0), 0.0, 0.0, 0.0])
    engine.select_layer(0)
    return _stroke(engine, rng)


def _pixelate_filter_then_paint(engine, rng: random.Random) -> bool:
    """Pixelate snaps the repainted region to its block size."""
    index = engine.add_filter_layer("pixelate", PIXELATE)
    engine.set_filter_params(index, [float(rng.choice((4, 8, 16))), 0.0, 0.0, 0.0])
    engine.select_layer(0)
    return _stroke(engine, rng)


def _background(engine, rng: random.Random) -> bool:
    engine.set_background_visibility(rng.random() < 0.5)
    engine.set_background_color(rng.randrange(256), rng.randrange(256), rng.randrange(256), 255)
    return True


def _profile(engine, rng: random.Random) -> bool:
    engine.set_color_profile(rng.choice((0, 1, 2, 8, 12)))
    return True


def _resize(engine, rng: random.Random) -> bool:
    engine.resize_canvas(rng.randint(40, 120), rng.randint(40, 120))
    return True


def _clear_canvas(engine, rng: random.Random) -> bool:
    engine.clear_canvas()
    return True


OPERATIONS = {
    "stroke": _stroke, "soft_stroke": lambda e, r: _stroke(e, r, 1, 40.0), "smudge_stroke": lambda e, r: _stroke(e, r, 6, 20.0),
    "paste": _paste, "flood_fill": _fill, "select_and_fill": _select_and_fill, "select_and_delete": _select_and_delete,
    "transform": _transform, "flip": _flip, "rotate_90": _rotate, "undo": _undo, "redo": _redo,
    "add_layer": _add_layer, "opacity": _opacity, "blend": _blend, "visibility": _visibility, "reorder": _reorder,
    "duplicate": _duplicate, "merge_down": _merge_down, "remove_layer": _remove, "clear_layer": _clear_layer,
    "blur_filter": _blur_filter_then_paint, "pixelate_filter": _pixelate_filter_then_paint,
    "background": _background, "colour_profile": _profile, "resize": _resize, "clear_canvas": _clear_canvas,
}
# Operations that make no pixel different when it is the first thing done on a fresh canvas,
# so they would pass a stale pyramid; the matrix test prepares the scene first.


def _scene(width: int = 101, height: int = 77, seed: int = 3):
    engine = native.PaintEngineFacade(width, height)
    rng = random.Random(seed)
    engine.paste_rgba_buffer_on_active_layer(0, 0, width, height, _noise(width, height, rng), 0, 1.0)
    engine.add_layer("top")
    engine.select_layer(1)
    engine.paste_rgba_buffer_on_active_layer(10, 8, 50, 40, _noise(50, 40, rng, 180), 0, 1.0)
    _assert_pyramid_is_current(engine, "the scene")  # builds the pyramid: from here on every change is incremental
    return engine


# -- 1. each operation, alone -------------------------------------------------

@pytest.mark.parametrize("name", sorted(OPERATIONS))
def test_after_each_operation_every_level_matches_a_fresh_filter_of_the_canvas(name):
    engine = _scene()
    rng = random.Random(11)
    # give undo/redo something to act on, then read so the next change is the one under test
    _stroke(engine, rng)
    _assert_pyramid_is_current(engine, "before the operation")
    OPERATIONS[name](engine, rng)
    _assert_pyramid_is_current(engine, name)
    if name == "undo":
        engine.redo()
        _assert_pyramid_is_current(engine, "redo")


@pytest.mark.parametrize("profile", (1, 3, 8, 12))
@pytest.mark.parametrize("name", sorted(OPERATIONS))
def test_with_a_colour_profile_every_operation_is_followed_by_converting_only_what_changed(name, profile):
    """With a profile other than sRGB the pyramid reads a converted copy of the canvas, converted only
    where the pyramid is about to rebuild (it was the whole canvas on every read: 390 ms at 4K)."""
    engine = _scene()
    rng = random.Random(23)
    engine.set_color_profile(profile)
    _assert_pyramid_is_current(engine, f"profile {profile} just set")
    _stroke(engine, rng)
    _assert_pyramid_is_current(engine, f"profile {profile}, a stroke")
    OPERATIONS[name](engine, rng)
    _assert_pyramid_is_current(engine, f"profile {profile}, {name}")


def test_with_a_colour_profile_changes_piling_up_between_two_reads_are_all_converted():
    engine = _scene()
    rng = random.Random(5)
    engine.set_color_profile(3)
    _assert_pyramid_is_current(engine, "profile set")
    for _ in range(4):
        _stroke(engine, rng)
        _paste(engine, rng)
    _assert_pyramid_is_current(engine, "four strokes and four pastes between two reads")


def test_switching_the_profile_back_and_forth_never_leaves_a_converted_pixel_behind():
    engine = _scene()
    rng = random.Random(9)
    for profile in (3, 0, 8, 3, 0):
        engine.set_color_profile(profile)
        _stroke(engine, rng)
        _assert_pyramid_is_current(engine, f"profile {profile}")


# -- 2. random sequences, with unread changes piling up ------------------------

@pytest.mark.parametrize("seed", range(40))
def test_random_sequences_never_leave_a_stale_pixel(seed):
    rng = random.Random(1000 + seed)
    engine = _scene(rng.choice((101, 64, 130)), rng.choice((77, 64, 51)), seed)
    names = sorted(OPERATIONS)
    done = []
    for _ in range(14):
        name = rng.choice(names)
        done.append(name)
        OPERATIONS[name](engine, rng)
        if rng.random() < 0.55:  # sometimes several changes happen before anyone looks
            _assert_pyramid_is_current(engine, f"seed {seed}, after {done}")
    _assert_pyramid_is_current(engine, f"seed {seed}, after {done}")


# -- 2b. reading in the middle of a stroke: the hot path -----------------------

@pytest.mark.parametrize("engine_kind", range(0, 9))
def test_reading_after_every_sample_of_a_stroke_never_shows_a_stale_pixel(engine_kind):
    """The repaint of a stroke at zoom-out asks for the pyramid after each segment, with the
    stroke still open: the only changes are the rectangles the compositor wrote."""
    engine = _scene()
    rng = random.Random(40 + engine_kind)
    _brush(engine, engine_kind, 18.0)
    x, y = rng.uniform(5, 60), rng.uniform(5, 40)
    engine.begin_stroke_raw(x, y, 0.9)
    for step in range(1, 16):
        engine.update_stroke_raw(x + step * 4.5, y + step * rng.uniform(0.5, 3.0), 0.9, step * 0.01)
        _assert_pyramid_is_current(engine, f"engine {engine_kind}, sample {step}")
    engine.end_stroke_raw()
    _assert_pyramid_is_current(engine, f"engine {engine_kind}, after the stroke")


def test_a_stroke_under_a_blur_layer_is_followed_across_the_reach_of_the_filter():
    engine = _scene()
    index = engine.add_filter_layer("blur", GAUSSIAN_BLUR)
    engine.set_filter_params(index, [8.0, 0.0, 0.0, 0.0])
    engine.select_layer(0)
    _assert_pyramid_is_current(engine, "with the filter")
    _brush(engine, 2, 10.0)
    engine.begin_stroke_raw(50.0, 40.0, 0.9)
    for step in range(1, 10):
        engine.update_stroke_raw(50.0 + step * 3, 40.0 + step, 0.9, step * 0.01)
        _assert_pyramid_is_current(engine, f"blur, sample {step}")
    engine.end_stroke_raw()


# -- 3. a read with nothing changed does no work -------------------------------

def test_a_read_with_no_change_returns_the_same_pixels_without_a_rebuild():
    engine = _scene()
    _stroke(engine, random.Random(5))
    first = bytes(engine.get_display_pixel_buffer_lod(1)[0])
    again = bytes(engine.get_display_pixel_buffer_lod(1)[0])
    assert first == again
    _assert_pyramid_is_current(engine, "idle read")


# -- 4. the region of a level ---------------------------------------------------

@pytest.mark.parametrize("level", LEVELS)
def test_a_lod_region_is_that_part_of_the_level(level):
    engine = _scene()
    _stroke(engine, random.Random(8))
    expected = _expected_levels(engine)[level]
    h, w = expected.shape[:2]
    for x, y, rw, rh in ((0, 0, 1, 1), (3, 2, w - 6, h - 4), (0, 0, w, h), (w - 2, h - 1, 2, 1)):
        got = engine.get_display_lod_region(level, x, y, rw, rh)
        assert got == expected[y:y + rh, x:x + rw].tobytes()


def test_a_lod_region_follows_a_change_without_a_whole_read_in_between():
    engine = _scene()
    engine.get_display_lod_region(1, 0, 0, 4, 4)  # builds the pyramid
    engine.paste_rgba_buffer_on_active_layer(20, 20, 6, 6, bytes([255, 0, 0, 255]) * 36, 0, 1.0)
    expected = _expected_levels(engine)[1]
    assert engine.get_display_lod_region(1, 8, 8, 6, 6) == expected[8:14, 8:14].tobytes()


@pytest.mark.parametrize("args", [(0, 0, 0, 4, 4), (4, 0, 0, 4, 4), (-1, 0, 0, 4, 4), (1, -1, 0, 4, 4), (1, 0, 0, 0, 4),
                                  (1, 40, 0, 20, 4), (1, 0, 30, 4, 20), (1, 0, 0, 1000, 4)])
def test_a_bad_level_or_rectangle_is_refused_not_clipped(args):
    engine = _scene()
    with pytest.raises(ValueError):
        engine.get_display_lod_region(*args)


@pytest.mark.parametrize("width, height", [(1, 1), (2, 1), (1, 7), (5, 3), (101, 77), (64, 64), (130, 51)])
def test_the_level_sizes_are_the_ones_the_engine_builds(width, height):
    engine = native.PaintEngineFacade(width, height)
    assert engine.get_lod_size(0) == (width, height)
    for number in LEVELS:
        data, level_w, level_h, _scale = engine.get_display_pixel_buffer_lod(number)
        assert engine.get_lod_size(number) == (level_w, level_h)
        assert len(data) == level_w * level_h * 4
