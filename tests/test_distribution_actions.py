"""DistributionActions (ui/boundary/orchestrator): the crash handler at start and the update offer."""
from __future__ import annotations

import pytest
from PySide6 import QtWidgets

from ui.boundary.orchestrator import distribution_actions
from ui.core.dialogs.update_dialog import UpdateChoice
from ui.infrastructure.updater import FoundUpdate


class FakeEngine:
    def __init__(self) -> None:
        self.crash_folders: list[str] = []

    def install_crash_handler(self, directory: str) -> bool:
        self.crash_folders.append(directory)
        return True

    def write_diagnostic_dump(self, _path: str) -> bool:
        return False


class FakeConfig:
    def __init__(self) -> None:
        self.data: dict[str, dict] = {"diagnostics": {"consent": "never"}}

    def get_section(self, section: str) -> dict:
        return dict(self.data.get(section, {}))

    def get(self, section: str, key: str, default=None):
        return self.data.get(section, {}).get(key, default)

    def set(self, section: str, key: str, value, auto_save: bool = True) -> None:
        self.data.setdefault(section, {})[key] = value

    def set_section(self, section: str, data: dict, auto_save: bool = True) -> None:
        self.data[section] = dict(data)


class RecordingUpdateDialog:
    """Stands in for the modal dialog: records what it was shown and answers `choice`."""

    shown: list[tuple[str, str]] = []
    choice = UpdateChoice.LATER

    def __init__(self, offer, current_version: str, _parent) -> None:
        type(self).shown.append((offer.version, current_version))

    def exec(self) -> int:
        return 0


@pytest.fixture
def actions(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(distribution_actions, "UpdateDialog", RecordingUpdateDialog)
    RecordingUpdateDialog.shown, RecordingUpdateDialog.choice = [], UpdateChoice.LATER
    window = QtWidgets.QWidget()
    qtbot.addWidget(window)
    engine = FakeEngine()
    built = distribution_actions.DistributionActions(window, lambda: engine, FakeConfig(), tmp_path / "logs")
    built.engine = engine
    yield built
    built.shutdown()


def test_the_start_installs_the_crash_handler(actions):
    actions.start(None)
    assert len(actions.engine.crash_folders) == 1


@pytest.mark.parametrize("choice,downloads", [
    (UpdateChoice.RESTART_NOW, 1),
    (UpdateChoice.ON_EXIT, 1),
    (UpdateChoice.LATER, 0),
])
def test_a_found_update_is_offered_and_only_downloaded_when_the_user_chooses(actions, monkeypatch, choice, downloads):
    started: list[FoundUpdate] = []
    monkeypatch.setattr(actions.updates, "download", started.append)
    RecordingUpdateDialog.choice = choice
    found = FoundUpdate("0.3.0", "<!-- released: 2099-01-01 -->\n## Novidades", None)

    actions.updates.worker.found.emit(found)

    assert [version for version, _ in RecordingUpdateDialog.shown] == ["0.3.0"]
    assert started == [found] * downloads
