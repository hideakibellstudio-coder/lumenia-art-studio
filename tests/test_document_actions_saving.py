"""Saving from the interface no longer freezes it, and no edit or document is lost on the way (S1.2).

`DocumentActions.save_active` takes the document in a few milliseconds and hands the writing to
the `DocumentSaver`. What can go wrong with that split, each pinned here:

  * the document must stay dirty until the file is written and checked, and an edit made while
    it is written must keep it dirty (the file holds the document as it was when saved);
  * a failure must leave the document open and dirty, say so, and never close it;
  * "save and close" closes only after the file is there;
  * quitting waits for what is being written;
  * a second Ctrl+S before the first file exists must not ask for a name again.
"""

from __future__ import annotations

import os
import time

import pytest
from PySide6 import QtWidgets

from ui.core.document.document_loader import DocumentLoader
from ui.core.document.document_saver import DocumentSaver
from ui.core.document.serializer import DocumentSerializer

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

SIZE = 96


class _Dialog:
    """Stands in for CloseDocumentDialog: the user always picks `choice`."""
    choice = None
    SAVE, DISCARD, CANCEL = 1, 2, 3

    def __init__(self, _name, _parent=None):
        self.result_code = type(self).choice

    def exec(self):
        return QtWidgets.QDialog.Accepted


@pytest.fixture()
def session(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("LUMENIA_CONFIG_PATH", os.fspath(tmp_path / "config.json"))
    from ui.boundary.orchestrator.document_actions import DocumentActions
    from ui.core.document.manager import DocumentManager
    from ui.core.engine.registry import EngineRegistry
    from ui.infrastructure.bridge_client.aladyn import AladynBackend
    import ui.core.screens.close_document_dialog as close_dialog

    monkeypatch.setattr(close_dialog, "CloseDocumentDialog", _Dialog)
    registry, manager = EngineRegistry.instance(), DocumentManager.instance()
    previous = registry.get_backend()
    already_open = {doc.uid for doc in manager.documents()}
    backend = AladynBackend()
    registry.set_backend(backend)
    window = QtWidgets.QWidget()
    messages = []

    class Env:
        pass

    env = Env()
    env.backend, env.manager, env.messages, env.window = backend, manager, messages, window
    env.slow = 0.0
    env.fail = False
    env.written = []

    def writer(capture):
        time.sleep(env.slow)
        if env.fail:
            raise OSError("disk full")
        env.written.append(capture.revision)
        return DocumentSerializer.write(capture)

    env.saver = DocumentSaver(window, writer=writer)
    env.actions = DocumentActions(window, manager, lambda: backend, None, None, env.saver, DocumentLoader(window))
    env.actions.statusMessage.connect(lambda text, _ms: messages.append(text))
    env.saved = []
    env.actions.documentSaved.connect(env.saved.append)

    def new_document(name="doc"):
        doc = manager.new_document(SIZE, SIZE, name)
        backend.set_active_document_context(doc.uid, SIZE, SIZE)
        backend.select_layer(0)
        backend.start_stroke(10, 10, 0.9, 0.0)
        for step in range(1, 12):
            backend.paint_stroke(10 + step * 5, 10 + step * 4, 0.9, step * 0.01)
        backend.end_stroke()
        doc.mark_dirty("stroke")
        return doc

    env.new_document = new_document
    try:
        yield env
    finally:
        env.saver.wait_idle(10000)
        for doc in list(manager.documents()):
            if doc.uid not in already_open:
                manager.close_document(doc.uid)
        registry.set_backend(previous)
        window.deleteLater()


def _path(tmp_path, name="a.lmn"):
    return os.fspath(tmp_path / name)


def test_saving_is_started_at_once_and_the_document_is_clean_only_when_the_file_is_there(session, tmp_path):
    env = session
    env.slow = 0.3
    doc = env.new_document()
    started = time.perf_counter()
    assert env.actions._save_to_path(doc, _path(tmp_path))
    assert time.perf_counter() - started < 0.1, "starting a save must not wait for the file"
    assert doc.is_dirty and doc.file_path is None and env.saved == []
    assert any("Salvando" in text for text in env.messages)
    assert env.actions.wait_for_saves(10000)
    assert not doc.is_dirty and doc.file_path == _path(tmp_path)
    assert env.saved == [doc.uid]
    assert os.path.exists(_path(tmp_path))
    assert any("salvo com sucesso" in text for text in env.messages)


def test_an_edit_made_while_the_file_is_written_keeps_the_document_dirty(session, tmp_path):
    env = session
    env.slow = 0.2
    doc = env.new_document()
    env.actions._save_to_path(doc, _path(tmp_path))
    doc.mark_dirty("edit during the write")
    assert env.actions.wait_for_saves(10000)
    assert doc.is_dirty and doc.dirty_reason == "edit during the write"
    assert doc.file_path == _path(tmp_path), "the file exists, so the document knows where it is"
    assert env.saved == [doc.uid]


def test_a_failed_write_leaves_the_document_dirty_and_says_so(session, tmp_path):
    env = session
    env.fail = True
    doc = env.new_document()
    assert env.actions._save_to_path(doc, _path(tmp_path))
    assert env.actions.wait_for_saves(10000)
    assert doc.is_dirty and doc.file_path is None and env.saved == []
    assert any("Falha ao salvar" in text and "disk full" in text for text in env.messages)
    assert not os.path.exists(_path(tmp_path))
    # and the document can be saved again once the disk has room
    env.fail = False
    assert env.actions._save_to_path(doc, _path(tmp_path))
    assert env.actions.wait_for_saves(10000)
    assert not doc.is_dirty and os.path.exists(_path(tmp_path))


def test_a_capture_that_cannot_be_taken_reports_at_once_and_starts_no_write(session, tmp_path):
    env = session
    doc = env.new_document()
    assert env.backend.begin_transform()
    try:
        assert not env.actions._save_to_path(doc, _path(tmp_path))
    finally:
        env.backend.cancel_transform()
    assert not env.saver.is_busy() and doc.is_dirty
    assert any("transformação" in text for text in env.messages)


def test_save_and_close_closes_only_after_the_file_is_written(session, tmp_path, monkeypatch):
    env = session
    env.slow = 0.25
    doc = env.new_document()
    doc.file_path = _path(tmp_path)
    _Dialog.choice = _Dialog.SAVE
    env.actions.close_with_confirmation(doc.uid)
    assert env.manager.get_document(doc.uid) is not None, "closed before the file existed"
    assert env.actions.wait_for_saves(10000)
    assert env.manager.get_document(doc.uid) is None
    assert os.path.exists(_path(tmp_path))


def test_save_and_close_keeps_the_document_open_when_the_write_fails(session, tmp_path):
    env = session
    env.fail = True
    doc = env.new_document()
    doc.file_path = _path(tmp_path)
    _Dialog.choice = _Dialog.SAVE
    env.actions.close_with_confirmation(doc.uid)
    assert env.actions.wait_for_saves(10000)
    assert env.manager.get_document(doc.uid) is doc and doc.is_dirty, "a failed save must never close the document"


def test_quitting_waits_for_the_write_and_stays_open_if_it_fails(session, tmp_path):
    env = session
    env.slow = 0.2
    doc = env.new_document("keeps")
    doc.file_path = _path(tmp_path, "keeps.lmn")
    _Dialog.choice = _Dialog.SAVE
    assert env.actions.close_all_for_exit() is True
    assert os.path.exists(_path(tmp_path, "keeps.lmn")) and env.manager.get_document(doc.uid) is None

    env.fail = True
    other = env.new_document("fails")
    other.file_path = _path(tmp_path, "fails.lmn")
    assert env.actions.close_all_for_exit() is False, "the application must not quit over a document that was not saved"
    assert env.manager.get_document(other.uid) is other


def test_a_second_save_before_the_first_file_exists_does_not_ask_for_a_name_again(session, tmp_path, monkeypatch):
    env = session
    env.slow = 0.2
    doc = env.new_document()
    asked = []

    def get_save_name(*_args, **_kwargs):
        asked.append(1)
        return _path(tmp_path), ""

    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", staticmethod(get_save_name))
    assert env.actions.save_active()
    assert env.actions.save_active()
    assert asked == [1]
    assert env.actions.wait_for_saves(10000)
    assert env.written == [doc.revision, doc.revision], "both captures are written, one after the other"


def test_closing_a_document_while_it_is_being_written_is_harmless(session, tmp_path):
    env = session
    env.slow = 0.2
    doc = env.new_document()
    env.actions._save_to_path(doc, _path(tmp_path))
    env.manager.close_document(doc.uid)
    assert env.actions.wait_for_saves(10000)
    assert os.path.exists(_path(tmp_path)), "the file holds the document as it was when saved"
    assert env.saved == [], "a closed document has nothing left to mark"
