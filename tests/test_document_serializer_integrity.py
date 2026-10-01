"""Regressões de integridade do formato editável .lmn."""

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PySide6 import QtWidgets

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])

from ui.core.document.document import Document
from ui.core.document.serializer import DocumentFormatError, DocumentSerializer
from tests.persistence_doubles import BackendDouble


class TestDocumentSerializerIntegrity(unittest.TestCase):
    def test_round_trip_writes_versioned_payload(self):
        doc = Document("doc", "Teste", 2, 2)
        doc.layer_manager.add_layer("Pintura")
        with tempfile.TemporaryDirectory() as tmp:
            path = DocumentSerializer.save(doc, BackendDouble(doc), Path(tmp) / "teste")
            manifest, payloads = DocumentSerializer.read(path)
        self.assertEqual(manifest["format"], "lmn")
        self.assertEqual(manifest["version"], DocumentSerializer.FORMAT_VERSION)
        self.assertEqual(list(payloads), ["layers/1.tiles"])
        self.assertTrue(payloads["layers/1.tiles"].startswith(b"LMNT"))

    def test_rejects_duplicate_uids(self):
        manifest = {"format": "lmn", "version": 1, "width": 1, "height": 1,
                    "layers": [{"uid": 1}, {"uid": 1}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.lmn"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
            with self.assertRaises(DocumentFormatError):
                DocumentSerializer.read(path)

    def test_rejects_wrong_payload_size(self):
        manifest = {"format": "lmn", "version": 1, "width": 2, "height": 2,
                    "layers": [{"uid": 1, "pixel_payload": "layers/1.rgba"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.lmn"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                archive.writestr("layers/1.rgba", b"short")
            with self.assertRaises(DocumentFormatError):
                DocumentSerializer.read(path)

    def test_migrates_unversioned_manifest_with_deterministic_defaults(self):
        manifest = {"format": "lmn", "width": 1, "height": 1,
                    "layers": [{"uid": 1, "is_group": False, "is_filter": False}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.lmn"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
            migrated, _ = DocumentSerializer.read(path)
        self.assertEqual(migrated["version"], DocumentSerializer.FORMAT_VERSION)
        self.assertEqual(migrated["zoom"], 1.0)
        self.assertEqual(migrated["paper"]["color"], [255, 255, 255, 255])


if __name__ == "__main__":
    unittest.main()
