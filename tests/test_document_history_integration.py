"""Exercise native pixels and document UIDs in the same history timeline."""
import pytest
from PySide6.QtWidgets import QApplication
from ui.core.document.document import Document
from ui.core.document.history import LayerTransactionCancelled
from ui.engine_backends.aladyn import AladynBackend

app = QApplication.instance() or QApplication(["--platform", "offscreen"])


@pytest.fixture
def session():
    backend = AladynBackend()
    document = Document("history-integration", "History", 8, 8)
    document.layer_manager.add_layer("Camada 1")
    backend.set_active_document_context(document.uid, 8, 8)
    yield document, backend
    backend.close_document_context(document.uid)


def pixels(backend):
    return [bytes(backend.get_layer_pixel_buffer(i) or b"") for i in range(backend.get_drawing_layer_count())]


def paint(backend, color):
    assert backend.paste_rgba_buffer_on_active_layer(0, 0, 8, 8, bytes(color) * 64)


def duplicate(document, backend):
    manager = document.layer_manager
    with document.history.transaction(backend):
        index = manager.active_index
        uid = manager.get_active_layer().uid
        assert backend.duplicate_layer(index) >= 0
        manager.duplicate_layer(uid)


def test_pixels_structure_and_redo_share_one_order(session):
    document, backend = session
    manager = document.layer_manager
    empty = pixels(backend)
    paint(backend, [255, 0, 0, 255])
    red = pixels(backend)
    duplicate(document, backend)
    ids = [layer.uid for layer in manager.layers]
    paint(backend, [0, 0, 255, 255])
    blue = pixels(backend)
    assert document.history.undo(backend)
    assert pixels(backend) == red * 2
    assert document.history.undo(backend)
    assert pixels(backend) == red
    assert [layer.uid for layer in manager.layers] == ids[:1]
    assert document.history.undo(backend)
    assert pixels(backend) == empty
    for _ in range(3):
        assert document.history.redo(backend)
    assert pixels(backend) == blue
    assert [layer.uid for layer in manager.layers] == ids
    assert document.is_dirty


def test_failed_transaction_preserves_pixels_and_history(session):
    document, backend = session
    paint(backend, [10, 30, 90, 255])
    before, step = pixels(backend), backend.get_undo_step_id()
    with pytest.raises(RuntimeError):
        with document.history.transaction(backend):
            backend.add_layer("only native", -1)
            # A partial backend mutation must never commit without its model.
    assert pixels(backend) == before
    assert backend.get_undo_step_id() == step
    assert len(document.layer_manager.layers) == 1
    assert document.history.undo(backend)


def test_nested_group_removal_restores_hierarchy_and_pixels(session):
    document, backend = session
    manager = document.layer_manager
    with document.history.transaction(backend):
        backend.add_group("group", -1)
        group = manager.add_group("group")
        backend.add_group("nested", -1)
        manager.add_group("nested")
        backend.add_layer("child", -1)
        manager.add_layer("child")
    paint(backend, [22, 33, 44, 255])
    before, metadata = pixels(backend), manager._snapshot()
    with document.history.transaction(backend):
        assert backend.remove_layer(1)
        assert manager.remove_layer(group)
    assert len(manager.layers) == backend.get_drawing_layer_count() == 1
    assert document.history.undo(backend)
    assert pixels(backend) == before
    assert manager._snapshot() == metadata
    assert document.history.redo(backend)
    assert backend.get_drawing_layer_count() == 1


def test_merge_rename_order_branch_and_filter(session):
    document, backend = session
    manager = document.layer_manager
    paint(backend, [255, 0, 0, 255])
    duplicate(document, backend)
    with document.history.transaction(backend):
        backend.set_layer_name(1, "changed")
        manager.set_layer_name(1, "changed")
        backend.set_layer_opacity(1, 0.5)
        manager.set_layer_opacity(1, 0.5)
    before = pixels(backend)
    with document.history.transaction(backend):
        assert backend.merge_layer_down(1)
        assert manager.merge_down(manager.layers[1].uid)
    assert document.history.undo(backend)
    assert pixels(backend) == before
    assert backend.get_layer_name(1) == manager.layers[1].name == "changed"
    with document.history.transaction(backend):
        backend.reorder_layers([1, 0])
        manager.move_layer_down(manager.layers[1].uid)
    assert not document.history.redo(backend)  # Editing after undo discards redo.
    with document.history.transaction(backend):
        index = backend.add_filter_layer("filter", 1, manager.active_index + 1)
        manager.add_layer("filter")
        manager.get_active_layer().is_filter = True
        backend.set_filter_params(index, [0.2, 0.3, 1.0, 0.0])
    params = backend.get_filter_params(index)
    duplicate(document, backend)
    assert backend.is_filter_layer(index + 1)
    assert backend.get_filter_params(index + 1) == params
    assert document.history.undo(backend)
    assert document.history.redo(backend)
    assert backend.get_filter_params(index + 1) == params


def test_reject_wrong_document_context(session):
    document, backend = session
    backend.set_active_document_context("other", 8, 8)
    try:
        with pytest.raises(RuntimeError):
            document.history.undo(backend)
    finally:
        backend.close_document_context("other")


def test_menu_actions_use_the_transaction(session, monkeypatch):
    from ui.boundary.orchestrator.main_window_menu_actions import MainWindowMenuActionsMixin
    from ui.core.engine.registry import EngineRegistry
    from types import SimpleNamespace
    document, backend = session
    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: backend)
    class Host(MainWindowMenuActionsMixin):
        dm = SimpleNamespace(active_document=lambda: document)
        status_bar = SimpleNamespace(showMessage=lambda *args: None)
        workspace = None
    paint(backend, [120, 80, 40, 255])
    before = pixels(backend)
    Host().duplicate_active_layer()
    assert len(document.layer_manager.layers) == 2
    assert document.history.undo(backend)
    assert pixels(backend) == before
    assert len(document.layer_manager.layers) == 1


def test_panel_restoration_does_not_reorder_native_twice(session, monkeypatch):
    from ui.core.document.manager import DocumentManager
    from ui.core.engine.registry import EngineRegistry
    from plugins.ui.layers_plugin.panel import LayersPanel
    document, backend = session
    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: backend)
    monkeypatch.setattr(DocumentManager.instance(), "active_document", lambda: document)
    panel = LayersPanel()
    panel.set_layer_manager(document.layer_manager)
    try:
        paint(backend, [90, 50, 20, 255])
        before = pixels(backend)
        panel.duplicate_layer()
        assert len(document.layer_manager.layers) == 2
        panel.move_down()
        order = [layer.uid for layer in document.layer_manager.layers]
        assert document.history.undo(backend)
        assert [layer.uid for layer in document.layer_manager.layers] == list(reversed(order))
        assert document.history.undo(backend)
        assert len(document.layer_manager.layers) == backend.get_drawing_layer_count() == 1
        assert pixels(backend) == before
        assert document.history.redo(backend)
        assert document.history.redo(backend)
        assert [layer.uid for layer in document.layer_manager.layers] == order
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()


def test_native_history_limit_prunes_model_metadata(session):
    document, backend = session
    backend.set_undo_max_steps(2)
    for index in range(5):
        with document.history.transaction(backend):
            backend.set_layer_name(0, str(index))
            document.layer_manager.set_layer_name(0, str(index))
    assert backend.get_undo_count() == 2
    assert len(document.history.entries) == 2
    assert document.history.undo(backend)
    assert document.history.undo(backend)
    assert not document.history.undo(backend)
    assert backend.get_layer_name(0) == document.layer_manager.layers[0].name == "2"


def test_explicit_interactive_cancel_restores_native_and_model_without_step(session):
    document, backend = session
    manager = document.layer_manager
    before_pixels = pixels(backend)
    before_model = manager._snapshot()
    before_ids = list(backend.get_history_step_ids())

    with document.history.transaction(backend):
        backend.set_layer_visibility(0, False)
        manager.set_layer_visibility(0, False)
        raise LayerTransactionCancelled()

    assert pixels(backend) == before_pixels
    assert manager._snapshot() == before_model
    assert list(backend.get_history_step_ids()) == before_ids
    assert backend.get_layer_info(0)["visible"] is True


def test_invalid_permutation_is_atomic(session):
    document, backend = session
    paint(backend, [200, 40, 20, 255])
    duplicate(document, backend)
    before = pixels(backend)
    assert not backend.reorder_layers([0, 0])
    assert pixels(backend) == before
    assert document.history.undo(backend)
    assert backend.get_drawing_layer_count() == 1


def test_direct_model_mutation_is_detected_before_next_transaction(session):
    document, backend = session
    document.layer_manager.add_layer("local only")
    with pytest.raises(RuntimeError, match="projeção"):
        with document.history.transaction(backend):
            pass
    with pytest.raises(RuntimeError, match="projeção"):
        document.history.assert_projection(backend)


def test_direct_model_reorder_cannot_swap_native_pixel_identity(session):
    document, backend = session
    manager = document.layer_manager
    with document.history.transaction(backend):
        backend.add_layer("blue", -1)
        manager.add_layer("blue")
    backend.select_layer(0)
    paint(backend, [255, 0, 0, 255])
    backend.select_layer(1)
    paint(backend, [0, 0, 255, 255])
    assert manager.move_layer_up(manager.layers[0].uid)
    with pytest.raises(RuntimeError, match="projeção"):
        document.history.assert_projection(backend)


def test_uid_api_rejects_index_bool_and_invalid_parent_graph(session):
    document, backend = session
    manager = document.layer_manager
    uid = manager.get_active_layer().uid
    assert manager.get_layer_by_uid(True) is None
    assert not manager.remove_layer(True)
    manager.layers[0].parent_uid = uid
    with pytest.raises(ValueError, match="hierarquia"):
        manager.validate_integrity()
    manager.layers[0].parent_uid = None


def test_flatten_group_reports_progress_and_one_step_history(session):
    document, backend = session
    manager = document.layer_manager
    with document.history.transaction(backend):
        backend.add_group("group", -1)
        manager.add_group("group")
        backend.add_layer("child", -1)
        manager.add_layer("child")
    group_index = next(i for i, layer in enumerate(manager.layers) if layer.is_group)
    before_count = len(manager.layers)
    with document.history.transaction(backend):
        assert backend.flatten_group(group_index)
        assert manager.flatten_group(group_index)
    assert len(manager.layers) < before_count
    assert document.history.undo(backend)
    assert len(manager.layers) == before_count


def test_flatten_nested_group_is_one_reversible_step(session):
    document, backend = session
    manager = document.layer_manager
    with document.history.transaction(backend):
        backend.add_group("group", -1)
        manager.add_group("group")
        backend.add_group("nested", -1)
        manager.add_group("nested")
        backend.add_layer("child", -1)
        manager.add_layer("child")
    paint(backend, [99, 80, 60, 255])
    before, ids = pixels(backend), [layer.uid for layer in manager.layers]
    with document.history.transaction(backend):
        assert backend.flatten_group(1)
        manager.flatten_group(1)
    flattened = pixels(backend)
    assert backend.get_drawing_layer_count() == len(manager.layers) == 2
    assert document.history.undo(backend)
    assert pixels(backend) == before
    assert [layer.uid for layer in manager.layers] == ids
    assert document.history.redo(backend)
    assert pixels(backend) == flattened


def test_model_restore_failure_rolls_native_history_back(session, monkeypatch):
    document, backend = session
    paint(backend, [66, 77, 88, 255])
    duplicate(document, backend)
    before, step = pixels(backend), backend.get_undo_step_id()
    restore = document.history._restore
    failed = False
    def fail_once(snapshot):
        nonlocal failed
        if not failed:
            failed = True
            raise MemoryError("injected model allocation failure")
        restore(snapshot)
    monkeypatch.setattr(document.history, "_restore", fail_once)
    with pytest.raises(MemoryError):
        document.history.undo(backend)
    assert pixels(backend) == before
    assert backend.get_undo_step_id() == step
    assert len(document.layer_manager.layers) == 2
