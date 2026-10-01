"""The recovery copy is written off the interface thread without leaving stale files behind (S1.3).

Every minute the recovery controller saved each dirty document on the interface thread (about 4 s
per large document). Now `RecoveryStore.prepare` takes the document (a few ms), the `DocumentSaver`
writes it, and `finish` records the outcome. What must hold in between:

  * a document with a write already in flight is not captured twice;
  * the revision counts as covered only after the file is written;
  * if the document is saved or closed while its copy is being written, the copy that comes out
    must not stay on disk (the next start would offer a recovery of a document that needs none);
  * a failed write is not recorded, so the next round tries again.
"""

from __future__ import annotations

import pytest

from tests.persistence_doubles import BackendDouble
from ui.core.document.document import Document
from ui.core.document.recovery import RecoveryStore
from ui.core.document.serializer import DocumentSerializer


@pytest.fixture()
def store(qapp, tmp_path):
    store = RecoveryStore(tmp_path)
    try:
        yield store
    finally:
        store.close()


def _document():
    document = Document("doc", "Drawing", 2, 2)
    document.layer_manager.add_layer("Paint")
    document.mark_dirty("stroke")
    return document


def test_a_clean_document_has_nothing_to_capture(store):
    document = _document()
    document.mark_saved()
    assert store.prepare(document, BackendDouble(document)) is None


def test_the_revision_is_covered_only_after_the_file_is_written(store):
    document = _document()
    capture = store.prepare(document, BackendDouble(document))
    assert capture is not None and capture.revision == document.revision
    assert store.revisions == {}, "it is not covered yet: nothing has been written"
    DocumentSerializer.write(capture)
    store.finish(capture, written=True)
    assert store.revisions == {"doc": document.revision}
    assert store.prepare(document, BackendDouble(document)) is None, "this revision already has its copy"
    document.mark_dirty("another stroke")
    assert store.prepare(document, BackendDouble(document)) is not None


def test_a_document_is_not_captured_again_while_its_copy_is_being_written(store):
    document = _document()
    first = store.prepare(document, BackendDouble(document))
    assert first is not None
    document.mark_dirty("edit during the write")
    assert store.prepare(document, BackendDouble(document)) is None
    store.finish(first, written=False)
    assert store.prepare(document, BackendDouble(document)) is not None, "once it is over the next round may capture"


def test_a_failed_write_is_not_recorded_so_the_next_round_tries_again(store):
    document = _document()
    capture = store.prepare(document, BackendDouble(document))
    store.finish(capture, written=False)
    assert store.revisions == {}
    assert store.prepare(document, BackendDouble(document)) is not None


def test_a_copy_written_after_the_document_was_saved_is_removed(store):
    document = _document()
    capture = store.prepare(document, BackendDouble(document))
    store.discard("doc")  # the user saved the document while its copy was being written
    DocumentSerializer.write(capture)
    assert store.path_for("doc").exists(), "the write finished after the discard: the file is there for a moment"
    store.finish(capture, written=True)
    assert not store.path_for("doc").exists(), "the stale copy must be removed once the write is over"
    assert store.revisions == {}


def test_a_discard_with_no_write_in_flight_does_not_cancel_the_next_capture(store):
    document = _document()
    store.discard("doc")
    capture = store.prepare(document, BackendDouble(document))
    DocumentSerializer.write(capture)
    store.finish(capture, written=True)
    assert store.path_for("doc").exists() and store.revisions == {"doc": document.revision}


def test_the_synchronous_capture_still_works_and_cleans_up_after_a_failure(store, monkeypatch):
    document = _document()
    assert store.capture(document, BackendDouble(document)) is True
    document.mark_dirty("more")

    def boom(_capture):
        raise OSError("disk full")

    monkeypatch.setattr(DocumentSerializer, "write", staticmethod(boom))
    with pytest.raises(OSError):
        store.capture(document, BackendDouble(document))
    monkeypatch.undo()
    assert store.prepare(document, BackendDouble(document)) is not None, "a failed write must not leave the document marked as in flight"
