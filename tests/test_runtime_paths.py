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
