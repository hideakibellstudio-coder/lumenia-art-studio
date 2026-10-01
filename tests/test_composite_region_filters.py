"""A region composed after a stroke equals the composition of the whole canvas, whatever filters are in the stack.

An area filter (Gaussian blur, sharpen) reads its neighbours. To compose a dirty region the compositor inflates it by the
filters' reach, but until 2026-10-01 it wrote the whole inflated region to the output buffer, and the outer band, where
the filter lacked neighbours, came out wrong. Painting under or over a blur adjustment layer left a band of pixels
different from the full composition (deltas up to 53 levels on a noisy base, 56 of 400 random stacks), until something else
forced a recomposite. Found by the property test that undoes and redoes random operations and compares the canvas.

Now the region is composed with twice the reach as context, only the area the stroke can change (the region plus one
reach) is written, and the outer band is given back as it was.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

import aladyn_engine_native as native

WIDTH, HEIGHT = 150, 110


def _snapshot(facade) -> np.ndarray:
    return np.frombuffer(bytes(facade.get_pixel_buffer()), dtype=np.uint8).reshape(-1, 4).astype(int)


def _recompose_everything(facade) -> None:
    facade.set_layer_visibility(0, False)
    facade.set_layer_visibility(0, True)


def _noise(seed: int) -> bytes:
    texture = np.random.default_rng(seed).integers(0, 255, size=(HEIGHT, WIDTH, 4), dtype=np.uint8)
    texture[..., 3] = 255
    return texture.tobytes()


def _stroke(facade, rng: random.Random, size: float) -> None:
    facade.get_brush_profile().brush_size = size
    x, y = rng.uniform(30, 120), rng.uniform(25, 85)
    facade.begin_stroke_raw(x, y, 0.8, 0.0)
    for step in range(1, 14):
        facade.update_stroke_raw(x + step * 3, y + (step % 5) * 4, 0.7, step * 0.01)
    facade.end_stroke_raw()


def _worst_difference(facade) -> int:
    incremental = _snapshot(facade)
    _recompose_everything(facade)
    return int(np.abs(incremental - _snapshot(facade)).max())


@pytest.mark.parametrize("filter_type, params", [
    (2, [3.0, 0.0, 0.0]), (2, [10.0, 0.0, 0.0]), (2, [60.0, 0.0, 0.0]),   # Gaussian blur
    (4, [100.0, 0.0, 50.0]),                                              # sharpen
    (6, [8.0, 0.0, 0.0]),                                                  # pixelate
])
@pytest.mark.parametrize("paint", ["under the filter", "over the filter"])
def test_a_stroke_next_to_one_area_filter_leaves_the_canvas_as_the_full_composition_would(filter_type, params, paint):
    for seed in range(3):
        facade = native.PaintEngineFacade(WIDTH, HEIGHT)
        facade.paste_rgba_buffer_on_active_layer(0, 0, WIDTH, HEIGHT, _noise(seed))
        facade.add_layer("middle", -1)
        facade.set_filter_params(facade.add_filter_layer("filter", filter_type), params)
        facade.add_layer("top", -1)
        facade.select_layer(1 if paint == "under the filter" else facade.get_drawing_layer_count() - 1)
        _stroke(facade, random.Random(seed), 24.0)
        assert _worst_difference(facade) == 0


def test_random_stacks_of_layers_groups_and_filters_never_drift_from_the_full_composition():
    """The same property over random stacks: blend modes, opacity, groups, stacked filters, strokes at the edges."""
    for seed in range(40):
        rng = random.Random(seed)
        facade = native.PaintEngineFacade(WIDTH, HEIGHT)
        facade.paste_rgba_buffer_on_active_layer(0, 0, WIDTH, HEIGHT, _noise(seed))
        for _ in range(rng.randint(2, 6)):
            kind = rng.choice(["layer", "layer", "filter", "filter", "group"])
            if kind == "layer":
                facade.add_layer("layer", -1)
                index = facade.get_drawing_layer_count() - 1
                facade.set_layer_opacity(index, rng.choice([1.0, 0.7, 0.4]))
                facade.set_layer_blend_mode(index, rng.choice([0, 0, 1, 2, 3, 5]))
                facade.select_layer(index)
                color = bytes([rng.randint(0, 255), 90, 160, rng.choice([255, 140])])
                facade.paste_rgba_buffer_on_active_layer(rng.randint(0, 60), rng.randint(0, 40), 60, 40, color * 2400)
            elif kind == "filter":
                filter_type = rng.choice([0, 2, 2, 4, 6])
                params = {0: [rng.uniform(0, 360), rng.random(), rng.random()], 2: [float(rng.choice([1, 8, 20, 60])), 0.0, 0.0],
                          4: [rng.choice([30.0, 100.0]), 0.0, 50.0], 6: [float(rng.choice([2, 8, 16])), 0.0, 0.0]}[filter_type]
                facade.set_filter_params(facade.add_filter_layer("filter", filter_type), params)
            else:
                facade.set_layer_blend_mode(facade.add_group("group", -1), rng.choice([0, 1, 7]))
        painted = False
        for _ in range(rng.randint(1, 3)):
            target = rng.randrange(facade.get_drawing_layer_count())
            if facade.is_group(target) or facade.is_filter_layer(target):
                continue
            facade.select_layer(target)
            _stroke(facade, rng, rng.choice([8.0, 30.0, 70.0]))
            painted = True
        if painted:
            assert _worst_difference(facade) == 0, f"stack of seed {seed} drifted from the full composition"
