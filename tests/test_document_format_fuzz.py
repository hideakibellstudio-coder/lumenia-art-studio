"""Deterministic malformed-file fuzzing for the untrusted LMN reader."""

from __future__ import annotations

import copy
import json
import random
import zipfile

import pytest

from ui.core.document.document import Document
from ui.core.document.serializer import DocumentFormatError, DocumentSerializer


class _Backend:
    available = True

    def get_layer_pixel_buffer(self, _index):
        return bytes([10, 20, 30, 255]) * 4


def _valid_archive(tmp_path):
    document = Document("fuzz", "Fuzz seed", 2, 2)
    document.layer_manager.add_layer("Paint")
    path = tmp_path / "seed.lmn"
    DocumentSerializer.save(document, _Backend(), path)
    with zipfile.ZipFile(path) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        payloads = {name: archive.read(name) for name in archive.namelist() if name != "manifest.json"}
    return path.read_bytes(), manifest, payloads


def _write_archive(path, manifest, payloads):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, allow_nan=True))
        for name, data in payloads.items():
            archive.writestr(name, data)


@pytest.mark.parametrize("field, invalid_values", [
    ("format", [None, "zip", 4]),
    ("version", [None, True, -1, 3, "2"]),
    ("width", [None, True, -1, 0, 100_001, "2"]),
    ("height", [None, True, -1, 0, 100_001, "2"]),
    ("layers", [None, {}, "layers", [], [{}]]),
    ("active_uid", [True, "1", -1, 999]),
    ("paper", [None, [], "paper"]),
    ("guide_state", [None, [], "guide"]),
    ("sym_state", [None, [], "symmetry"]),
    ("color_profile_id", [None, True, -1, 14, "0"]),
])
def test_generated_invalid_manifest_values_are_rejected(tmp_path, field, invalid_values):
    _raw, manifest, payloads = _valid_archive(tmp_path)
    for index, value in enumerate(invalid_values):
        candidate = copy.deepcopy(manifest)
        candidate[field] = value
        path = tmp_path / f"manifest-{field}-{index}.lmn"
        _write_archive(path, candidate, payloads)
        with pytest.raises(DocumentFormatError):
            DocumentSerializer.read(path)


def test_random_truncations_and_non_zip_bytes_have_only_domain_errors(tmp_path):
    raw, _manifest, _payloads = _valid_archive(tmp_path)
    rng = random.Random(20260911)
    samples = [bytes(rng.randrange(256) for _ in range(length)) for length in range(0, 80, 7)]
    samples.extend(raw[:cut] for cut in sorted({rng.randrange(len(raw)) for _ in range(64)}))
    for index, data in enumerate(samples):
        path = tmp_path / f"mutated-{index}.lmn"
        path.write_bytes(data)
        with pytest.raises(DocumentFormatError):
            DocumentSerializer.read(path)
