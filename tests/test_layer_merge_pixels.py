"""Merging a layer down and flattening a group give the same pixels as before (S2, Compositor seal).

`LayerMerger::flattenGroup` (cyclomatic complexity 32) and `mergeLayerDown` (19) were split into
named steps. The existing layer tests count layers and check the engine and the document agree;
none looked at the pixels a merge produces. This one does, through the real engine, for the cases
the maths branches on: opacity and blend mode of the upper layer, a clipping mask (only where the
base has pixels), a filter layer rasterized into the layer below, and a group with a nested
group, a hidden child and an opacity chain. The digests were recorded before the split.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

from ui.core.document.layer_blend_mode import LayerBlendMode  # noqa: E402
from ui.infrastructure.bridge_client.aladyn import AladynBackend  # noqa: E402

SIZE = 160  # more than one 128-px tile each way, so the merge crosses tile seams


@pytest.fixture()
def backend():
    backend = AladynBackend()
    backend.set_active_document_context("merge-pixels", SIZE, SIZE)
    return backend


def _scene(seed: int, covers: float) -> bytes:
    """Deterministic RGBA with soft alpha; `covers` is the share of the canvas that has pixels."""
    rng = np.random.default_rng(seed)
    pixels = rng.integers(0, 256, size=(SIZE, SIZE, 4), dtype=np.uint8)
    pixels[..., 3] = np.where(rng.random((SIZE, SIZE)) < covers, pixels[..., 3] | 1, 0)
    pixels[:, SIZE // 2:, 3] = (pixels[:, SIZE // 2:, 3] // 2) * (pixels[:, SIZE // 2:, 3] > 0)  # soft half
    return pixels.tobytes()


def _layer(backend, index: int, seed: int, covers: float = 0.6) -> None:
    assert backend.select_layer(index)
    assert backend.paste_rgba_buffer_on_active_layer(0, 0, SIZE, SIZE, _scene(seed, covers))


def _digest(backend, index: int) -> str:
    return hashlib.sha256(bytes(backend.get_layer_pixel_buffer(index))).hexdigest()


def _three_layers(backend) -> None:
    backend.add_layer("one", -1)
    backend.add_layer("two", -1)
    backend.add_layer("three", -1)
    for index, seed in ((1, 11), (2, 22), (3, 33)):
        _layer(backend, index, seed)


def merge_opacity_and_blend(backend) -> str:
    _three_layers(backend)
    backend.set_layer_opacity(2, 0.6)
    backend.set_layer_blend_mode(2, LayerBlendMode.MULTIPLY)
    assert backend.merge_layer_down(2)
    return _digest(backend, 1)


def merge_clipping_mask(backend) -> str:
    _three_layers(backend)
    backend.set_layer_clipping_mask(2, True)
    backend.set_layer_opacity(2, 0.8)
    assert backend.merge_layer_down(2)
    return _digest(backend, 1)


def merge_filter_layer(backend) -> str:
    backend.add_layer("base", -1)
    _layer(backend, 1, 44)
    assert backend.add_filter_layer("invert", 5, -1) >= 0
    assert backend.merge_layer_down(2)
    return _digest(backend, 1)


def flatten_nested_group(backend) -> str:
    # 0 paper | 1 group (0.8) | 2 child (0.5) | 3 nested group (0.7) | 4 grandchild | 5 hidden child
    # | 6 outside the group | 7 hidden nested group | 8 its child (visible, but under a hidden group)
    backend.add_group("group", -1)
    backend.add_layer("child", -1)
    backend.add_group("inner", -1)
    backend.add_layer("grandchild", -1)
    backend.add_layer("hidden", -1)
    backend.add_layer("outside", -1)
    backend.add_group("hidden group", -1)
    backend.add_layer("ghost", -1)
    for index, seed in ((2, 55), (4, 66), (5, 77), (6, 88), (8, 99)):
        _layer(backend, index, seed)
    assert backend.set_layer_parents([-1, -1, 1, 1, 3, 1, -1, 1, 7])
    backend.set_layer_opacity(1, 0.8)
    backend.set_layer_opacity(2, 0.5)
    backend.set_layer_opacity(3, 0.7)
    backend.set_layer_visibility(5, False)
    backend.set_layer_visibility(7, False)
    assert backend.flatten_group(1)
    count = backend.get_drawing_layer_count()
    return f"{count}:{_digest(backend, 1)}:{_digest(backend, 2)}"


SCENARIOS = {
    "merge_opacity_and_blend": (merge_opacity_and_blend, "f122bd40083bfbadb6bc6971cd08d49f6fd394d569d1231d3f35782389af4230"),
    "merge_clipping_mask": (merge_clipping_mask, "2b3602e5d61e83ee2d02abe9ad38b3483433a6643cef42d67fceb64dec3665de"),
    "merge_filter_layer": (merge_filter_layer, "dd9a09eb159d102e1a57d96a7e83c7f9ec63831e5991e64ec3ce25e3ece7b366"),
    "flatten_nested_group": (flatten_nested_group, (
        "3:0e286af335447a0c3655695ba805bef85e0c26d8641b90be1c0b7661055a2578:81d6183b2cea0d96bbf7253f4bfb6f64a20e5ab2d93bd9f6bc85f47360e0839a"
    )),
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_a_merge_gives_the_recorded_pixels(backend, name):
    scenario, recorded = SCENARIOS[name]
    assert scenario(backend) == recorded
