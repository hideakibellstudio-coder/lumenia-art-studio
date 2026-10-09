"""Free mode is announced: a welcome once at the first start without a license, a status-bar button after."""
from __future__ import annotations

import pytest
from PySide6 import QtWidgets

from ui.boundary.orchestrator import distribution_actions
from ui.core.components.status_bar import StatusBar
from ui.core.dialogs.welcome_dialog import WelcomeChoice, WelcomeDialog

LICENSED = {"state": "licensed", "license_id": "L-000001", "sku": "pro", "holder_name": "Fulana",
            "issued_on": "2026-10-08", "updates_until": "", "expires_on": ""}


class FakeEngine:
    def __init__(self, answer: dict[str, str]) -> None:
        self.answer = answer

    def license_apply(self, _token: str) -> dict[str, str]:
        return self.answer

    def license_status(self) -> dict[str, str]:
        return self.answer

    def license_clear(self) -> None:
        pass

    def install_crash_handler(self, _directory: str) -> bool:
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


class RecordingWelcome:
    """Stands in for the modal dialog: records that it was shown and answers `choice`."""

    shown = 0
    choice = WelcomeChoice.FREE

    def __init__(self, _parent) -> None:
        type(self).shown += 1

    def exec(self) -> int:
        return 0


@pytest.fixture
def make_actions(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(distribution_actions, "user_data_dir", lambda: tmp_path / "data")
    monkeypatch.setattr(distribution_actions, "WelcomeDialog", RecordingWelcome)
    RecordingWelcome.shown, RecordingWelcome.choice = 0, WelcomeChoice.FREE
    created = []

    def build(saved_token: str = "", answer: dict | None = None, config: FakeConfig | None = None):
        if saved_token:
            (tmp_path / "data").mkdir(exist_ok=True)
            (tmp_path / "data" / "license.lic").write_text(saved_token, encoding="utf-8")
        window = QtWidgets.QWidget()
        qtbot.addWidget(window)
        engine = FakeEngine(answer or {"state": "unlicensed"})
        actions = distribution_actions.DistributionActions(window, lambda: engine, config or FakeConfig(),
                                                           tmp_path / "logs")
        created.append(actions)
        return actions

    yield build
    for actions in created:
        actions.shutdown()


def test_the_first_start_without_a_license_welcomes_once(qtbot, make_actions):
    config = FakeConfig()
    actions = make_actions(config=config)
    free = []
    actions.freeModeChanged.connect(free.append)
    actions.start(None)
    qtbot.waitUntil(lambda: RecordingWelcome.shown == 1)
    assert free == [True] and config.get("licensing", "welcome_shown") is True
    make_actions(config=config).start(None)
    qtbot.wait(50)
    assert RecordingWelcome.shown == 1, "the welcome is shown once, not at every start"


def test_a_licensed_start_neither_welcomes_nor_shows_free_mode(qtbot, make_actions):
    actions = make_actions(saved_token="LUMENIA1-GOOD", answer=LICENSED)
    free = []
    actions.freeModeChanged.connect(free.append)
    actions.start(None)
    qtbot.wait(50)
    assert RecordingWelcome.shown == 0 and free[-1] is False


def test_choosing_activate_opens_the_license_dialog(make_actions, monkeypatch):
    actions = make_actions()
    opened = []
    monkeypatch.setattr(actions, "open_license_dialog", lambda: opened.append(True))
    RecordingWelcome.choice = WelcomeChoice.ACTIVATE
    actions.show_welcome()
    assert opened == [True]


def test_activating_hides_the_status_bar_button(qtbot, make_actions):
    actions = make_actions(answer=LICENSED)
    bar = StatusBar()
    qtbot.addWidget(bar)
    actions.freeModeChanged.connect(bar.show_free_mode)
    bar.show_free_mode(True)
    assert bar.free_mode_btn.isVisibleTo(bar)
    assert actions.license.activate("LUMENIA1-GOOD").is_licensed
    assert not bar.free_mode_btn.isVisibleTo(bar)


def test_the_status_bar_button_asks_for_activation(qtbot):
    bar = StatusBar()
    qtbot.addWidget(bar)
    with qtbot.waitSignal(bar.activateRequested, timeout=500):
        bar.free_mode_btn.click()


def test_the_welcome_dialog_reports_each_choice(qtbot):
    for button, choice in (("btn_activate", WelcomeChoice.ACTIVATE), ("btn_buy", WelcomeChoice.BUY),
                           ("btn_free", WelcomeChoice.FREE)):
        dialog = WelcomeDialog()
        qtbot.addWidget(dialog)
        getattr(dialog, button).click()
        assert dialog.choice is choice
