import json

from scripts import build_portable


def test_portable_command_includes_native_engine_and_runtime_data():
    command = build_portable.nuitka_command()
    joined = "\n".join(command)
    assert "--standalone" in command
    assert "--enable-plugin=pyside6" in command
    assert "--include-package=plugins" in command
    assert "--include-package=ui" in command
    assert "aladyn_engine_native" in joined
    assert "assets" in joined
    assert "themes" in joined


def test_release_manifest_hashes_every_file(tmp_path):
    distribution = tmp_path / "Lumenia.dist"
    distribution.mkdir()
    (distribution / "Lumenia.exe").write_bytes(b"binary")
    manifest_path = build_portable.write_release_manifest(distribution)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["files"] == [{
        "path": "Lumenia.exe",
        "bytes": 6,
        "sha256": "9a3a45d01531a20e89ac6ae10b0b0beb0492acd7216a368aa062d1a5fecaf9cd",
    }]
