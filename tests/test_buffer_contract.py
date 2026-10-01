"""Snapshots survive native mutations/destruction; malformed inputs never mutate."""

import gc
import weakref

import pytest
import aladyn_engine_native as native
from PySide6.QtWidgets import QApplication
from ui.infrastructure.bridge_client.aladyn import AladynBackend


@pytest.fixture
def facade():
    engine = native.PaintEngineFacade(8, 8)
    engine.paste_rgba_buffer_on_active_layer(0, 0, 8, 8, bytes([90, 60, 30, 255]) * 64)
    return engine


@pytest.mark.parametrize("accessor", [
    "get_pixel_buffer", "get_display_pixel_buffer", "get_display_region", "get_layer_pixel_buffer",
    "get_layer_thumbnail_buffer", "get_display_pixel_buffer_lod",
    "get_selection_mask_buffer", "get_transform_source_buffer",
    "get_shape_preview_buffer", "get_brush_height_preview_buffer",
    "get_canvas_height_preview_buffer",
])
def test_native_snapshots_survive_mutation_and_destruction(accessor):
    engine = native.PaintEngineFacade(8, 8)
    engine.paste_rgba_buffer_on_active_layer(0, 0, 8, 8, bytes([90, 60, 30, 255]) * 64)
    engine.select_rect(1, 1, 4, 4)
    for name in ("shape", "brush_height", "canvas_height"):
        getattr(engine, f"load_{name}_texture")(3, 2, bytes([23]) * 6)
    args = {"get_layer_pixel_buffer": (0,), "get_layer_thumbnail_buffer": (0, 3, 3),
            "get_display_pixel_buffer_lod": (1,), "get_display_region": (1, 1, 4, 4)}.get(accessor, ())
    if accessor == "get_transform_source_buffer":
        assert engine.begin_transform()
    result = getattr(engine, accessor)(*args)
    snapshot = result[0] if accessor == "get_display_pixel_buffer_lod" else result
    assert isinstance(snapshot, bytes)
    view = memoryview(snapshot)
    assert view.readonly
    expected = bytes(bytearray(snapshot))
    if engine.is_transform_active():
        assert engine.cancel_transform()
    engine.clear_selection()
    engine.clear_canvas()
    engine.resize_canvas(3, 5)
    engine.get_display_pixel_buffer_lod(1)
    for name in ("shape", "brush_height", "canvas_height"):
        getattr(engine, f"load_{name}_texture")(2, 3, bytes([199]) * 6)
    del engine, snapshot, result
    gc.collect()
    assert bytes(view) == expected


@pytest.mark.parametrize("getter", ["get_brush_profile", "get_canvas_texture", "get_stabilizer"])
def test_native_member_reference_keeps_owner_alive(getter):
    engine = native.PaintEngineFacade(3, 3)
    owner = weakref.ref(engine)
    member = getattr(engine, getter)()
    del engine
    gc.collect()
    assert owner() is not None
    del member
    gc.collect()
    assert owner() is None


@pytest.mark.parametrize("width,height,data", [
    (2, 2, b""), (2, 2, bytes(15)), (2, 2, bytes(17)),
    (0, 2, b""), (-1, 2, b""), (2**30, 4, b""),
])
def test_invalid_paste_preserves_pixels_and_history(facade, width, height, data):
    before = facade.get_layer_pixel_buffer(0)
    step = facade.get_undo_step_id()
    with pytest.raises(ValueError):
        facade.paste_rgba_buffer_on_active_layer(0, 0, width, height, data)
    assert facade.get_layer_pixel_buffer(0) == before
    assert facade.get_undo_step_id() == step


@pytest.mark.parametrize("name", ["shape", "brush_height", "canvas_height"])
@pytest.mark.parametrize("width,height,data", [(2, 3, bytes(5)), (2, 3, bytes(7)),
                                                   (-1, 3, b""), (2**30, 4, b"")])
def test_invalid_texture_preserves_previous_texture(facade, name, width, height, data):
    loader = getattr(facade, f"load_{name}_texture")
    preview = getattr(facade, f"get_{name}_preview_buffer")
    loader(2, 3, bytes([77]) * 6)
    with pytest.raises(ValueError):
        loader(width, height, data)
    assert preview() == bytes([77]) * 6


def test_paste_coordinate_and_thumbnail_overflow_rejected(facade):
    with pytest.raises(ValueError):
        facade.paste_rgba_buffer_on_active_layer(2**31 - 1, 0, 2, 2, bytes(16))
    with pytest.raises(ValueError):
        facade.get_layer_thumbnail_buffer(0, 2**30, 4)


def test_backend_images_and_buffers_survive_mdi_close():
    _app = QApplication.instance() or QApplication(["--platform", "offscreen"])
    backend = AladynBackend()
    backend.set_active_document_context("buffer-owner", 8, 8)
    assert backend.paste_rgba_buffer_on_active_layer(0, 0, 8, 8, bytes([90, 60, 30, 255]) * 64)
    backend.select_rect(1, 1, 4, 4)
    raw = backend.get_pixel_buffer()
    images = [backend.get_qimage(), backend.get_qimage_lod(0.25)[0],
              backend.get_selection_mask_qimage()]
    assert backend.begin_transform()
    images.append(backend.get_transform_source_qimage())
    expected = [bytes(image.constBits()) for image in images]
    raw_expected = bytes(bytearray(raw))
    assert backend.cancel_transform()
    backend.clear_selection()
    backend.resize(5, 7)
    backend.close_document_context("buffer-owner")
    backend.set_active_document_context("buffer-other", 3, 3)
    backend.clear_canvas()
    backend.close_document_context("buffer-other")
    del backend
    gc.collect()
    assert bytes(raw) == raw_expected
    assert [bytes(image.constBits()) for image in images] == expected


def test_backend_reports_native_paste_rejection():
    backend = AladynBackend()
    backend.set_active_document_context("paste-reject", 3, 3)
    try:
        backend.set_layer_lock(0, True)
        assert not backend.paste_rgba_buffer_on_active_layer(0, 0, 1, 1, bytes([2, 3, 4, 255]))
    finally:
        backend.close_document_context("paste-reject")


@pytest.mark.parametrize("setter,getter", [
    ("set_shape_texture", "get_shape_preview_buffer"),
    ("set_heightmap_texture", "get_brush_height_preview_buffer"),
])
def test_rgba_texture_bridge_preserves_rows_and_transparency(setter, getter):
    backend = AladynBackend()
    rgba = bytes([0, 0, 0, 255, 255, 255, 255, 255, 128, 128, 128, 255,
                  255, 255, 255, 0, 255, 255, 255, 128, 64, 64, 64, 255])
    getattr(backend, setter)(rgba, 3, 2)
    assert getattr(backend, getter)() == bytes([0, 255, 128, 0, 128, 64])
    with pytest.raises(ValueError):
        getattr(backend, setter)(rgba[:-1], 3, 2)
    assert getattr(backend, getter)() == bytes([0, 255, 128, 0, 128, 64])
