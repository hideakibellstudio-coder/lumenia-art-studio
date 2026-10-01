"""The actions that open documents: they work, and they refuse what the engine cannot hold (S0.2, D2).

Opening a .lmn file raised TypeError from 2026-09-24 to 2026-10-01: `open_native_document`
passed `paper_texture_id` to `DocumentManager.new_document`, which had lost that parameter
in 23c503a. No test went through the action (the serializer and the restore were tested
separately), so the user's File > Open did nothing and the suite stayed green.

--- D2 ---

When the engine could not allocate the context of a new document (a 16384 px
canvas needs two 1 GiB buffers), the backend logged the error and returned.
The previously active context stayed active, the view showed the new document
anyway, and whatever the user did next went into the old one: opening an image
pasted it into the open document's layer, and opening a .lmn file removed the
open document's layers before restoring the new ones.

The failure now travels: the backend raises `EngineContextError`, the view
closes the document it could not give a context to and tells the user, and the
actions that create documents stop there.
"""

from __future__ import annotations

import hashlib
import os

import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="native module not built in this environment"
)

from ui.core.engine.errors import EngineContextError  # noqa: E402
from ui.core.engine.registry import EngineRegistry  # noqa: E402

LIMIT_PIXELS = 1_000_000  # what the simulated machine can allocate
HUGE = 2000               # 2000 x 2000 = 4 000 000 pixels


def _limit_memory(monkeypatch):
    """Make the native facade fail for big canvases, like an out-of-memory machine."""
    real = native.PaintEngineFacade

    def facade(width, height):
        if width * height > LIMIT_PIXELS:
            raise MemoryError("simulated out of memory")
        return real(width, height)

    facade.max_canvas_dimension = real.max_canvas_dimension  # the engine's own limit stays visible
    monkeypatch.setattr(native, "PaintEngineFacade", facade)


def _digest(buffer) -> str:
    return hashlib.sha256(bytes(buffer)).hexdigest()


def test_a_context_the_engine_cannot_allocate_raises_and_keeps_the_previous_one(monkeypatch):
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    backend = AladynBackend()
    backend.set_active_document_context("small", 200, 100)
    _limit_memory(monkeypatch)
    with pytest.raises(EngineContextError):
        backend.set_active_document_context("huge", HUGE, HUGE)
    assert backend.get_active_document_context() == "small"


@pytest.fixture()
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("LUMENIA_CONFIG_PATH", os.fspath(tmp_path / "config.json"))
    from tests.main_window_fixture import main_window_com_workspace

    win = main_window_com_workspace()
    already_open = {doc.uid for doc in win.dm.documents()}
    yield win
    for doc in list(win.dm.documents()):
        if doc.uid not in already_open:
            win.dm.close_document(doc.uid)


def _open_document_with_ink(window):
    """A small open document with a stroke on its layer, and the digest of that layer."""
    backend = EngineRegistry.instance().get_backend()
    previous = window.dm.new_document(200, 100, "previous")
    backend.select_layer(0)
    backend.begin_stroke_raw(30, 30, 0.8, 0.0)
    for i in range(1, 20):
        backend.update_stroke_raw(30 + i * 6, 30 + i * 2, 0.8, i * 0.004)
    backend.end_stroke()
    return backend, previous, _digest(backend.get_layer_pixel_buffer(0))


def test_opening_an_image_the_engine_cannot_hold_leaves_the_open_document_alone(window, tmp_path, monkeypatch):
    from PySide6 import QtGui, QtWidgets

    backend, previous, ink = _open_document_with_ink(window)
    documents_before = [doc.uid for doc in window.dm.documents()]
    image = QtGui.QImage(HUGE, HUGE, QtGui.QImage.Format_RGBA8888)
    image.fill(QtGui.QColor(200, 30, 30))
    path = tmp_path / "huge.png"
    assert image.save(os.fspath(path))

    _limit_memory(monkeypatch)
    window.documents.open_image(os.fspath(path))
    QtWidgets.QApplication.processEvents()  # a vista fecha o documento recusado depois da emissão

    assert [doc.uid for doc in window.dm.documents()] == documents_before, "a document the engine could not host stayed open"
    assert window.dm.active_document() is previous
    assert backend.get_active_document_context() == previous.uid
    assert _digest(backend.get_layer_pixel_buffer(0)) == ink, "the image was pasted into the open document"
    assert "memória" in window.status_bar.currentMessage().lower()


def test_opening_a_native_document_the_engine_cannot_hold_leaves_the_open_document_alone(window, tmp_path, monkeypatch):
    from PySide6 import QtWidgets

    from ui.core.document.serializer import DocumentSerializer

    backend, previous, ink = _open_document_with_ink(window)
    big = window.dm.new_document(HUGE, HUGE, "big", activate=False)
    backend.set_active_document_context(big.uid, HUGE, HUGE)
    path = tmp_path / "big.lmn"
    DocumentSerializer.save(big, backend, path)
    window.dm.close_document(big.uid)
    backend.close_document_context(big.uid)
    window.dm.set_active_document(previous.uid)
    layers_before = backend.get_drawing_layer_count()
    documents_before = [doc.uid for doc in window.dm.documents()]

    _limit_memory(monkeypatch)
    assert window.documents.open_native_document(os.fspath(path)) is False
    QtWidgets.QApplication.processEvents()

    assert [doc.uid for doc in window.dm.documents()] == documents_before
    assert backend.get_active_document_context() == previous.uid
    assert backend.get_drawing_layer_count() == layers_before, "the open document's layers were replaced"
    assert _digest(backend.get_layer_pixel_buffer(0)) == ink


def test_a_saved_document_opens_through_the_open_action(window, tmp_path):
    """The path that was broken: File > Open of a .lmn, with every layer back."""
    from ui.core.document.serializer import DocumentSerializer

    backend, original, ink = _open_document_with_ink(window)
    original.layer_manager.add_layer("second")
    path = tmp_path / "saved.lmn"
    DocumentSerializer.save(original, backend, path)
    window.dm.close_document(original.uid)
    backend.close_document_context(original.uid)

    assert window.documents.open_native_document(os.fspath(path)) is True

    reopened = window.dm.active_document()
    assert reopened is not None and reopened.uid != original.uid
    assert [layer.name for layer in reopened.layer_manager.layers][-1] == "second"
    assert backend.get_drawing_layer_count() == 2
    assert _digest(backend.get_layer_pixel_buffer(0)) == ink, "the stroke did not come back as saved"
