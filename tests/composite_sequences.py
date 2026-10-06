"""Random sequences of document operations, to compare what the screen shows with the whole composition.

Shared by `tests/test_composite_projection.py`. A sequence is a seed: the same seed always gives the same
operations (one random stream decides the operations, another one the reads), so two engines, or the same engine
read in two different ways, can be compared step by step.

The operations are the ones that change the composition: layers (add, remove, duplicate, reorder, merge, clear),
groups and filters, opacity, blend mode, visibility and clipping, strokes, pastes, bucket fill, selection fills,
flips, transforms, undo and redo, paper colour, render options and canvas resize, with some of them inside a
batch. An operation the engine refuses (a bad index, nothing to undo) is simply skipped, the same way in both runs.
"""
from __future__ import annotations

import hashlib
import random
from typing import Callable

import aladyn_engine_native as native

SIZES = [(150, 110), (257, 131), (300, 200), (128, 128), (129, 257)]
FILTER_PARAMS = {
    0: lambda r: [r.uniform(0, 360), r.random(), r.random()],
    1: lambda r: [r.uniform(-50, 50), r.uniform(-50, 50), 1.0, 0.0],
    2: lambda r: [float(r.choice([1, 8, 20, 60])), 0.0, 0.0],
    4: lambda r: [r.choice([30.0, 100.0]), 0.0, 50.0],
    6: lambda r: [float(r.choice([2, 8, 16])), 0.0, 0.0],
}
STEPS = 12


def digest(data) -> str:
    return hashlib.sha256(bytes(data)).hexdigest()[:16]


def _paintable(facade, index: int) -> bool:
    return not (facade.is_group(index) or facade.is_filter_layer(index))


def _pick_layer(facade, rng: random.Random, paintable: bool = False) -> int:
    count = facade.get_drawing_layer_count()
    candidates = [i for i in range(count) if not paintable or _paintable(facade, i)]
    return rng.choice(candidates) if candidates else 0


def _paste(facade, rng: random.Random) -> None:
    facade.select_layer(_pick_layer(facade, rng, paintable=True))
    w, h = facade.get_width(), facade.get_height()
    pw, ph = rng.randint(8, max(9, w // 2)), rng.randint(8, max(9, h // 2))
    x, y = rng.randint(-10, max(1, w - pw)), rng.randint(-10, max(1, h - ph))
    color = bytes([rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255), rng.choice([255, 255, 200, 90])])
    facade.paste_rgba_buffer_on_active_layer(x, y, pw, ph, color * (pw * ph), rng.choice([0, 0, 0, 1, 3]), rng.choice([1.0, 1.0, 0.6]))


def _stroke(facade, rng: random.Random) -> None:
    facade.select_layer(_pick_layer(facade, rng, paintable=True))
    facade.get_brush_profile().brush_size = rng.choice([6.0, 20.0, 50.0])
    w, h = facade.get_width(), facade.get_height()
    x, y = rng.uniform(5, max(6, w - 5)), rng.uniform(5, max(6, h - 5))
    facade.begin_stroke_raw(x, y, 0.8, 0.0)
    for step in range(1, rng.randint(4, 12)):
        facade.update_stroke_raw(min(w - 1.0, max(0.0, x + step * rng.uniform(-6, 6))), min(h - 1.0, max(0.0, y + step * rng.uniform(-6, 6))), 0.7, step * 0.01)
    facade.end_stroke_raw()


def _add_filter(facade, rng: random.Random) -> None:
    filter_type = rng.choice(list(FILTER_PARAMS))
    index = facade.add_filter_layer("filter", filter_type, rng.randint(-1, facade.get_drawing_layer_count()))
    facade.set_filter_params(index, FILTER_PARAMS[filter_type](rng))


def _fill(facade, rng: random.Random) -> None:
    facade.select_layer(_pick_layer(facade, rng, paintable=True))
    w, h = facade.get_width(), facade.get_height()
    if rng.random() < 0.5:
        facade.flood_fill(rng.randint(0, w - 1), rng.randint(0, h - 1), native.ColorRGBA(rng.randint(0, 255), 40, 200, 255),
                          rng.choice([5, 30]), rng.choice([True, False]), rng.choice([0, 1]), rng.choice([True, False]))
    else:
        facade.select_rect(rng.randint(0, w // 2), rng.randint(0, h // 2), rng.randint(5, w // 2), rng.randint(5, h // 2))
        if rng.random() < 0.5:
            facade.fill_selection_on_active_layer(native.ColorRGBA(rng.randint(0, 255), 200, 40, 255))
        else:
            facade.delete_selection_on_active_layer()
        facade.clear_selection()


def _transform(facade, rng: random.Random) -> None:
    facade.select_layer(_pick_layer(facade, rng, paintable=True))
    choice = rng.randint(0, 3)
    if choice == 0:
        facade.flip_active_layer(rng.choice([True, False]))
    elif choice == 1:
        facade.rotate_active_layer_90(rng.choice([True, False]))
    elif facade.begin_transform():
        if choice == 2:
            facade.commit_transform(rng.uniform(-20, 20), rng.uniform(-20, 20), rng.choice([0.5, 1.0, 1.5]), 1.0, rng.choice([0.0, 15.0, 90.0]),
                                    facade.get_width() / 2.0, facade.get_height() / 2.0)
        else:
            facade.cancel_transform()


def _setter(facade, rng: random.Random) -> None:
    index = _pick_layer(facade, rng)
    kind = rng.randint(0, 4)
    if kind == 0:
        facade.set_layer_opacity(index, rng.choice([1.0, 0.7, 0.4, 0.0]))
    elif kind == 1:
        facade.set_layer_blend_mode(index, rng.randint(0, 12))
    elif kind == 2:
        facade.set_layer_visibility(index, rng.choice([True, False]))
    elif kind == 3:
        facade.set_layer_clipping_mask(index, rng.choice([True, False]))
    else:
        facade.set_group_pass_through(index, rng.choice([True, False]))


def _structure(facade, rng: random.Random) -> None:
    count = facade.get_drawing_layer_count()
    kind = rng.randint(0, 6)
    if kind == 0:
        facade.add_layer("layer", rng.randint(-1, count))
    elif kind == 1:
        facade.remove_layer(_pick_layer(facade, rng)) if count > 1 else None
    elif kind == 2:
        facade.duplicate_layer(_pick_layer(facade, rng))
    elif kind == 3:
        facade.reorder_layer(_pick_layer(facade, rng), rng.randint(0, count - 1))
    elif kind == 4:
        facade.merge_layer_down(_pick_layer(facade, rng))
    elif kind == 5:
        facade.clear_layer(_pick_layer(facade, rng))
    else:
        facade.add_group("group", rng.randint(-1, count))


def _document(facade, rng: random.Random) -> None:
    kind = rng.randint(0, 5)
    if kind == 0:
        facade.set_background_color(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255), 255)
    elif kind == 1:
        facade.set_background_visibility(rng.choice([True, False]))
    elif kind == 2:
        facade.set_render_options(False, rng.choice([True, False]), rng.choice([True, False, False]))
    elif kind == 3:
        facade.set_color_profile(rng.choice([0, 0, 1, 2]))
    elif kind == 4:
        facade.resize_canvas(rng.choice([128, 150, 200, 257]), rng.choice([110, 131, 200]))
    else:
        for _ in range(rng.randint(2, 3)):
            _setter(facade, rng)


def _history(facade, rng: random.Random) -> None:
    for _ in range(rng.randint(1, 2)):
        (facade.undo if rng.random() < 0.6 else facade.redo)()


OPERATIONS = [(_paste, 4), (_stroke, 4), (_add_filter, 1), (_fill, 2), (_transform, 2), (_setter, 6), (_structure, 6),
              (_document, 3), (_history, 3)]


def build(seed: int):
    """The document of a sequence: a size, 2 to 4 layers with something on them."""
    rng = random.Random(seed)
    width, height = SIZES[seed % len(SIZES)]
    facade = native.PaintEngineFacade(width, height)
    for _ in range(rng.randint(1, 3)):
        facade.add_layer("layer", -1)
    for index in range(facade.get_drawing_layer_count()):
        facade.select_layer(index)
        _paste(facade, rng)
    return facade, rng


def operate(facade, rng: random.Random) -> None:
    """One operation, chosen by `rng`; refused operations are skipped."""
    operation = rng.choices([op for op, _ in OPERATIONS], [weight for _, weight in OPERATIONS])[0]
    try:
        operation(facade, rng)
    except (ValueError, RuntimeError, IndexError):
        pass


def full_read(facade, rng: random.Random) -> str:
    """The whole composition, plus one random region at full size and one of the zoomed-out pyramid."""
    parts = [digest(facade.get_pixel_buffer())]
    parts.append(digest(read_region(facade, rng)))
    parts.append(digest(read_lod_region(facade, rng)))
    return "".join(parts)


def read_region(facade, rng: random.Random) -> bytes:
    width, height = facade.get_width(), facade.get_height()
    x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
    return bytes(facade.get_display_region(x, y, rng.randint(1, width - x), rng.randint(1, height - y)))


def read_lod_region(facade, rng: random.Random) -> bytes:
    level = rng.randint(1, 3)
    width, height = facade.get_lod_size(level)
    x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
    return bytes(facade.get_display_lod_region(level, x, y, rng.randint(1, width - x), rng.randint(1, height - y)))


def run(seed: int, reader: Callable[[object, random.Random, int], str], steps: int = STEPS) -> list[str]:
    """What `reader` saw after each step of the sequence `seed`, as a list of short digests."""
    facade, ops = build(seed)
    reads = random.Random(seed ^ 0x5EED)
    seen = []
    for step in range(steps):
        operate(facade, ops)
        seen.append(reader(facade, reads, step))
    return seen


def sequence_digest(seed: int, steps: int = STEPS) -> str:
    """The golden of a sequence: one digest of everything `full_read` saw over its steps."""
    seen = run(seed, lambda facade, reads, step: full_read(facade, reads), steps)
    return hashlib.sha256("".join(seen).encode("ascii")).hexdigest()[:16]


def recompose_everything(facade) -> None:
    """Forces a total recomposition without changing the document: the paper colour is set to the one it has."""
    paper = facade.get_canvas_texture().background_color
    facade.set_background_color(paper.r, paper.g, paper.b, paper.a)


def pyramid(facade) -> list[bytes]:
    return [bytes(facade.get_display_pixel_buffer_lod(level)[0]) for level in (1, 2, 3)]


def lazy_differs_from_total(seed: int, steps: int = STEPS) -> tuple[int, str] | None:
    """Runs the sequence reading only windows, and every few steps (`1 + seed % 4`, so stale tiles pile up between
    the checks) compares the whole lazy picture and the pyramid with a total recomposition of the same document.
    None when they always agree; otherwise (step, what differs)."""
    facade, ops = build(seed)
    reads = random.Random(seed ^ 0x5EED)
    every = 1 + seed % 4
    for step in range(steps):
        operate(facade, ops)
        read_region(facade, reads)
        read_lod_region(facade, reads)
        if (step + 1) % every and step != steps - 1:
            continue
        lazy, lazy_levels = bytes(facade.get_pixel_buffer()), pyramid(facade)
        recompose_everything(facade)
        if lazy != bytes(facade.get_pixel_buffer()):
            return step, "picture"
        if lazy_levels != pyramid(facade):
            return step, "pyramid"
    return None
