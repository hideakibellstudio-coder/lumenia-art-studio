import json
import zipfile

from ui.core.plugins.manager import PluginManager


def _package(path, entries):
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def _manifest(plugin_id, **overrides):
    manifest = {
        "id": plugin_id,
        "version": "1.0.0",
        "minimum_api_version": 1,
        "dependencies": [],
        "permissions": [],
        "entrypoint": "__init__.py",
    }
    manifest.update(overrides)
    return json.dumps(manifest)


def _plugin_source(class_name="SamplePlugin", plugin_id="sample"):
    return f'''from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata

class {class_name}(BasePlugin):
    def get_metadata(self):
        return PluginMetadata(
            id="{plugin_id}", name="Sample", version="1.0.0",
            author="Test", description="Test plugin",
        )
'''


def test_plugin_install_requires_manifest_and_promotes_staging(tmp_path):
    manager = PluginManager(str(tmp_path / "plugins"))
    package = tmp_path / "valid.zip"
    _package(package, {
        "sample/manifest.json": _manifest("sample"),
        "sample/__init__.py": _plugin_source(),
    })
    assert manager.load_plugin_from_source(str(package)) is True
    assert (tmp_path / "plugins" / "sample" / "__init__.py").exists()
    assert not list((tmp_path / "plugins").glob(".plugin-staging-*"))


def test_plugin_install_rejects_traversal_without_touching_root(tmp_path):
    manager = PluginManager(str(tmp_path / "plugins"))
    package = tmp_path / "invalid.zip"
    _package(package, {
        "manifest.json": _manifest("bad"),
        "../../outside.txt": "no",
    })
    assert manager.load_plugin_from_source(str(package)) is None
    assert not (tmp_path / "outside.txt").exists()
    assert not list((tmp_path / "plugins").glob(".plugin-staging-*"))


def test_plugin_install_rejects_existing_id_without_overwriting(tmp_path):
    manager = PluginManager(str(tmp_path / "plugins"))
    target = tmp_path / "plugins" / "sample"
    target.mkdir(parents=True)
    (target / "keep.txt").write_text("keep", encoding="utf-8")
    package = tmp_path / "duplicate.zip"
    _package(package, {
        "manifest.json": _manifest("sample"),
        "__init__.py": "changed\n",
    })
    assert manager.load_plugin_from_source(str(package)) is None
    assert (target / "keep.txt").read_text(encoding="utf-8") == "keep"


def test_plugin_install_rejects_incomplete_or_unsupported_manifest(tmp_path):
    manager = PluginManager(str(tmp_path / "plugins"))
    package = tmp_path / "invalid-manifest.zip"
    _package(package, {
        "manifest.json": json.dumps({"id": "sample", "version": "1.0.0"}),
        "__init__.py": _plugin_source(),
    })
    assert manager.load_plugin_from_source(str(package)) is None
    assert not (tmp_path / "plugins" / "sample").exists()

    _package(package, {
        "manifest.json": _manifest("sample", permissions=["subprocess"]),
        "__init__.py": _plugin_source(),
    })
    assert manager.load_plugin_from_source(str(package)) is None
    assert not (tmp_path / "plugins" / "sample").exists()


def test_plugin_install_verifies_declared_integrity(tmp_path):
    manager = PluginManager(str(tmp_path / "plugins"))
    package = tmp_path / "invalid-integrity.zip"
    _package(package, {
        "manifest.json": _manifest("sample", integrity={
            "algorithm": "sha256",
            "files": {"__init__.py": "0" * 64},
        }),
        "__init__.py": _plugin_source(),
    })
    assert manager.load_plugin_from_source(str(package)) is None
    assert not (tmp_path / "plugins" / "sample").exists()


def test_plugin_install_quarantines_promoted_package_without_plugin_class(tmp_path):
    manager = PluginManager(str(tmp_path / "plugins"))
    package = tmp_path / "broken.zip"
    _package(package, {
        "manifest.json": _manifest("broken"),
        "__init__.py": "raise RuntimeError('broken package')\n",
    })
    assert manager.load_plugin_from_source(str(package)) is None
    assert not (tmp_path / "plugins" / "broken").exists()
    quarantined = tmp_path / "plugins" / ".plugin-quarantine"
    assert any(quarantined.iterdir())


def test_plugin_install_quarantines_metadata_that_diverges_from_manifest(tmp_path):
    manager = PluginManager(str(tmp_path / "plugins"))
    package = tmp_path / "mismatched-metadata.zip"
    _package(package, {
        "manifest.json": _manifest("sample"),
        "__init__.py": _plugin_source(plugin_id="other"),
    })
    assert manager.load_plugin_from_source(str(package)) is None
    assert not (tmp_path / "plugins" / "sample").exists()
    assert any((tmp_path / "plugins" / ".plugin-quarantine").iterdir())
