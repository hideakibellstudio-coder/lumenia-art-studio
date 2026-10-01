"""Opening a saved document reproduces the pixels that were saved.

Found by the application benchmark (2026-10-01): saving a document with a
default-colour soft stroke and opening it again failed with "restauração de
pixels não corresponde ao arquivo". Two causes, one on each side of the bridge:

  * `BufferPasteOrchestrator` blended in `double` and converted with a plain
    cast (truncation): blue 14 under alpha 227 came back as 13;
  * pixels with alpha 0 but non-zero RGB, which soft brushes leave on their
    fringe, are not pasted, so the restored layer never equalled the file byte
    for byte.

The engine must write the source pixel exactly when nothing is underneath, and
the restore must treat the RGB of a fully transparent pixel as not-data.
"""

from __future__ import annotations

import os

import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="native module not built in this environment"
)

SIZE = 64
COLORS = [(0, 0, 0), (255, 255, 255), (1, 2, 3), (10, 10, 14), (200, 100, 50),
          (37, 91, 173), (254, 1, 128), (13, 13, 13)]


def _every_alpha_with_every_colour() -> bytes:
    """255 alphas x 8 colours = 2040 pixels (the rest of the 64x64 layer stays empty)."""
    buffer = bytearray(SIZE * SIZE * 4)
    index = 0
    for alpha in range(1, 256):
        for r, g, b in COLORS:
            buffer[index * 4:index * 4 + 4] = bytes((r, g, b, alpha))
            index += 1
    return bytes(buffer)


def _fresh_engine():
    engine = native.PaintEngineFacade(SIZE, SIZE)
    engine.select_layer(0)
    return engine


def test_paste_onto_an_empty_layer_is_bit_exact():
    source = _every_alpha_with_every_colour()
    engine = _fresh_engine()
    assert engine.paste_rgba_buffer_on_active_layer(0, 0, SIZE, SIZE, source)
    restored = bytes(engine.get_layer_pixel_buffer(0))
    wrong = [i // 4 for i in range(0, len(source), 4) if restored[i:i + 4] != source[i:i + 4]]
    assert not wrong, f"{len(wrong)} pixels changed by the paste, first at index {wrong[0]}"


def test_a_fully_transparent_pixel_stays_fully_transparent():
    source = bytearray(SIZE * SIZE * 4)
    source[0:4] = bytes((10, 10, 14, 0))
    engine = _fresh_engine()
    engine.paste_rgba_buffer_on_active_layer(0, 0, SIZE, SIZE, bytes(source))
    assert bytes(engine.get_layer_pixel_buffer(0))[3] == 0


def test_paste_over_existing_ink_still_blends():
    """The fix must not turn the paste into a plain copy: over opaque pixels it blends."""
    engine = _fresh_engine()
    base = bytes((200, 0, 0, 255)) * (SIZE * SIZE)
    engine.paste_rgba_buffer_on_active_layer(0, 0, SIZE, SIZE, base)
    over = bytes((0, 0, 200, 128)) * (SIZE * SIZE)
    engine.paste_rgba_buffer_on_active_layer(0, 0, SIZE, SIZE, over)
    r, g, b, a = bytes(engine.get_layer_pixel_buffer(0))[0:4]
    assert a == 255 and 90 <= r <= 110 and 90 <= b <= 110, (r, g, b, a)


@pytest.fixture()
def backend(qapp, tmp_path, monkeypatch):
    """A real backend and a document manager, both put back as they were.

    Leaving documents or a backend behind is not harmless: a main window kept
    alive by another test reacts to the next "document modified" and calls the
    registered backend, which in a later test is a fake without `can_undo`.
    """
    monkeypatch.setenv("LUMENIA_CONFIG_PATH", os.fspath(tmp_path / "config.json"))
    from ui.core.document.manager import DocumentManager
    from ui.core.engine.registry import EngineRegistry
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    registry, manager = EngineRegistry.instance(), DocumentManager.instance()
    previous_backend = registry.get_backend()
    already_open = {doc.uid for doc in manager.documents()}
    registry.set_backend(AladynBackend())
    try:
        yield registry.get_backend(), manager
    finally:
        for doc in list(manager.documents()):
            if doc.uid not in already_open:
                manager.close_document(doc.uid)
        registry.set_backend(previous_backend)


def test_a_document_with_soft_strokes_opens_again(backend, tmp_path):
    """The case the benchmark hit: default colour, several layers, anti-aliased edges."""
    from ui.core.document.restore import restore_document
    from ui.core.document.serializer import DocumentSerializer

    engine, manager = backend
    doc = manager.new_document(SIZE * 4, SIZE * 4, "fidelity")
    engine.set_active_document_context(doc.uid, SIZE * 4, SIZE * 4)
    for i in range(2):
        doc.layer_manager.add_layer(f"L{i}")
    for layer in range(3):
        engine.select_layer(layer)
        engine.start_stroke(30 + layer * 30, 30, 0.8, 0.0)
        for j in range(20):
            engine.paint_stroke(30 + layer * 30 + j * 6, 30 + j * 5, 0.8, j * 0.004)
        engine.end_stroke()
    wanted_layers = [bytes(engine.get_layer_pixel_buffer(index)) for index in range(3)]
    path = tmp_path / "fidelity.lmn"
    DocumentSerializer.save(doc, engine, path)

    manifest, payloads = DocumentSerializer.read(path)
    reopened = manager.new_document(SIZE * 4, SIZE * 4, "fidelity-reopened")
    engine.set_active_document_context(reopened.uid, SIZE * 4, SIZE * 4)
    restore_document(reopened, engine, manifest, payloads)

    for index in range(len(manifest["layers"])):
        wanted = wanted_layers[index]
        got = bytes(engine.get_layer_pixel_buffer(index))
        visible_wanted = [wanted[i:i + 4] for i in range(0, len(wanted), 4) if wanted[i + 3]]
        visible_got = [got[i:i + 4] for i in range(0, len(got), 4) if got[i + 3]]
        assert visible_got == visible_wanted, f"layer {index} lost pixels on the way"
