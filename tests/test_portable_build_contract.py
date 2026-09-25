import json
import sys
import tomllib
from pathlib import Path

import pytest

from scripts import build_portable


@pytest.mark.skipif(sys.platform != "win32", reason="o bundle Nuitka exige o .pyd do Windows na raiz")
def test_portable_command_includes_native_engine_and_runtime_data():
    command = build_portable.nuitka_command()
    joined = "\n".join(command)
    assert "--standalone" in command
    assert "--enable-plugin=pyside6" in command
    assert "--windows-console-mode=disable" in command
    assert "--include-package=ui.plugins" in command
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


def test_portable_command_ships_plugins_themes_and_legal_notices(monkeypatch):
    """Versão que roda em qualquer sistema: o teste acima só roda no Windows e
    ficou pedindo `--include-package=plugins` depois que os plugins foram para
    `ui/plugins` (achado em 2026-09-25)."""
    monkeypatch.setattr(build_portable, "_native_extension", lambda: Path("aladyn_engine_native.pyd"))
    monkeypatch.setattr(build_portable, "_runtime_package_data", lambda name: [f"--include-data-files={name}"])
    command = build_portable.nuitka_command()
    assert "--include-package=ui.plugins" in command
    assert any(arg.endswith("=ui/infrastructure/theme/themes") for arg in command)
    assert any(arg.endswith("=TERMS_AND_LICENSE.txt") for arg in command)
    assert f"--include-data-files={build_portable.NOTICES}=THIRD_PARTY_NOTICES.txt" in command


def test_bundled_packages_ship_their_license_texts(tmp_path):
    copied = build_portable.copy_third_party_licenses(tmp_path, ("Pillow", "pybind11"))
    for package in ("Pillow", "pybind11"):
        texts = [path for path in copied if path.is_relative_to(tmp_path / "licenses" / package)]
        assert texts and all(path.stat().st_size > 0 for path in texts), package


def test_notices_name_every_distributed_dependency():
    notices = build_portable.NOTICES.read_text(encoding="utf-8")
    with (build_portable.ROOT / "pyproject.toml").open("rb") as stream:
        dependencies = tomllib.load(stream)["project"]["dependencies"]
    names = {dep.split(">")[0].split("=")[0].split("<")[0].strip() for dep in dependencies}
    names |= set(build_portable.LICENSED_PACKAGES)
    missing = sorted(name for name in names if name.lower() not in notices.lower())
    assert missing == [], f"dependência distribuída sem aviso em {build_portable.NOTICES.name}: {missing}"
    for text in ("LGPL-3.0.txt", "GPL-3.0.txt"):
        assert (build_portable.NOTICES.parent / text).stat().st_size > 5000


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
    (distribution / "ui" / "infrastructure" / "theme" / "themes").mkdir(parents=True)
    (distribution / "Lumenia.exe").write_bytes(b"binary")
    native = tmp_path / "aladyn_engine_native.cp314-win_amd64.pyd"
    native.write_bytes(b"native")
    (distribution / "aladyn_engine_native.pyd").write_bytes(b"native")
    monkeypatch.setattr(build_portable, "_native_extension", lambda: native)
    monkeypatch.setattr(build_portable, "LICENSED_PACKAGES", ("pybind11",))

    assert build_portable.verify_distribution(tmp_path) == distribution
    assert (distribution / "release-manifest.json").exists()
    manifest = json.loads((distribution / "release-manifest.json").read_text(encoding="utf-8"))
    assert "licenses/pybind11/LICENSE" in {entry["path"] for entry in manifest["files"]}
