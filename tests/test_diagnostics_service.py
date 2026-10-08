"""Crash reports: born on this machine, cleaned of the user's identity, sent only when allowed."""
from __future__ import annotations

import logging
import sys
import zipfile
from pathlib import Path

import pytest

from ui.core.diagnostics import AppFacts, CrashKind, DiagnosticsService, PythonErrorHandler, ReportConsent, SendResult, scrub
from ui.infrastructure.diagnostics import SentryEndpoint, report_bundle


class FakeEngine:
    def __init__(self) -> None:
        self.handler_dir = ""

    def install_crash_handler(self, directory: str) -> bool:
        self.handler_dir = directory
        return True

    def write_diagnostic_dump(self, path: str) -> bool:
        Path(path).write_bytes(b"MDMP fake dump")
        return True


@pytest.fixture
def service(tmp_path, monkeypatch):
    from ui.core.diagnostics import diagnostics_service

    # The report hides whoever runs the suite; pin "Hide" so the check is the same on any machine.
    home = tmp_path / "Users" / "Hide"
    monkeypatch.setattr(diagnostics_service.getpass, "getuser", lambda: "Hide")
    monkeypatch.setattr(diagnostics_service.Path, "home", classmethod(lambda cls: cls(home)))
    engine = FakeEngine()
    (tmp_path / "lumenia_latest.log").write_text(f"linha 1\n{home / 'Pictures' / 'arte.lmn'} aberto por hide@x.com\n",
                                                 encoding="utf-8")
    return DiagnosticsService(lambda: engine, tmp_path, AppFacts("0.2.0", "stable")), engine


def test_scrub_removes_home_user_name_and_emails(tmp_path):
    home = tmp_path / "Users" / "Hide"
    text = f"{home / 'Desktop' / 'a.lmn'} (Hide) fulana@example.com {home.as_posix()}"
    clean = scrub(text, home, "Hide")
    assert "Hide" not in clean and "fulana@example.com" not in clean
    assert "~" in clean and "<email>" in clean


def test_consent_defaults_to_asking():
    assert ReportConsent.parse("always") is ReportConsent.ALWAYS
    assert ReportConsent.parse(None) is ReportConsent.ASK


def test_install_points_the_engine_at_the_dumps_folder(service, tmp_path):
    svc, engine = service
    assert svc.install()
    assert Path(engine.handler_dir) == report_bundle.dumps_dir(tmp_path)


def test_a_clean_previous_session_makes_no_report(service):
    svc, _ = service
    assert svc.collect_previous_session(None) is None
    assert svc.pending() == []


def test_a_native_crash_becomes_a_bundle_with_stack_log_and_dump(service, tmp_path):
    svc, _ = service
    stack = tmp_path / "native_crash-20261008-101010.log"
    stack.write_text(f"Windows fatal exception: access violation\n  File {tmp_path / 'Users' / 'Hide' / 'x.py'}\n",
                     encoding="utf-8")
    dump = report_bundle.dumps_dir(tmp_path) / "lumenia-20261008-101010-42.dmp"
    dump.write_bytes(b"MDMP")
    bundle = svc.collect_previous_session(stack)
    assert bundle is not None and not dump.exists(), "the dump moves into the bundle"
    ((report, path),) = svc.pending()
    assert path == bundle and report.kind is CrashKind.NATIVE
    assert report.summary.startswith("Windows fatal exception")
    with zipfile.ZipFile(bundle) as archive:
        names = set(archive.namelist())
        log = archive.read("log_tail.txt").decode("utf-8")
    assert {"manifest.json", "native_stack.txt", "log_tail.txt", dump.name} <= names
    assert "Hide" not in log and "hide@x.com" not in log


def test_only_the_first_python_error_of_a_session_becomes_a_report(service):
    svc, _ = service
    log = logging.getLogger("test.diagnostics.crash")
    handler = PythonErrorHandler(svc)
    log.addHandler(handler)
    try:
        for _ in range(2):
            try:
                raise RuntimeError("boom")
            except RuntimeError:
                log.critical("unhandled", exc_info=sys.exc_info())
    finally:
        log.removeHandler(handler)
    ((report, _),) = svc.pending()
    assert report.kind is CrashKind.PYTHON and "RuntimeError: boom" in report.summary


def test_a_manual_report_carries_a_dump_of_the_running_process(service):
    svc, _ = service
    bundle = svc.create_manual_report()
    ((report, path),) = svc.pending()
    assert path == bundle and report.kind is CrashKind.MANUAL
    assert any(name.endswith(".dmp") for name in report.files)


def test_without_a_dsn_nothing_leaves_and_the_bundle_stays(service):
    svc, _ = service
    bundle = svc.create_manual_report()
    report, _ = svc.pending()[0]
    assert svc.send(report, bundle) is SendResult.NO_ENDPOINT
    assert bundle.exists()


def test_discard_removes_the_bundle(service):
    svc, _ = service
    bundle = svc.create_manual_report()
    svc.discard(bundle)
    assert svc.pending() == []


@pytest.mark.parametrize("dsn,ok", [
    ("https://abc123@o1.ingest.sentry.io/456", True),
    ("https://abc@glitchtip.example.com:8443/2", True),
    ("", False), ("not a url", False), ("https://o1.ingest.sentry.io/456", False),
])
def test_the_dsn_is_parsed_into_the_endpoints(dsn, ok):
    endpoint = SentryEndpoint.parse(dsn)
    assert (endpoint is not None) is ok
    if endpoint is not None:
        assert endpoint.url("minidump").endswith(f"/minidump/?sentry_key={endpoint.public_key}")


def test_old_bundles_are_pruned(tmp_path):
    for index in range(report_bundle.KEEP_PENDING + 3):
        report_bundle.write_bundle(tmp_path, f"2026100{index:02d}-manual", {"report_id": "x"}, {"a.txt": "a"}, [])
    assert len(report_bundle.pending_bundles(tmp_path)) == report_bundle.KEEP_PENDING


def test_the_crash_dialog_records_the_choice(qapp, service):
    from ui.core.dialogs.crash_report_dialog import CrashReportChoice, CrashReportDialog

    svc, _ = service
    svc.create_manual_report()
    report, _ = svc.pending()[0]
    dialog = CrashReportDialog(report)
    try:
        dialog.chk_always.setChecked(True)
        assert dialog.choice is CrashReportChoice.KEEP and dialog.always_send
    finally:
        dialog.deleteLater()
