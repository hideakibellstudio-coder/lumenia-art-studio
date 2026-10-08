"""The license in a session: the engine judges, the service saves only what was accepted, the dialog follows."""
from __future__ import annotations

import pytest

from ui.core.licensing import LicenseService, LicenseState, LicenseStatus
from ui.infrastructure.licensing import LICENSE_FILE, LicenseStore


class FakeEngine:
    """Accepts the token "GOOD", refuses anything else; records what it was asked."""

    def __init__(self) -> None:
        self.applied: list[str] = []
        self.cleared = 0

    def license_apply(self, token: str) -> dict[str, str]:
        self.applied.append(token)
        if token == "GOOD":
            return {"state": "licensed", "license_id": "L-000001", "sku": "pro", "holder_name": "Fulana",
                    "issued_on": "2026-10-08", "updates_until": "2027-10-08", "expires_on": ""}
        return {"state": "bad_signature"}

    def license_status(self) -> dict[str, str]:
        return {"state": "unlicensed"}

    def license_clear(self) -> None:
        self.cleared += 1


@pytest.fixture
def engine():
    return FakeEngine()


@pytest.fixture
def store(tmp_path):
    return LicenseStore(tmp_path)


def test_status_reads_the_engine_dict_and_unknown_states_are_never_licensed():
    assert LicenseStatus.from_engine({"state": "licensed", "sku": "pro"}).is_licensed
    assert LicenseStatus.from_engine({"state": "weird"}).state is LicenseState.UNSUPPORTED
    assert LicenseStatus.from_engine({}).state is LicenseState.UNSUPPORTED


@pytest.mark.parametrize("updates_until,release,covered", [
    ("2027-10-08", "2027-10-08", True), ("2027-10-08", "2027-10-09", False),
    ("2027-10-08", "", None), ("", "2030-01-01", True),
])
def test_a_release_is_covered_until_the_update_date(updates_until, release, covered):
    status = LicenseStatus(state=LicenseState.LICENSED, updates_until=updates_until)
    assert status.covers_release(release) is covered


def test_without_a_license_every_release_is_covered():
    assert LicenseStatus().covers_release("2099-01-01") is True


def test_an_accepted_key_is_saved_and_announced(qapp, engine, store):
    service = LicenseService(lambda: engine, store)
    seen = []
    service.statusChanged.connect(seen.append)
    assert service.activate("  GOOD \n").is_licensed
    assert store.read() == "GOOD"
    assert seen and seen[-1].holder_name == "Fulana"


def test_a_refused_key_is_neither_saved_nor_replaces_the_session(qapp, engine, store):
    service = LicenseService(lambda: engine, store)
    service.activate("GOOD")
    status = service.activate("FORGED")
    assert status.state is LicenseState.BAD_SIGNATURE
    assert store.read() == "GOOD" and service.status.is_licensed


def test_restore_applies_the_saved_key_and_keeps_a_refused_one_on_disk(qapp, engine, store):
    store.write("GOOD")
    assert LicenseService(lambda: engine, store).restore().is_licensed
    store.write("EXPIRED-ONE")
    service = LicenseService(lambda: engine, store)
    assert service.restore().state is LicenseState.BAD_SIGNATURE
    assert store.read() == "EXPIRED-ONE"


def test_deactivate_clears_the_file_and_the_engine(qapp, engine, store):
    service = LicenseService(lambda: engine, store)
    service.activate("GOOD")
    service.deactivate()
    assert store.read() == "" and engine.cleared == 1 and not service.status.is_licensed


def test_without_an_engine_nothing_is_licensed(qapp, store):
    store.write("GOOD")
    service = LicenseService(lambda: None, store)
    assert service.restore().state is LicenseState.UNSUPPORTED
    assert service.activate("GOOD").state is LicenseState.UNSUPPORTED


def test_the_store_writes_atomically_and_leaves_no_temporary(tmp_path):
    store = LicenseStore(tmp_path / "data")
    store.write("TOKEN")
    assert [p.name for p in (tmp_path / "data").iterdir()] == [LICENSE_FILE]
    store.clear()
    store.clear()  # removing twice is fine
    assert store.read() == ""


def test_the_dialog_shows_the_holder_and_activates_through_the_service(qapp, engine, store):
    from ui.core.dialogs.license_dialog import LicenseDialog, describe

    service = LicenseService(lambda: engine, store)
    dialog = LicenseDialog(service)
    try:
        dialog.txt_key.setPlainText("GOOD")
        dialog.btn_activate.click()
        assert "Fulana" in dialog.lbl_status.text()
        assert "Fulana" in describe(service.status)
    finally:
        dialog.deleteLater()
