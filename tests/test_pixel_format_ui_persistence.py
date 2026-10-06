"""UI, document persistence, and export of 16-bit (RGBA16) documents (S7).

Verifies the integration of pixel format across Document model, schema validation,
manifest persistence (.lmn), backend MDI context management, capabilities, QImage (Format_RGBA64),
and image export.
"""

from __future__ import annotations

import os

import pytest
from PySide6.QtGui import QImage

native = pytest.importorskip("aladyn_engine_native", reason="native module not built in this environment")

from ui.core.document.document import Document
from ui.core.document.manager import DocumentManager
from ui.core.document.schema import DocumentFormatError, validate_auxiliary
from ui.core.document.save_capture import capture_document
from ui.core.document.restore import restore_document
from ui.infrastructure.bridge_client.aladyn import AladynBackend


def test_document_model_pixel_format_default_and_explicit():
    doc8 = Document("doc_8", "Untitled 8", 100, 100)
    assert doc8.pixel_format == 0
    assert not doc8.rgba16_document

    doc16 = Document("doc_16", "Untitled 16", 100, 100, pixel_format=1)
    assert doc16.pixel_format == 1
    assert doc16.rgba16_document


def test_document_manager_creates_16bit_document():
    dm = DocumentManager()
    doc = dm.new_document(width=200, height=150, pixel_format=1, activate=False)
    assert doc.pixel_format == 1
    assert doc.rgba16_document


def test_schema_validates_pixel_format():
    valid_8 = {"dpi": 300, "paper": {}, "color_profile_id": 0, "pixel_format": 0}
    valid_16 = {"dpi": 300, "paper": {}, "color_profile_id": 0, "pixel_format": 1}
    validate_auxiliary(valid_8)
    validate_auxiliary(valid_16)

    for invalid in (-1, 2, 99, "1", None, 1.0):
        with pytest.raises(DocumentFormatError):
            validate_auxiliary({"dpi": 300, "paper": {}, "color_profile_id": 0, "pixel_format": invalid})


def test_save_capture_and_restore_16bit_roundtrip(tmp_path):
    backend = AladynBackend()
    dm = DocumentManager()
    doc = dm.new_document(128, 128, pixel_format=1, activate=False)
    backend.set_active_document_context(doc.uid, doc.width, doc.height, doc.pixel_format)

    # Put a dab on active layer
    backend.start_stroke(10.0, 10.0, 1.0)
    backend.end_stroke()

    lmn_path = tmp_path / "test16.lmn"
    capture = capture_document(doc, backend, lmn_path)
    assert capture.manifest["pixel_format"] == 1

    # Verify tile payload is encoded as 16-bit block
    assert len(capture.raster_layers) == 1
    tile_bytes = capture.snapshot.encode_layer(0)
    assert len(tile_bytes) > 0

    # Restore in new context
    restored_doc = Document("doc_restored", "Restored", 128, 128, pixel_format=1)
    backend.set_active_document_context(restored_doc.uid, 128, 128, 1)
    payloads = {capture.raster_layers[0][1]: tile_bytes, **capture.extras}
    restore_document(restored_doc, backend, capture.manifest, payloads)

    assert restored_doc.pixel_format == 1
    assert restored_doc.rgba16_document


def test_backend_capabilities_and_qimage_format():
    backend = AladynBackend()

    # 8-bit document
    backend.set_active_document_context("doc_cap8", 64, 64, pixel_format=0)
    caps8 = backend.get_capabilities()
    assert caps8["rgba16_document"] is False
    assert caps8["document_pixel_format"] == "RGBA8"
    qimg8 = backend.get_qimage()
    assert qimg8 is not None
    assert qimg8.format() == QImage.Format_RGBA8888

    # 16-bit document
    backend.set_active_document_context("doc_cap16", 64, 64, pixel_format=1)
    caps16 = backend.get_capabilities()
    assert caps16["rgba16_document"] is True
    assert caps16["document_pixel_format"] == "RGBA16"
    qimg16 = backend.get_qimage()
    assert qimg16 is not None
    assert qimg16.format() == QImage.Format_RGBA64


def test_export_16bit_image(tmp_path):
    backend = AladynBackend()
    backend.set_active_document_context("doc_exp16", 32, 32, pixel_format=1)
    backend.start_stroke(5.0, 5.0, 1.0)
    backend.end_stroke()

    png_target = tmp_path / "export16.png"
    assert backend.export_image(png_target)
    assert png_target.exists()
    reader = QImage(os.fspath(png_target))
    assert not reader.isNull()
    assert reader.width() == 32
    assert reader.height() == 32


def test_new_document_dialog_pixel_format(qapp):
    from ui.core.screens.new_document_dialog import NewDocumentDialog
    dlg = NewDocumentDialog()
    assert hasattr(dlg, "cmb_pixel_format")
    dlg.cmb_pixel_format.setCurrentIndex(0)
    params8 = dlg.get_document_params()
    assert params8["pixel_format"] == 0
    assert dlg.spn_width.maximum() == 16384

    dlg.cmb_pixel_format.setCurrentIndex(1)
    params16 = dlg.get_document_params()
    assert params16["pixel_format"] == 1
    assert dlg.spn_width.maximum() == 8192
    assert "16-bit" in dlg.lbl_ram_estimate.text()
    dlg.close()

