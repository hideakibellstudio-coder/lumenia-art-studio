"""A damaged or hand-edited `.lmn` is refused with a document error, never with a bridge error or a library message.

Mutating the manifest and the zip of a real file (1500 mutants, 2026-10-01) found no crash and no hang in the reader and
the native tile decoder; it found two files refused for the wrong reason: a compressed entry that does not decompress
raised `zlib.error` ("invalid distance too far back") and a paper texture id outside the 32-bit range reached the bridge
and raised a pybind `TypeError` with the whole overload signature in the message. Both are `DocumentFormatError` now. The
file also stopped carrying the absolute path where the author saved it (`file_path`, read by nobody): sharing a
`.lmn` shared the folder names of the author's machine.
"""

from __future__ import annotations

import io
import json
import zipfile

import pytest

from ui.core.document.manager import DocumentManager
from ui.core.document.schema import DocumentFormatError
from ui.core.document.serializer import DocumentSerializer
from ui.core.engine.registry import EngineRegistry
from ui.infrastructure.bridge_client.aladyn import AladynBackend


@pytest.fixture
def saved(tmp_path, qapp):
    registry = EngineRegistry.instance()
    previous = registry.get_backend()
    backend = AladynBackend()
    registry.set_backend(backend)
    document = DocumentManager.instance().new_document(64, 48, "hostile")
    backend.set_active_document_context(document.uid, 64, 48)
    backend.set_brush_size(10)
    backend.start_stroke(10, 10, 0.8, 0.0)
    backend.paint_stroke(40, 30, 0.8, 0.02)
    backend.end_stroke()
    path = tmp_path / "doc.lmn"
    DocumentSerializer.save(document, backend, path)
    try:
        yield path
    finally:
        DocumentManager.instance().close_document(document.uid)
        backend.close_document_context(document.uid)
        registry.set_backend(previous)


def _rewrite(path, edit_manifest=None, damage_entry=None):
    entries = {}
    with zipfile.ZipFile(path) as source:
        for info in source.infolist():
            entries[info.filename] = source.read(info.filename)
    if edit_manifest is not None:
        manifest = json.loads(entries["manifest.json"])
        edit_manifest(manifest)
        entries["manifest.json"] = json.dumps(manifest).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as target:
        for name, data in entries.items():
            target.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
    raw = bytearray(buffer.getvalue())
    if damage_entry is not None:
        with zipfile.ZipFile(io.BytesIO(bytes(raw))) as probe:
            info = probe.getinfo(damage_entry)
        start = info.header_offset + 30 + len(info.filename.encode()) + 4
        for offset in range(start, start + 24):  # inside the deflate stream, past its first bytes
            raw[offset] = (raw[offset] + 77) & 0xFF
    path.write_bytes(bytes(raw))


def test_a_manifest_with_a_texture_id_outside_32_bits_is_refused_as_a_document_error(saved):
    _rewrite(saved, lambda m: m["paper"].update(texture_id=2**31))
    with pytest.raises(DocumentFormatError, match="textura do papel"):
        DocumentSerializer.read(saved)


@pytest.mark.parametrize("field, value", [("texture_id", "3"), ("texture_id", None), ("texture_id", -1), ("visible", 1), ("texture_enabled", "yes"), ("color", [1, 2]), ("color", [256, 0, 0, 255]), ("color", "red")])
def test_every_paper_field_has_a_type_and_a_range(saved, field, value):
    _rewrite(saved, lambda m: m["paper"].update({field: value}))
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(saved)


def test_a_compressed_entry_that_does_not_decompress_is_a_corrupt_file_not_a_zlib_message(saved):
    _rewrite(saved, damage_entry="manifest.json")
    with pytest.raises(DocumentFormatError):
        DocumentSerializer.read(saved)


def test_the_file_does_not_carry_the_folder_where_the_author_saved_it(saved):
    with zipfile.ZipFile(saved) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    assert "file_path" not in manifest
    assert str(saved.parent) not in json.dumps(manifest)


def test_a_valid_file_still_reads(saved):
    manifest, _payloads = DocumentSerializer.read(saved)
    assert manifest["paper"]["texture_id"] == 0
