"""Geometry must keep earlier native history, selection and MDI isolation."""
import pytest
from PySide6.QtWidgets import QApplication
from ui.core.document.document import Document
from ui.core.document.geometry import change_geometry
from ui.engine_backends.aladyn import AladynBackend

app = QApplication.instance() or QApplication(["--platform", "offscreen"])


@pytest.fixture
def session():
    backend = AladynBackend()
    doc = Document("geometry-history", "Geometry", 8, 8)
    doc.layer_manager.add_layer("Camada 1")
    backend.set_active_document_context(doc.uid, 8, 8)
    yield doc, backend
    backend.close_document_context(doc.uid)


def pixels(backend):
    return bytes(backend.get_layer_pixel_buffer(0))


def assert_size(doc, backend, size):
    assert (doc.width, doc.height) == size
    image = backend.get_qimage()
    assert (image.width(), image.height()) == size


@pytest.mark.parametrize("size,options", [
    ((12, 10), {"anchor": (2, 0)}),
    ((4, 3), {"crop": (2, 1)}),
    ((5, 7), {"resample": 0}),
    ((5, 7), {"resample": 1}),
    ((5, 7), {"resample": 2}),
])
def test_geometry_between_pixel_steps_roundtrips(session, size, options):
    doc, backend = session
    empty = pixels(backend)
    original = bytes([90, 60, 30, 255]) * 64
    backend.paste_rgba_buffer_on_active_layer(0, 0, 8, 8, original)
    uid = doc.layer_manager.get_active_layer().uid
    change_geometry(doc, backend, *size, **options)
    assert_size(doc, backend, size)
    transformed = pixels(backend)
    backend.paste_rgba_buffer_on_active_layer(0, 0, *size, bytes([10, 20, 250, 255]) * (size[0] * size[1]))
    painted = pixels(backend)
    assert doc.history.undo(backend)
    assert pixels(backend) == transformed
    assert doc.history.undo(backend)
    assert_size(doc, backend, (8, 8))
    assert pixels(backend) == original
    assert doc.layer_manager.get_active_layer().uid == uid
    assert doc.history.undo(backend)
    assert pixels(backend) == empty
    for _ in range(3):
        assert doc.history.redo(backend)
    assert_size(doc, backend, size)
    assert pixels(backend) == painted


def test_crop_selection_is_restored_by_undo(session):
    doc, backend = session
    backend.select_rect(2, 1, 4, 3)
    before = backend.get_selection_bounds()
    change_geometry(doc, backend, 4, 3, crop=(2, 1))
    assert not backend.has_selection()
    assert doc.history.undo(backend)
    assert backend.get_selection_bounds() == before
    assert doc.history.redo(backend)
    assert not backend.has_selection()


def test_apply_failure_keeps_original_context_and_history(session, monkeypatch):
    doc, backend = session
    backend.paste_rgba_buffer_on_active_layer(0, 0, 8, 8, bytes([45, 67, 89, 255]) * 64)
    original, step = pixels(backend), backend.get_undo_step_id()
    apply = backend.apply_prepared_geometry
    def fail_after_apply(uid):
        assert apply(uid)
        raise RuntimeError("injected commit failure")
    monkeypatch.setattr(backend, "apply_prepared_geometry", fail_after_apply)
    with pytest.raises(RuntimeError):
        change_geometry(doc, backend, 3, 4)
    assert backend.get_active_document_context() == doc.uid
    assert_size(doc, backend, (8, 8))
    assert pixels(backend) == original
    assert backend.get_undo_step_id() == step
    assert doc.history.undo(backend)


def test_two_geometry_steps_and_mdi(session):
    doc, backend = session
    change_geometry(doc, backend, 12, 12)
    change_geometry(doc, backend, 3, 3, crop=(2, 2))
    backend.set_active_document_context("other-geometry", 5, 5)
    try:
        with pytest.raises(RuntimeError):
            doc.history.undo(backend)
        backend.set_active_document_context(doc.uid, doc.width, doc.height)
        assert doc.history.undo(backend)
        assert_size(doc, backend, (12, 12))
        assert doc.history.undo(backend)
        assert_size(doc, backend, (8, 8))
        backend.set_active_document_context("other-geometry", 5, 5)
        image = backend.get_qimage()
        assert (image.width(), image.height()) == (5, 5)
    finally:
        backend.close_document_context("other-geometry")


def test_geometry_signal_updates_canvas_and_navigator(session):
    from types import SimpleNamespace
    from plugins.system.workspace_core.workspace.workspace_document_sync import WorkspaceDocSyncMixin
    doc, backend = session
    sizes = []
    class Workspace(WorkspaceDocSyncMixin):
        _properties_dock = None
        _navigator_panel = SimpleNamespace(set_canvas_size=lambda w, h: sizes.append((w, h)))
        canvas_widget = SimpleNamespace(update=lambda: None)
        def _sync_navigator_to_canvas(self):
            pass
    workspace = Workspace()
    doc.geometry_changed.connect(workspace._on_document_geometry_changed)
    change_geometry(doc, backend, 10, 9)
    assert (workspace.canvas_widget.canvas_w, workspace.canvas_widget.canvas_h) == (10, 9)
    assert doc.history.undo(backend)
    assert (workspace.canvas_w, workspace.canvas_h) == (8, 8)
    assert sizes == [(10, 9), (8, 8)]
