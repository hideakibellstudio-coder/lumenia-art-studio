"""When to look for an update and whether it may be offered (ui/core/updates)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from ui.core.licensing import LicenseState, LicenseStatus
from ui.core.updates import CHECK_INTERVAL, UpdateChannel, UpdateDecision, UpdateOffer, UpdatePreferences, decide

NOW = datetime(2026, 10, 8, 12, 0, 0)
LICENSED = LicenseStatus(state=LicenseState.LICENSED, updates_until="2027-01-31")


def test_preferences_round_trip_and_survive_bad_values():
    prefs = UpdatePreferences.from_config({"channel": "beta", "auto_check": False, "last_check": "x"})
    assert prefs.channel is UpdateChannel.BETA and not prefs.auto_check
    assert UpdatePreferences.from_config(prefs.to_config()) == prefs
    fallback = UpdatePreferences.from_config({"channel": "nightly", "auto_check": "yes"})
    assert fallback.channel is UpdateChannel.STABLE and fallback.auto_check


@pytest.mark.parametrize("last_check,auto,due", [
    ("", True, True),
    ((NOW - CHECK_INTERVAL - timedelta(minutes=1)).isoformat(), True, True),
    ((NOW - timedelta(hours=1)).isoformat(), True, False),
    ((NOW + timedelta(days=3)).isoformat(), True, True),   # clock moved back: check again
    ("not a date", True, True),
    ("", False, False),
])
def test_a_check_is_due_every_twenty_hours_when_enabled(last_check, auto, due):
    assert UpdatePreferences(auto_check=auto, last_check=last_check).is_check_due(NOW) is due


def test_the_release_date_comes_from_the_notes_and_is_hidden_from_the_reader():
    offer = UpdateOffer("0.3.0", "<!-- released: 2026-12-01 -->\n## Novidades\n- pincéis")
    assert offer.release_date == "2026-12-01"
    assert offer.readable_notes.startswith("## Novidades")
    assert UpdateOffer("0.3.0", "sem data").release_date == ""


@pytest.mark.parametrize("notes,status,decision", [
    ("<!-- released: 2026-12-01 -->", LICENSED, UpdateDecision.OFFER),
    ("<!-- released: 2027-02-01 -->", LICENSED, UpdateDecision.NOT_COVERED),
    ("no date", LICENSED, UpdateDecision.UNKNOWN_COVERAGE),
    ("<!-- released: 2030-01-01 -->", LicenseStatus(), UpdateDecision.OFFER),
])
def test_a_version_the_license_does_not_cover_is_never_offered(notes, status, decision):
    assert decide(UpdateOffer("0.3.0", notes), status) is decision


def test_the_dialog_hides_the_install_buttons_for_an_uncovered_version(qapp):
    from PySide6 import QtWidgets

    from ui.core.dialogs.update_dialog import UpdateDialog

    covered = UpdateDialog(UpdateOffer("0.3.0", "x"), UpdateDecision.OFFER, "0.2.0")
    uncovered = UpdateDialog(UpdateOffer("0.3.0", "x"), UpdateDecision.NOT_COVERED, "0.2.0")
    try:
        assert len(covered.findChildren(QtWidgets.QPushButton)) > len(uncovered.findChildren(QtWidgets.QPushButton))
    finally:
        covered.deleteLater()
        uncovered.deleteLater()


def test_the_updater_is_unavailable_outside_an_installed_copy():
    from ui.infrastructure.updater import VelopackUpdater

    updater = VelopackUpdater("https://github.com/example/releases", "stable")
    assert updater.available is False
    assert updater.check() is None
