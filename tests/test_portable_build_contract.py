import json

from scripts import build_portable


def test_portable_command_includes_native_engine_and_runtime_data():
    command = build_portable.nuitka_command()
    joined = "\n".join(command)
    assert "--standalone" in command
    assert "--enable-plugin=pyside6" in command
    assert "--windows-console-mode=disable" in command
    assert "--include-package=plugins" in command
    assert "--include-package=ui" in command
    assert "--include-module=aladyn_engine_native" in command
    assert "--nofollow-import-to=numpy" in command
    assert "--nofollow-import-to=scipy" in command
    assert not any("aladyn_engine_native" in arg and arg.startswith("--include-data-files=")
                   for arg in command)
    assert "numpy.libs/" in joined
    assert "scipy.libs/" in joined
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


def test_distribution_is_normalized_to_the_installer_path(tmp_path):
    generated = tmp_path / "main.dist"
    generated.mkdir()
    assert build_portable._canonical_distribution(tmp_path) == tmp_path / "Lumenia.dist"


def test_distribution_verification_does_not_require_plugin_source_files(tmp_path, monkeypatch):
    distribution = tmp_path / "Lumenia.dist"
    (distribution / "assets").mkdir(parents=True)
    (distribution / "ui" / "core" / "theme" / "themes").mkdir(parents=True)
    (distribution / "Lumenia.exe").write_bytes(b"binary")
    native = tmp_path / "aladyn_engine_native.cp314-win_amd64.pyd"
    native.write_bytes(b"native")
    (distribution / "aladyn_engine_native.pyd").write_bytes(b"native")
    monkeypatch.setattr(build_portable, "_native_extension", lambda: native)

    assert build_portable.verify_distribution(tmp_path) == distribution
    assert (distribution / "release-manifest.json").exists()
