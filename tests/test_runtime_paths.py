from pathlib import Path
import sys

from ui.infrastructure import runtime_paths


def test_development_root_points_to_the_repository():
    assert runtime_paths.app_root() == Path(__file__).parents[1]
    assert runtime_paths.resource_path("main.py").is_file()


def test_packaged_root_uses_the_executable_directory(monkeypatch, tmp_path):
    executable = tmp_path / "Lumenia.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    assert runtime_paths.is_packaged()
    assert runtime_paths.app_root() == tmp_path
    assert runtime_paths.resource_path("assets") == tmp_path / "assets"


def test_installed_data_lives_outside_the_program_folder(monkeypatch, tmp_path):
    """Velopack replaces the program folder (`current\\`) on every update: data beside the
    executable would vanish (until 2026-10-08 it lived in `data\\` there)."""
    executable = tmp_path / "current" / "Lumenia.exe"
    executable.parent.mkdir()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert not runtime_paths.is_portable()
    assert runtime_paths.writable_data_dir() == tmp_path / "Roaming" / "Lumenia"


def test_a_portable_copy_keeps_its_data_beside_itself(monkeypatch, tmp_path):
    executable = tmp_path / "Lumenia.exe"
    (tmp_path / runtime_paths.PORTABLE_MARKER).write_text("", encoding="utf-8")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    assert runtime_paths.is_portable()
    assert runtime_paths.writable_data_dir() == tmp_path / "data"


def test_legacy_data_is_imported_once_without_overwriting(tmp_path):
    from ui.infrastructure.legacy_data import MARKER, import_legacy_data

    legacy = tmp_path / "old" / "data"
    (legacy / "plugins" / "brush_pack").mkdir(parents=True)
    (legacy / "plugins" / "brush_pack" / "plugin.json").write_text("{}", encoding="utf-8")
    (legacy / "license.lic").write_text("OLD", encoding="utf-8")
    target = tmp_path / "Roaming" / "Lumenia"
    target.mkdir(parents=True)
    (target / "license.lic").write_text("NEW", encoding="utf-8")

    copied = import_legacy_data(target, [tmp_path / "missing", legacy])
    assert copied == [target / "plugins" / "brush_pack" / "plugin.json"]
    assert (target / "license.lic").read_text(encoding="utf-8") == "NEW"
    assert (target / MARKER).exists()
    assert import_legacy_data(target, [legacy]) == []
