"""Native LMN v2 persistence, migrations and recovery failure regressions."""

import copy
import json
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from ui.core.document.document import Document
from ui.core.document.schema import migrate
from ui.core.document.serializer import DocumentSerializer, DocumentFormatError
from ui.core.document.restore import restore_document
from ui.engine_backends.aladyn import AladynBackend

app = QApplication.instance() or QApplication(["--platform", "offscreen"])


@pytest.fixture
def drawing():
    backend = AladynBackend()
    document = Document("v2-source", "Persistência", 4, 4)
    document.layer_manager.add_layer("Pintura")
    backend.set_active_document_context(document.uid, 4, 4)
    yield document, backend
    for uid in (document.uid, "v2-copy", "other"):
        backend.close_document_context(uid)


def test_native_round_trip_preserves_mask_profile_texture_curve_and_guides(drawing, tmp_path):
    document: Document
    document, backend = drawing
    pixels = bytes([77, 100, 33, 128]) * 16
    backend.paste_rgba_buffer_on_active_layer(0, 0, 4, 4, pixels)
    mask = bytes([0, 1, 127, 255]) * 4
    assert backend.set_selection_mask_buffer(mask)
    backend.set_color_profile(2)
    canvas = backend.get_canvas_resource()
    canvas.update(width=2, height=2, pixels=bytes([0, 75, 170, 255]),
                  enabled=True, scale=2.5, contrast=0.7, invert=True,
                  curve=[(i / 255) ** 2 for i in range(256)])
    assert backend.set_canvas_resource(canvas)
    document.paper_color = QColor(30, 40, 50, 90)
    document.paper_visible = False
    document.guide_state = {"type": "straight", "p0": QPointF(1.5, 2.5), "p1": QPointF(8, 9)}
    document.sym_state = {"mode": "radial", "segments": 9, "cx": 2.0, "cy": 3.0}
    document.zoom, document.rotation = 1.75, 20.0
    path = DocumentSerializer.save(document, backend, tmp_path / "drawing.lmn")
    manifest, payloads = DocumentSerializer.read(path)
    assert manifest["version"] == 2
    assert manifest["guide_state"]["p0"] == [1.5, 2.5]
    other: Document = Document("v2-copy", "Cópia", 4, 4)
    backend.set_active_document_context(other.uid, 4, 4)
    # An existing selection must not clip the incoming layer pixels.
    backend.select_rect(0, 0, 1, 1)
    restore_document(other, backend, manifest, payloads)
    assert backend.get_layer_pixel_buffer(0) == pixels
    assert backend.get_selection_mask_buffer() == mask
    assert backend.get_color_profile() == 2
    assert backend.get_canvas_resource() == canvas
    assert other.guide_state == document.guide_state
    assert other.sym_state == document.sym_state
    assert other.paper_color == document.paper_color
    assert not other.paper_visible
    assert (other.paper_scale, other.paper_contrast, other.paper_invert) == (2.5, 0.7, True)
    assert (other.zoom, other.rotation) == (1.75, 20.0)
    backend.set_active_document_context(document.uid, 4, 4)
    assert backend.get_selection_mask_buffer() == mask


@pytest.mark.parametrize("version", [True, "1", 1.5, -1, 3])
def test_rejects_invalid_or_future_version(version):
    with pytest.raises(DocumentFormatError):
        migrate({"version": version})


@pytest.mark.parametrize("version", [0, 1])
def test_migration_chain_does_not_modify_source(version):
    source = {"version": version, "layers": [{"uid": 1}]}
    before = copy.deepcopy(source)
    result = migrate(source)
    assert source == before
    assert result["version"] == 2
    assert result["layers"][0]["empty"] is True
    assert result["selection_payload"] is None
    assert result["color_profile_id"] == 0


def rewrite(path, changes, replace_payload=None):
    with zipfile.ZipFile(path) as archive:
        entries = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(entries["manifest.json"])
    manifest.update(changes)
    entries["manifest.json"] = json.dumps(manifest).encode()
    if replace_payload:
        entries.update(replace_payload)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


@pytest.mark.parametrize("changes", [
    {"width": True}, {"width": 100000, "height": 100000}, {"zoom": 0},
    {"color_profile_id": 999}, {"selection_payload": "../selection.gray"},
    {"guide_state": {"p0": [0]}}, {"guide_state": {"p0": [0, float("nan")]}},
    {"sym_state": {"segments": 1.5}}, {"sym_state": {"hidden": "false"}},
    {"paper": {"visible": "false"}},
])
def test_rejects_malformed_v2_before_restore(drawing, tmp_path, changes):
    document, backend = drawing
    path = DocumentSerializer.save(document, backend, tmp_path / "invalid.lmn")
    rewrite(path, changes)
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


def test_bad_resource_does_not_replace_previous_file(drawing, tmp_path):
    document, backend = drawing
    path = DocumentSerializer.save(document, backend, tmp_path / "drawing.lmn")
    previous = Path(path).read_bytes()
    canvas = backend.get_canvas_resource()
    canvas["pixels"] = b"short"
    with patch.object(backend, "get_canvas_resource", return_value=canvas):
        with pytest.raises(DocumentFormatError):
            DocumentSerializer.save(document, backend, path)
    assert Path(path).read_bytes() == previous
    assert not list(tmp_path.glob(".*.tmp"))


def test_wrong_context_cannot_save_another_documents_pixels(drawing, tmp_path):
    document, backend = drawing
    backend.set_active_document_context("other", 4, 4)
    with pytest.raises(DocumentFormatError, match="contexto"):
        DocumentSerializer.save(document, backend, tmp_path / "wrong.lmn")
    assert not (tmp_path / "wrong.lmn").exists()


def test_truncated_mask_rejected_and_native_mask_unchanged(drawing, tmp_path):
    document, backend = drawing
    backend.select_all()
    original = backend.get_selection_mask_buffer()
    with pytest.raises(ValueError):
        backend.set_selection_mask_buffer(b"short")
    assert backend.get_selection_mask_buffer() == original
    path = DocumentSerializer.save(document, backend, tmp_path / "mask.lmn")
    rewrite(path, {}, {"masks/selection.gray": b"short"})
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(path)


@pytest.mark.parametrize("missing", [False, True])
def test_recovery_falls_back_to_valid_previous_generation(drawing, tmp_path, missing):
    from pathlib import Path
    from ui.core.document.recovery import RecoveryStore
    document, backend = drawing
    store, reader = RecoveryStore(tmp_path), RecoveryStore(tmp_path)
    try:
        document.mark_dirty()
        assert store.capture(document, backend)
        document.name = "New generation"
        document.mark_dirty()
        assert store.capture(document, backend)
        assert reader.candidates() == []
        store.close()
        path = store.path_for(document.uid)
        if missing:
            path.unlink()
        else:
            path.write_bytes(b"corrupted")
        assert reader.candidates() == [Path(str(path) + ".bak")]
        assert DocumentSerializer.read(reader.candidates()[0])[0]["name"] == "Persistência"
        reader.discard_candidate(reader.candidates()[0])
        assert reader.candidates() == []
        assert not path.exists()
        assert not Path(str(path) + ".bak").exists()
    finally:
        store.close()
        reader.close()


def test_paper_ui_updates_model_without_replacing_embedded_texture(drawing, monkeypatch):
    """Mostrar o papel não suja nada; editar muda o modelo e o motor, e só
    escolher outro preset troca a textura embutida."""
    from ui.core.document.manager import DocumentManager
    from ui.core.engine.registry import EngineRegistry
    from plugins.ui.layers_plugin.paper import PaperLayerWidget
    document, backend = drawing
    monkeypatch.setattr(DocumentManager.instance(), "active_document", lambda: document)
    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: backend)
    widget = PaperLayerWidget()
    canvas = backend.get_canvas_resource()
    try:
        document.mark_saved()
        widget.show_document(document)
        assert not document.is_dirty
        assert backend.get_canvas_resource() == canvas
        document.set_paper(color=QColor(20, 30, 40, 50), visible=False, texture_enabled=True,
                           scale=2.3, contrast=0.8, invert=True)
        assert document.is_dirty
        assert (document.paper_visible, document.paper_texture_enabled) == (False, True)
        assert (document.paper_scale, document.paper_contrast, document.paper_invert) == (2.3, 0.8, True)
        assert document.paper_color == QColor(20, 30, 40, 50)
        assert backend.get_canvas_resource()["pixels"] == canvas["pixels"]
    finally:
        widget.close()


def test_guide_switch_resets_old_modes_and_restores_points(drawing, monkeypatch):
    from types import SimpleNamespace
    from ui.core.document.manager import DocumentManager
    from ui.core.engine.registry import EngineRegistry
    from plugins.system.workspace_core.workspace.canvas.tools.geometry_tool_controller import GeometryToolController
    document, backend = drawing
    monkeypatch.setattr(DocumentManager.instance(), "active_document", lambda: document)
    monkeypatch.setattr(EngineRegistry.instance(), "get_backend", lambda: backend)
    controller = GeometryToolController(SimpleNamespace())
    # `guide_state`/`sym_state` do controller sao SyncedDict (Fase pos-C5,
    # item P1 #2): qualquer escrita -- inclusive uma unica chave -- propaga
    # imediatamente para o documento ativo. Por isso o "estado anterior" e
    # simulado diretamente no documento (que usa dicts simples), e nao no
    # controller, para isolar este teste do proprio efeito de auto-sync que
    # ele testa mais abaixo.
    document.guide_state["type"] = "three_point"
    document.sym_state["mode"] = "radial"
    document.mark_saved()
    controller.load_document_state(document)
    assert not document.is_dirty
    assert controller.guide_state["type"] == "three_point"
    assert controller.sym_state["mode"] == "radial"
    controller.guide_state.update(type="straight", p0=QPointF(1, 2), p1=QPointF(3, 4))
    assert document.is_dirty
    assert document.guide_state["p0"] == QPointF(1, 2)
    # Escrita de chave unica -- sem chamada explicita a sync_guides_to_engine
    # -- agora tambem propaga sozinha (o proprio comportamento que o
    # SyncedDict foi criado para garantir).
    controller.guide_state["p0"] = QPointF(9, 9)
    assert document.guide_state["p0"] == QPointF(9, 9)
    controller.load_document_state(document)
    assert controller.guide_state["p0"] == QPointF(9, 9)


def test_selection_and_profile_changes_invalidate_recovery_revision(drawing, monkeypatch):
    from ui.core.document.manager import DocumentManager
    document, backend = drawing
    monkeypatch.setattr(DocumentManager.instance(), "get_document", lambda uid: document if uid == document.uid else None)
    document.mark_saved()
    backend.select_all()
    assert document.is_dirty and document.dirty_reason == "selection"
    revision = document.revision
    backend.clear_selection()
    assert document.revision > revision
    document.mark_saved()
    backend.set_color_profile(1)
    assert document.is_dirty and document.dirty_reason == "color_profile"


def test_recovery_after_process_exit_without_cleanup(tmp_path):
    import subprocess
    import sys
    from ui.core.document.recovery import RecoveryStore
    script = """
import os, sys
from PySide6.QtWidgets import QApplication
from ui.core.document.document import Document
from ui.core.document.recovery import RecoveryStore
app = QApplication([])
class Backend:
    available = True
    def get_layer_pixel_buffer(self, index): return bytes([1, 2, 3, 255])
doc = Document('crashed', 'Recovered after crash', 1, 1)
doc.layer_manager.add_layer('Paint')
store = RecoveryStore(sys.argv[1])
assert store.capture(doc, Backend())
os._exit(0)
"""
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    reader = RecoveryStore(tmp_path)
    try:
        candidates = reader.candidates()
        assert len(candidates) == 1
        manifest, payloads = DocumentSerializer.read(candidates[0])
        assert manifest["name"] == "Recovered after crash"
        assert list(payloads.values()) == [bytes([1, 2, 3, 255])]
    finally:
        reader.close()


def test_save_during_transform_preserves_existing_file(drawing, tmp_path):
    document, backend = drawing
    pixels = bytes([12, 34, 56, 255]) * 16
    backend.paste_rgba_buffer_on_active_layer(0, 0, 4, 4, pixels)
    path = Path(DocumentSerializer.save(document, backend, tmp_path / "safe.lmn"))
    previous = path.read_bytes()
    assert backend.begin_transform()
    try:
        with pytest.raises(DocumentFormatError, match="transformação"):
            DocumentSerializer.save(document, backend, path)
        assert path.read_bytes() == previous
    finally:
        backend.cancel_transform()
    assert backend.get_layer_pixel_buffer(0) == pixels
