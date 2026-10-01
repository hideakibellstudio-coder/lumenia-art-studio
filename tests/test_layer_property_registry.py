"""A layer property is one entry in a table; each consumer walks the table (S2.2).

Until 2026-10-01 every layer property (visible, locked, opacity, blend mode, alpha lock, clipping
mask) was written by hand in eight places: the default of a new layer, the history snapshot, the
copy when a layer is duplicated, the read of a saved record, the record written to the file, the
validation of the file, the push to the engine on each change, and the re-read of the engine when a
history transaction commits. The alpha lock showed up in 34 files, and forgetting one of the eight
lost data without a sound (saved without the property, duplicated without copying it).

This test adds a property only to `layer_properties.TABLE` and checks that each of those places
treats it, without any other file knowing its name. If a consumer goes back to listing properties by
hand, the new one is missing in it and the test names it.
"""

from __future__ import annotations

import pytest

from ui.core.document import layer_properties
from ui.core.document.layer_manager import LocalLayerManager
from ui.core.document.layer_properties import LAYER_PROPERTIES, LayerProperty, LayerPropertyTable
from ui.core.document.save_capture import _layer_entries
from ui.core.document.schema import DocumentFormatError
from ui.core.document.serializer import DocumentSerializer

from tests.persistence_doubles import SnapshotDouble

PINNED = LayerProperty("pinned", False, bool, engine_setter="set_layer_pinned", reason="pin", is_flag=True)


class Recorder:
    """Um motor que aceita qualquer chamada e a anota."""

    available = True

    def __init__(self, layer_count: int) -> None:
        self.calls: list[tuple] = []
        self._count = layer_count

    def get_drawing_layer_count(self) -> int:
        return self._count

    def __getattr__(self, name):
        def record(*args):
            self.calls.append((name, *args))
            return True
        return record


@pytest.fixture()
def table(monkeypatch):
    monkeypatch.setattr(layer_properties, "TABLE", LayerPropertyTable(LAYER_PROPERTIES + (PINNED,)))


@pytest.fixture()
def manager(table):
    backend = Recorder(layer_count=2)
    manager = LocalLayerManager(backend)
    manager.replace_layers([{"uid": 1, "name": "paper"}, {"uid": 2, "name": "ink"}])
    manager.set_active_layer(2)
    manager.engine = backend
    return manager


def test_a_new_layer_and_a_new_group_start_with_the_default(table):
    manager = LocalLayerManager(Recorder(layer_count=0))
    manager.replace_layers([{"uid": 1, "name": "layer"}, {"uid": 2, "name": "group", "is_group": True}])
    assert [layer.pinned for layer in manager.layers] == [False, False]


def test_a_record_with_the_property_gives_a_layer_with_it(table):
    manager = LocalLayerManager(Recorder(layer_count=0))
    manager.replace_layers([{"uid": 1, "name": "layer", "pinned": True}])
    assert manager.layers[0].pinned is True


def test_changing_it_reaches_the_engine_and_the_listeners(manager):
    reasons, changed = [], []
    manager.content_changed.connect(reasons.append)
    manager.layer_property_changed.connect(changed.append)

    assert manager.set_property(1, "pinned", True)

    assert manager.layers[1].pinned is True
    assert ("set_layer_pinned", 1, True) in manager.engine.calls
    assert reasons == ["pin"] and changed == [2]


def test_a_duplicate_inherits_it(manager):
    manager.set_property(1, "pinned", True)
    copy_uid = manager.duplicate_layer(2)
    assert manager.get_layer_by_uid(copy_uid).pinned is True


def test_the_history_snapshot_carries_it_and_restores_it(manager):
    manager.set_property(1, "pinned", True)
    snapshot = manager._snapshot()
    manager.set_property(1, "pinned", False)

    manager._restore_snapshot(snapshot)

    assert manager.layers[1].pinned is True


class _Document:
    def __init__(self, manager) -> None:
        self.layer_manager = manager


def test_the_saved_record_carries_it(manager):
    manager.set_property(1, "pinned", True)
    entries, _raster = _layer_entries(_Document(manager), None, SnapshotDouble([True, True], 8, 8))
    assert [entry["pinned"] for entry in entries] == [False, True]


def test_the_file_refuses_it_when_it_is_not_a_real_boolean(table):
    manifest = {"layers": [{"uid": 1, "pinned": "yes", "tiles_payload": "layers/1.tiles"}], "active_uid": 1}
    with pytest.raises(DocumentFormatError, match="flag inválido: pinned"):
        DocumentSerializer._validate_manifest(manifest)


def test_opening_a_file_pushes_it_to_the_engine(table):
    from ui.core.document.restore import _restore_into_engine

    class Engine(Recorder):
        def get_drawing_layer_count(self) -> int:
            return len([call for call in self.calls if call[0] == "add_layer"]) or 1

        def add_layer(self, name, index):
            self.calls.append(("add_layer", name, index))
            return len([call for call in self.calls if call[0] == "add_layer"]) - 1

        def remove_layer(self, index):
            self.calls.append(("remove_layer", index))
            return True

    engine = Engine(layer_count=1)
    manager = LocalLayerManager(engine)

    class Document:
        layer_manager = manager
        history = Recorder(layer_count=0)
        width = height = 8
        dpi = 96
        paper_texture_id = 0
        paper_texture_enabled = False
        paper_visible = True

        class paper_color:
            @staticmethod
            def getRgb():
                return (255, 255, 255, 255)

    manifest = {"layers": [{"uid": 1, "name": "layer", "pinned": True, "empty": True}], "active_uid": 1}
    try:
        _restore_into_engine(Document, engine, manifest, {}, {})
    except Exception:  # noqa: BLE001 -- só interessa o que foi ao motor antes do fim da restauração
        pass

    assert ("set_layer_pinned", 0, True) in engine.calls


class HistoryEngine(Recorder):
    """O que `DocumentHistory.transaction` pergunta ao motor numa pilha de camadas comuns."""

    def __init__(self, uids: list[int]) -> None:
        super().__init__(layer_count=len(uids))
        self._uids = uids

    def get_active_document_context(self):
        return "doc"

    def get_layer_info(self, index):
        return {"document_uid": self._uids[index], "is_group": False, "is_filter": False, "parent_index": -1}

    def is_group(self, index):
        return False

    def is_filter_layer(self, index):
        return False

    def get_history_step_ids(self):
        return []


def test_a_history_transaction_rewrites_it_into_every_layer_of_the_engine(manager):
    from types import SimpleNamespace

    from ui.core.document.history import DocumentHistory

    engine = HistoryEngine([1, 2])
    document = SimpleNamespace(uid="doc", layer_manager=manager, width=8, height=8, mark_dirty=lambda reason: None)
    history = DocumentHistory(document)
    manager.engine = engine

    with history.transaction(engine):
        manager.set_property(1, "pinned", True)

    # A camada 0 não mudou: só o laço de confirmação do histórico a reenvia ao motor.
    assert ("set_layer_pinned", 0, False) in engine.calls
    assert ("set_layer_pinned", 1, True) in engine.calls
