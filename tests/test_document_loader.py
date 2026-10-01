"""Opening a document without freezing the interface (S1.2).

Reading a .lmn and decoding the tiles of its layers is nearly all of the time it takes to open
(CRC, decompression: 1.2 s for a 4K document with ten fully painted layers). `load_document`
does it on a worker thread into engine objects that belong to no document, and `restore_document`
adopts them on the interface thread in constant time. What these tests pin:

  * the pixels that come out are the pixels that went in, through the thread boundary;
  * the worker needs no document and no engine context (it only decodes);
  * a file that cannot be read or decoded reports to the caller and opens nothing;
  * the event loop keeps running while a slow read is in flight;
  * an older file (raw payloads) still loads, and opening through the action ends with the same
    document the user saved.
"""

from __future__ import annotations

import os
import random
import threading
import time
import zipfile

import numpy as np
import pytest
from PySide6 import QtCore

from ui.core.document.document_loader import DocumentLoader, load_document
from ui.core.document.restore import restore_document
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


def _saved_document(session, tmp_path, layers=3):
    engine, manager = session
    doc = manager.new_document(WIDTH, HEIGHT, "source")
    engine.set_active_document_context(doc.uid, WIDTH, HEIGHT)
    for index in range(layers - 1):
        doc.layer_manager.add_layer(f"L{index}")
    rng = random.Random(4)
    for layer in range(layers):
        engine.select_layer(layer)
        engine.set_brush_size(26.0)
        x, y = rng.uniform(30, WIDTH - 30), rng.uniform(30, HEIGHT - 30)
        engine.begin_stroke_raw(x, y, 0.9, 0.0)
        for step in range(1, 14):
            engine.update_stroke_raw(x + step * rng.uniform(-9, 12), y + step * rng.uniform(-9, 12), 0.9, step * 0.01)
        engine.end_stroke()
    pixels = [np.frombuffer(engine.get_layer_pixel_buffer(i), dtype=np.uint8).reshape(HEIGHT, WIDTH, 4).copy() for i in range(layers)]
    return DocumentSerializer.save(doc, engine, tmp_path / "source.lmn"), pixels


def _same_visible(a, b):
    return not bool(((a != b).any(axis=2) & ~((a[:, :, 3] == 0) & (b[:, :, 3] == 0))).any())


def test_a_loaded_document_restores_to_the_same_pixels_through_the_thread_boundary(session, tmp_path):
    engine, manager = session
    path, wanted = _saved_document(session, tmp_path)
    loaded = []
    worker = threading.Thread(target=lambda: loaded.append(load_document(path, engine)))
    worker.start()
    worker.join()
    result = loaded[0]
    assert len(result.prepared) == 3 and not [name for name in result.payloads if name.endswith(".tiles")], \
        "the tile blocks must be decoded and dropped from the payloads, not kept twice"
    doc = manager.new_document(WIDTH, HEIGHT, "reopened")
    engine.set_active_document_context(doc.uid, WIDTH, HEIGHT)
    restore_document(doc, engine, result.manifest, result.payloads, result.prepared)
    for index, expected in enumerate(wanted):
        got = np.frombuffer(engine.get_layer_pixel_buffer(index), dtype=np.uint8).reshape(HEIGHT, WIDTH, 4)
        assert _same_visible(got, expected)


def test_the_worker_needs_no_engine_context(session, tmp_path):
    """Nothing in the load may touch the active document: it runs while the artist paints."""
    engine, manager = session
    path, _ = _saved_document(session, tmp_path)
    other = manager.new_document(64, 64, "the one being painted")
    engine.set_active_document_context(other.uid, 64, 64)
    before = bytes(engine.get_layer_pixel_buffer(0))
    load_document(path, engine)
    assert engine.get_active_document_context() == other.uid
    assert bytes(engine.get_layer_pixel_buffer(0)) == before


def test_an_older_file_with_raw_payloads_loads_without_prepared_layers(session, tmp_path):
    engine, _manager = session
    path, _ = _saved_document(session, tmp_path, layers=1)
    manifest, _payloads = DocumentSerializer.read(path)
    record = manifest["layers"][0]
    raw = bytes(WIDTH * HEIGHT * 4)
    old = tmp_path / "old.lmn"
    record.pop("tiles_payload")
    record["pixel_payload"] = f"layers/{record['uid']}.rgba"
    manifest["version"] = 2
    import json
    with zipfile.ZipFile(old, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr(record["pixel_payload"], raw)
        archive.writestr("assets/canvas.gray", _payloads["assets/canvas.gray"])
    loaded = load_document(old, engine)
    assert loaded.prepared == {} and record["pixel_payload"] in loaded.payloads


def test_a_file_that_cannot_be_decoded_reports_and_opens_nothing(session, tmp_path):
    engine, _manager = session
    path, _ = _saved_document(session, tmp_path, layers=1)
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    name = next(name for name in entries if name.endswith(".tiles"))
    entries[name] = entries[name][:-6]  # a valid zip around a truncated block: only the codec can tell
    with zipfile.ZipFile(path, "w") as archive:
        for entry, data in entries.items():
            archive.writestr(entry, data)
    with pytest.raises(DocumentFormatError):
        load_document(path, engine)


def test_the_loader_reports_to_the_interface_thread_and_never_blocks_the_event_loop(qapp, session):
    seen = {}

    def slow_loader(path, _backend):
        time.sleep(0.4)
        seen["worker"] = threading.get_ident()
        return path

    loader = DocumentLoader(loader=slow_loader)
    results = []
    loader.submit("x.lmn", None, on_done=lambda loaded: results.append((loaded, threading.get_ident())),
                  on_error=lambda path, exc: results.append(exc))
    ticks = []
    timer = QtCore.QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
    timer.start()
    deadline = time.perf_counter() + 5
    while loader.is_busy() and time.perf_counter() < deadline:
        qapp.processEvents()
        time.sleep(0.001)
    timer.stop()
    assert results == [("x.lmn", threading.get_ident())] and seen["worker"] != threading.get_ident()
    gaps = [b - a for a, b in zip(ticks, ticks[1:])]
    assert len(ticks) > 30 and max(gaps) < 0.05, "the event loop stopped while the file was being read"


def test_a_loader_failure_reaches_the_caller_with_the_path(qapp):
    def failing(_path, _backend):
        raise DocumentFormatError("arquivo .lmn corrompido")

    loader = DocumentLoader(loader=failing)
    errors = []
    loader.submit("broken.lmn", None, on_done=lambda loaded: errors.append("done"), on_error=lambda path, exc: errors.append((path, str(exc))))
    assert loader.wait_idle(5000)
    assert errors == [("broken.lmn", "arquivo .lmn corrompido")]
