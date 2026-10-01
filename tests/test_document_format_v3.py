"""The .lmn v3 file: layers as blocks of tiles, and the older files that still open (S1.2).

v1 and v2 stored the whole canvas of every layer as raw RGBA inside the ZIP. v3 stores only
the painted tiles, in LZ4 (`engine/core/canvas/TileGridCodec.hpp`). What these tests pin:

  * a v3 file opens to the same visible pixels, with every layer property;
  * a v2 file (raw payloads) written by hand still opens, and saving it again makes it v3;
  * the file is as small as what is painted, not as big as the canvas;
  * the reader refuses a v3 file that lies about its payloads, and a block that does not
    match the document is refused by the restore, never half-applied;
  * the second half of a save runs on another thread while the artist paints, and what
    it writes is the document as it was when the first half ran.
"""

from __future__ import annotations

import json
import os
import random
import threading
import zipfile

import numpy as np
import pytest

from ui.core.document.restore import restore_document
from ui.core.document.save_capture import capture_document
from ui.core.document.schema import DocumentFormatError
from ui.core.document.serializer import DocumentSerializer

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

WIDTH, HEIGHT = 301, 203


@pytest.fixture()
def session(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("LUMENIA_CONFIG_PATH", os.fspath(tmp_path / "config.json"))
    from ui.core.document.manager import DocumentManager
    from ui.core.engine.registry import EngineRegistry
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    registry, manager = EngineRegistry.instance(), DocumentManager.instance()
    previous = registry.get_backend()
    already_open = {doc.uid for doc in manager.documents()}
    registry.set_backend(AladynBackend())
    try:
        yield registry.get_backend(), manager
    finally:
        for doc in list(manager.documents()):
            if doc.uid not in already_open:
                manager.close_document(doc.uid)
        registry.set_backend(previous)


def _paint(engine, rng: random.Random, strokes: int = 4, size: float = 22.0) -> None:
    engine.set_brush_size(size)
    for _ in range(strokes):
        x, y = rng.uniform(20, WIDTH - 20), rng.uniform(20, HEIGHT - 20)
        engine.begin_stroke_raw(x, y, 0.9, 0.0)
        for step in range(1, 16):
            engine.update_stroke_raw(x + step * rng.uniform(-8, 12), y + step * rng.uniform(-8, 12), 0.9, step * 0.01)
        engine.end_stroke()


def _document(manager, engine, name="v3", layers=3, seed=1):
    doc = manager.new_document(WIDTH, HEIGHT, name)
    engine.set_active_document_context(doc.uid, WIDTH, HEIGHT)
    for index in range(layers - 1):
        doc.layer_manager.add_layer(f"L{index}")
    rng = random.Random(seed)
    for layer in range(layers):
        engine.select_layer(layer)
        _paint(engine, rng)
    return doc


def _layers(engine, count) -> list[np.ndarray]:
    return [np.frombuffer(engine.get_layer_pixel_buffer(i), dtype=np.uint8).reshape(HEIGHT, WIDTH, 4).copy() for i in range(count)]


def _same_visible(a: np.ndarray, b: np.ndarray) -> bool:
    return not bool(((a != b).any(axis=2) & ~((a[:, :, 3] == 0) & (b[:, :, 3] == 0))).any())


def _reopen(manager, engine, path, name="reopened"):
    manifest, payloads = DocumentSerializer.read(path)
    doc = manager.new_document(manifest["width"], manifest["height"], name)
    engine.set_active_document_context(doc.uid, manifest["width"], manifest["height"])
    restore_document(doc, engine, manifest, payloads)
    return doc, manifest


# -- a v3 file ------------------------------------------------------------------

def test_a_saved_document_opens_to_the_same_visible_pixels_and_properties(session, tmp_path):
    engine, manager = session
    doc = _document(manager, engine)
    doc.layer_manager.layers[1].opacity = 0.4
    engine.set_layer_opacity(1, 0.4)
    wanted = _layers(engine, 3)
    path = DocumentSerializer.save(doc, engine, tmp_path / "v3.lmn")

    reopened, manifest = _reopen(manager, engine, path)
    assert manifest["version"] == 3
    assert all("tiles_payload" in record and "pixel_payload" not in record for record in manifest["layers"])
    for got, expected in zip(_layers(engine, 3), wanted):
        assert _same_visible(got, expected)
    assert engine.get_layer_info(1)["opacity"] == pytest.approx(0.4)
    assert [layer.uid for layer in reopened.layer_manager.layers] == [layer.uid for layer in doc.layer_manager.layers]


def test_the_file_is_as_big_as_what_is_painted_not_as_the_canvas(session, tmp_path):
    engine, manager = session
    doc = manager.new_document(4000, 3000, "big-and-empty")
    engine.set_active_document_context(doc.uid, 4000, 3000)
    for index in range(7):
        doc.layer_manager.add_layer(f"L{index}")
    path = DocumentSerializer.save(doc, engine, tmp_path / "empty.lmn")
    with zipfile.ZipFile(path) as archive:
        layer_bytes = [info.file_size for info in archive.infolist() if info.filename.endswith(".tiles")]
    assert layer_bytes == [24] * 8, "a blank layer is its header and nothing else, whatever the canvas size"
    # 8 raw layers would be 384 MB; what remains is the paper texture and the manifest
    assert os.path.getsize(path) < 512 * 1024


def test_a_fully_painted_noise_layer_costs_about_its_raw_size_and_comes_back_exactly(session, tmp_path):
    engine, manager = session
    doc = manager.new_document(WIDTH, HEIGHT, "noise")
    engine.set_active_document_context(doc.uid, WIDTH, HEIGHT)
    rng = np.random.default_rng(3)
    noise = rng.integers(0, 256, size=(HEIGHT, WIDTH, 4), dtype=np.uint8)
    noise[:, :, 3] = 255
    engine.paste_rgba_buffer_on_active_layer(0, 0, WIDTH, HEIGHT, noise.tobytes())
    path = DocumentSerializer.save(doc, engine, tmp_path / "noise.lmn")
    with zipfile.ZipFile(path) as archive:
        stored = archive.getinfo("layers/1.tiles").file_size
    # 301 x 203 px is 3 x 2 tiles: the noise itself does not compress (the raw codec takes over, so it
    # is not inflated) and the empty margin of the edge tiles does. A hair above the raw bytes of the canvas.
    assert stored < WIDTH * HEIGHT * 4 * 1.02
    reopened, _ = _reopen(manager, engine, path)
    assert _layers(engine, 1)[0].tobytes() == noise.tobytes()
    assert reopened is not None


# -- the older file -----------------------------------------------------------------

def _write_v2(path, doc, pixels: dict[int, bytes]) -> None:
    """A .lmn as v2 wrote it: the manifest and one raw RGBA entry per layer."""
    layers = []
    for layer in doc.layer_manager.layers:
        layers.append({"uid": layer.uid, "name": layer.name, "parent_uid": None, "is_group": False, "is_filter": False,
                       "visible": True, "locked": False, "opacity": 1.0, "blend_mode": layer.blend_mode,
                       "alpha_locked": False, "clipping_mask": False, "pixel_payload": f"layers/{layer.uid}.rgba"})
    manifest = {"format": "lmn", "version": 2, "name": "old", "width": WIDTH, "height": HEIGHT, "dpi": 300,
                "paper": {"color": [255, 255, 255, 255], "visible": True, "texture_id": 0, "texture_enabled": False},
                "layers": layers, "active_uid": layers[0]["uid"], "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0, "rotation": 0.0,
                "guide_state": {}, "sym_state": {}, "color_profile_id": 0, "color_profile_payload": None,
                "selection_payload": None, "canvas_resource": None}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for layer in layers:
            archive.writestr(layer["pixel_payload"], pixels[layer["uid"]])


def test_a_v2_file_with_raw_payloads_still_opens_and_saving_it_again_makes_it_v3(session, tmp_path):
    engine, manager = session
    source = _document(manager, engine, "to-be-old", layers=2, seed=5)
    wanted = _layers(engine, 2)
    old_path = tmp_path / "old.lmn"
    _write_v2(old_path, source, {layer.uid: wanted[i].tobytes() for i, layer in enumerate(source.layer_manager.layers)})

    reopened, manifest = _reopen(manager, engine, old_path)
    assert manifest["version"] == 3, "the reader migrates the manifest"
    assert all("pixel_payload" in record for record in manifest["layers"]), "the payloads are not rewritten by the migration"
    for got, expected in zip(_layers(engine, 2), wanted):
        assert _same_visible(got, expected)

    new_path = DocumentSerializer.save(reopened, engine, tmp_path / "new.lmn")
    again, saved_manifest = _reopen(manager, engine, new_path, "again")
    assert all("tiles_payload" in record for record in saved_manifest["layers"])
    for got, expected in zip(_layers(engine, 2), wanted):
        assert _same_visible(got, expected)
    assert again is not None


# -- what the reader refuses ------------------------------------------------------------

def _rewrite(path, manifest_changes=None, replace=None, drop=()):
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(entries["manifest.json"])
    for key, value in (manifest_changes or {}).items():
        manifest[key] = value
    entries["manifest.json"] = json.dumps(manifest).encode()
    entries.update(replace or {})
    for name in drop:
        entries.pop(name)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return manifest


@pytest.fixture()
def saved(session, tmp_path):
    engine, manager = session
    doc = _document(manager, engine, "saved", layers=2)
    return engine, manager, DocumentSerializer.save(doc, engine, tmp_path / "saved.lmn")


def _layer_records(path):
    with zipfile.ZipFile(path) as archive:
        return json.loads(archive.read("manifest.json"))["layers"]


def _with_record_change(path, index, **changes):
    records = _layer_records(path)
    records[index].update(changes)
    return _rewrite(path, {"layers": records})


def test_a_layer_that_declares_pixels_two_ways_is_refused(saved):
    _engine, _manager, path = saved
    _with_record_change(path, 0, pixel_payload="layers/1.rgba")
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


@pytest.mark.parametrize("change", [{"tiles_payload": "layers/99.tiles"}, {"tiles_payload": "layers/1.rgba"},
                                    {"tiles_payload": "../escape.tiles"}])
def test_a_payload_outside_the_layers_own_name_is_refused(saved, change):
    _engine, _manager, path = saved
    _with_record_change(path, 0, **change)
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


def test_a_missing_or_extra_entry_is_refused(saved):
    _engine, _manager, path = saved
    name = _layer_records(path)[0]["tiles_payload"]
    _rewrite(path, drop=[name])
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


def test_an_undeclared_entry_is_refused(saved):
    _engine, _manager, path = saved
    _rewrite(path, replace={"layers/extra.tiles": b"LMNT" + bytes(20)})
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


@pytest.mark.parametrize("block", [b"", b"LMNT", b"XXXX" + bytes(40), b"LMNT" + bytes(20) + b"x" * (2 * 1024 * 1024 * 40)])
def test_a_tile_block_with_the_wrong_size_or_magic_is_refused(saved, block):
    _engine, _manager, path = saved
    name = _layer_records(path)[0]["tiles_payload"]
    _rewrite(path, replace={name: block})
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


def test_a_group_cannot_carry_tiles(saved):
    _engine, _manager, path = saved
    _with_record_change(path, 0, is_group=True)
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


def test_a_block_that_does_not_match_the_document_is_refused_by_the_restore(session, tmp_path):
    engine, manager = session
    doc = _document(manager, engine, "mismatch", layers=1)
    path = DocumentSerializer.save(doc, engine, tmp_path / "mismatch.lmn")
    manifest, payloads = DocumentSerializer.read(path)
    smaller = manager.new_document(100, 100, "smaller")
    engine.set_active_document_context(smaller.uid, 100, 100)
    manifest = dict(manifest, width=100, height=100)
    with pytest.raises(DocumentFormatError):
        restore_document(smaller, engine, manifest, payloads)


def test_a_structurally_broken_block_inside_a_valid_zip_is_refused_by_the_restore(session, tmp_path):
    engine, manager = session
    doc = _document(manager, engine, "broken", layers=1)
    path = DocumentSerializer.save(doc, engine, tmp_path / "broken.lmn")
    manifest, payloads = DocumentSerializer.read(path)
    name = manifest["layers"][0]["tiles_payload"]
    payloads[name] = payloads[name][:-5]  # the zip's CRC would have caught it on disk; here only the codec can
    target = manager.new_document(WIDTH, HEIGHT, "target")
    engine.set_active_document_context(target.uid, WIDTH, HEIGHT)
    with pytest.raises(DocumentFormatError):
        restore_document(target, engine, manifest, payloads)


def test_a_flipped_byte_on_disk_is_caught_by_the_archive(saved):
    _engine, _manager, path = saved
    data = bytearray(open(path, "rb").read())
    data[len(data) // 3] ^= 0xFF
    with open(path, "wb") as stream:
        stream.write(data)
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


def test_verify_checks_a_file_without_loading_it_and_catches_a_flipped_byte(saved):
    _engine, _manager, path = saved
    assert DocumentSerializer.verify(path) is None
    data = bytearray(open(path, "rb").read())
    data[len(data) // 3] ^= 0xFF
    with open(path, "wb") as stream:
        stream.write(data)
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.verify(path)


# -- the two halves of a save --------------------------------------------------------------

def test_the_second_half_runs_on_another_thread_and_writes_the_document_as_it_was_captured(session, tmp_path):
    engine, manager = session
    doc = _document(manager, engine, "threaded", layers=3, seed=9)
    wanted = _layers(engine, 3)
    capture = capture_document(doc, engine, tmp_path / "threaded.lmn")  # the first half: this thread
    written, errors = [], []

    def second_half():
        try:
            written.append(DocumentSerializer.write(capture))
        except Exception as exc:  # noqa: BLE001 -- the test reports it
            errors.append(exc)

    worker = threading.Thread(target=second_half)
    worker.start()
    rng = random.Random(90)
    while worker.is_alive():  # the artist keeps painting on every layer while the file is written
        for layer in range(3):
            engine.select_layer(layer)
            _paint(engine, rng, strokes=1, size=40.0)
    worker.join()
    assert not errors and written
    assert not all(_same_visible(a, b) for a, b in zip(_layers(engine, 3), wanted)), "the live document must have moved on"

    reopened, _ = _reopen(manager, engine, written[0], "from-the-thread")
    for got, expected in zip(_layers(engine, 3), wanted):
        assert _same_visible(got, expected)
    assert reopened is not None


def test_the_capture_remembers_the_revision_it_was_taken_at(session, tmp_path):
    engine, manager = session
    doc = _document(manager, engine, "revision", layers=1)
    capture = capture_document(doc, engine, tmp_path / "revision.lmn")
    assert capture.revision == doc.revision and capture.uid == doc.uid
    doc.mark_dirty("edit")
    assert doc.revision == capture.revision + 1


def test_a_capture_is_refused_when_the_engine_and_the_document_disagree(session, tmp_path):
    engine, manager = session
    doc = _document(manager, engine, "diverged", layers=2)
    engine.add_layer("only in the engine", -1)  # a layer the document does not know
    with pytest.raises(DocumentFormatError):
        capture_document(doc, engine, tmp_path / "diverged.lmn")
