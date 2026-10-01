"""Failure injection and native round-trip regression coverage."""

import json
from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication

from ui.infrastructure.config.manager import ConfigManager
from ui.core.document.document import Document
from ui.core.document.serializer import DocumentSerializer, DocumentFormatError
from ui.core.document.restore import restore_document

app = QApplication.instance() or QApplication(["--platform", "offscreen"])


def test_config_recovers_backup_without_overwriting_it(tmp_path):
    path = tmp_path / "config.json"
    config = ConfigManager(str(path))
    config.set("theme", "active", "previous")
    config.set("theme", "active", "latest")
    path.write_text("broken", encoding="utf-8")
    recovered = ConfigManager(str(path))
    assert recovered.get("theme", "active") == "previous"
    assert json.loads(path.with_suffix(".json.bak").read_text(encoding="utf-8"))["theme"]["active"] == "previous"


def test_failed_config_replace_preserves_previous_file_and_reports_error(tmp_path):
    path = tmp_path / "config.json"
    config = ConfigManager(str(path))
    previous = path.read_bytes()
    errors = []
    config.persistenceFailed.connect(errors.append)
    config.set("theme", "active", "changed", auto_save=False)
    with patch("ui.infrastructure.config.storage.os.replace", side_effect=PermissionError("locked")):
        assert not config.save()
    assert path.read_bytes() == previous
    assert errors == ["locked"]
    assert not list(tmp_path.glob(".*"))


def test_config_does_not_expose_mutable_state(tmp_path):
    config = ConfigManager(str(tmp_path / "config.json"))
    tools = config.get("floating_toolbar", "tools")
    tools.clear()
    assert config.get("floating_toolbar", "tools")


def test_cannot_save_without_native_pixels(tmp_path):
    document = Document("test", "Drawing", 1, 1)
    document.layer_manager.add_layer("Paint")
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.save(document, None, tmp_path / "test.lmn")
    assert not (tmp_path / "test.lmn").exists()


def test_group_first_and_locked_transparent_pixels_round_trip(tmp_path):
    from ui.infrastructure.bridge_client.aladyn import AladynBackend
    backend = AladynBackend()
    assert backend.available
    backend.set_active_document_context("source", 2, 2)
    document = Document("source", "Groups", 2, 2)
    records = [
        {"uid": 10, "name": "Group", "is_group": True, "blend_mode": "Atravessar"},
        {"uid": 20, "name": "Paint", "parent_uid": 10, "locked": True,
         "alpha_locked": True, "opacity": 0.4, "blend_mode": "Multiply",
         "pixel_payload": "layers/20.rgba"},
    ]
    pixels = bytes([30, 60, 90, 128]) * 4
    manifest = {"layers": records, "active_uid": 20}
    restore_document(document, backend, manifest, {"layers/20.rgba": pixels})
    path = DocumentSerializer.save(document, backend, tmp_path / "groups.lmn")
    saved, payloads = DocumentSerializer.read(path)
    backend.set_active_document_context("restored", 2, 2)
    other = Document("restored", "Groups", 2, 2)
    restore_document(other, backend, saved, payloads)
    assert backend.is_group(0)
    assert bytes(backend.get_layer_pixel_buffer(1)) == pixels
    assert other.layer_manager.layers[1].parent_uid == 10
    assert other.layer_manager.get_active_layer().uid == 20
    assert backend.get_active_layer_index() == 1


@pytest.mark.parametrize("records", [
    [{"uid": 1, "is_group": True, "parent_uid": 1}],
    [{"uid": 1, "parent_uid": 2}, {"uid": 2}],
    [{"uid": 1, "opacity": float("nan")}],
    [{"uid": 1, "visible": "false"}],
])
def test_rejects_invalid_layer_metadata(records):
    with pytest.raises(DocumentFormatError):
        DocumentSerializer._validate_manifest({"layers": records})


def test_recovery_keeps_dirty_state_and_skips_active_sessions(tmp_path):
    from ui.core.document.recovery import RecoveryStore
    from tests.persistence_doubles import BackendDouble
    document: Document = Document("doc", "Drawing", 2, 2)
    document.layer_manager.add_layer("Paint")
    document.file_path = "original.lmn"
    store = RecoveryStore(tmp_path)
    other = RecoveryStore(tmp_path)
    try:
        assert store.capture(document, BackendDouble(document))
        assert document.is_dirty
        assert document.file_path == "original.lmn"
        assert not store.capture(document, BackendDouble(document))
        assert other.candidates() == []
        store.close()
        assert other.candidates() == [store.path_for("doc")]
        manifest, payloads = DocumentSerializer.read(other.candidates()[0])
        assert manifest["name"] == "Drawing"
        assert payloads
        store.discard("doc")
        assert other.candidates() == []
    finally:
        store.close()
        other.close()


def test_document_backup_retains_previous_generation(tmp_path):
    from tests.persistence_doubles import BackendDouble
    document = Document("doc", "Previous", 2, 2)
    document.layer_manager.add_layer("Paint")
    path = DocumentSerializer.save(document, BackendDouble(document), tmp_path / "drawing.lmn")
    document.name = "Current"
    DocumentSerializer.save(document, BackendDouble(document), path)
    assert DocumentSerializer.read(path)[0]["name"] == "Current"
    assert DocumentSerializer.read(path + ".bak")[0]["name"] == "Previous"


def test_geometry_change_preserves_pixels_and_applies_crop(tmp_path):
    from ui.core.document.geometry import change_geometry
    from ui.infrastructure.bridge_client.aladyn import AladynBackend
    backend = AladynBackend()
    document = Document("geometry", "Geometry", 2, 2)
    document.layer_manager.add_layer("Camada 1")
    backend.set_active_document_context(document.uid, 2, 2)
    pixels = bytes([0, 0, 0, 0]) * 4
    pixels = bytearray(pixels)
    pixels[(1 * 2 + 1) * 4:(1 * 2 + 1) * 4 + 4] = bytes([240, 10, 20, 255])
    backend.paste_rgba_buffer_on_active_layer(0, 0, 2, 2, bytes(pixels))
    change_geometry(document, backend, 4, 4, anchor=(1, 1))
    assert (document.width, document.height) == (4, 4)
    grown = bytes(backend.get_layer_pixel_buffer(0))
    assert grown[(2 * 4 + 2) * 4:(2 * 4 + 2) * 4 + 4] == bytes([240, 10, 20, 255])
    change_geometry(document, backend, 2, 2, crop=(2, 2))
    assert (document.width, document.height) == (2, 2)
    assert bytes(backend.get_layer_pixel_buffer(0))[:4] == bytes([240, 10, 20, 255])
