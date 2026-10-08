"""Crash reports from birth to the user's answer: collect, keep, send or discard.

A report is born in three ways: the previous session died (native stack archived
by `crash_log.py`, minidump written by the engine), a Python exception escaped to
the global hook during this session, or the user asked for one (Help menu). It is
kept as a zip in `logs/crash-reports/` until the user decides; it leaves the
machine only with consent, and without the user's name, home folder or e-mails.
"""

from __future__ import annotations

import getpass
import logging
import platform
import sys
import time
import traceback
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from ui.core.diagnostics.crash_report import CrashKind, CrashReport
from ui.core.diagnostics.report_privacy import ReportConsent, scrub
from ui.core.engine.backend_protocols import RoleProvider, RuntimeServicesProtocol
from ui.infrastructure.diagnostics import SentryEndpoint, report_bundle, upload_event, upload_minidump

logger = logging.getLogger(__name__)
LOG_FILE = "lumenia_latest.log"


class SendResult(Enum):
    SENT = "sent"
    NO_ENDPOINT = "no_endpoint"   # no DSN configured: the user attaches the zip to an e-mail
    FAILED = "failed"


@dataclass(frozen=True)
class AppFacts:
    version: str
    channel: str
    dsn: str = ""


class DiagnosticsService:
    def __init__(self, engine: RoleProvider[RuntimeServicesProtocol], logs_dir: Path, facts: AppFacts,
                 consent: ReportConsent = ReportConsent.ASK) -> None:
        self._engine = engine
        self._logs_dir = logs_dir
        self._reports_dir = report_bundle.reports_dir(logs_dir)
        self._facts = facts
        self.consent = consent
        self._python_error_reported = False

    # ── Birth ─────────────────────────────────────────────────────────────

    def install(self) -> bool:
        """Asks the engine to write a minidump if the process dies."""
        engine = self._engine()
        return bool(engine and engine.install_crash_handler(str(report_bundle.dumps_dir(self._logs_dir))))

    def collect_previous_session(self, archived_native_log: Optional[Path]) -> Optional[Path]:
        """Bundles what the last session left when it died; None if it ended normally."""
        dumps = report_bundle.fresh_dumps(report_bundle.dumps_dir(self._logs_dir))
        if archived_native_log is None and not dumps:
            return None
        stack = archived_native_log.read_text(encoding="utf-8", errors="replace") if archived_native_log else ""
        first = next((line.strip() for line in stack.splitlines() if line.strip()), "queda nativa")
        texts = {"native_stack.txt": stack, "log_tail.txt": report_bundle.tail(self._logs_dir / LOG_FILE)}
        return self._bundle(CrashKind.NATIVE, first, texts, dumps)

    def record_python_error(self, record: logging.LogRecord) -> Optional[Path]:
        """The first unhandled Python exception of the session becomes a report (later ones only log)."""
        if self._python_error_reported or not record.exc_info:
            return None
        self._python_error_reported = True
        exc_type, exc, tb = record.exc_info
        summary = "".join(traceback.format_exception_only(exc_type, exc)).strip()
        texts = {"python_traceback.txt": "".join(traceback.format_exception(exc_type, exc, tb)),
                 "log_tail.txt": report_bundle.tail(self._logs_dir / LOG_FILE)}
        return self._bundle(CrashKind.PYTHON, summary, texts, [])

    def create_manual_report(self) -> Path:
        dumps: list[Path] = []
        engine = self._engine()
        dump = report_bundle.dumps_dir(self._logs_dir) / f"manual-{time.strftime('%Y%m%d-%H%M%S')}.dmp"
        if engine and engine.write_diagnostic_dump(str(dump)) and dump.is_file():
            dumps.append(dump)
        texts = {"log_tail.txt": report_bundle.tail(self._logs_dir / LOG_FILE, 2000)}
        return self._bundle(CrashKind.MANUAL, "relatório pedido pelo usuário", texts, dumps)

    # ── Life ──────────────────────────────────────────────────────────────

    def pending(self) -> list[tuple[CrashReport, Path]]:
        found = []
        for bundle in report_bundle.pending_bundles(self._reports_dir):
            try:
                found.append((CrashReport.from_manifest(report_bundle.read_manifest(bundle)), bundle))
            except (OSError, KeyError, ValueError):
                logger.warning("Relatório ilegível descartado: %s", bundle.name)
                report_bundle.discard(bundle)
        return found

    def send(self, report: CrashReport, bundle: Path) -> SendResult:
        endpoint = SentryEndpoint.parse(self._facts.dsn)
        if endpoint is None:
            return SendResult.NO_ENDPOINT
        tags = {"release": report.app_version, "channel": report.update_channel, "kind": report.kind.value,
                "simd": report.engine_simd or "unknown"}
        try:
            dumps = [name for name in report.files if name.endswith(".dmp")]
            texts = {name: report_bundle.read_member(bundle, name) for name in report.files
                     if name.endswith(".txt")}
            if dumps:
                sent = upload_minidump(endpoint, (dumps[0], report_bundle.read_member(bundle, dumps[0])), tags, texts)
            else:
                extra = {name: data.decode("utf-8", errors="replace")[-30000:] for name, data in texts.items()}
                sent = upload_event(endpoint, report.summary, tags, extra)
        except OSError as exc:
            logger.warning("Envio do relatório %s falhou: %s", report.report_id, exc)
            return SendResult.FAILED
        if sent:
            report_bundle.mark_sent(bundle)
        return SendResult.SENT if sent else SendResult.FAILED

    def discard(self, bundle: Path) -> None:
        report_bundle.discard(bundle)

    # ── Inside ────────────────────────────────────────────────────────────

    def _bundle(self, kind: CrashKind, summary: str, texts: dict[str, str], dumps: list[Path]) -> Path:
        home, user = Path.home(), getpass.getuser()
        clean = {name: scrub(text, home, user) for name, text in texts.items() if text}
        report = CrashReport(
            report_id=f"{time.strftime('%Y%m%d-%H%M%S')}-{kind.value}", kind=kind,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"), app_version=self._facts.version,
            update_channel=self._facts.channel, platform=platform.platform(),
            python_version=sys.version.split()[0], summary=scrub(summary, home, user)[:300],
            files=tuple(sorted(clean)) + tuple(path.name for path in dumps))
        return report_bundle.write_bundle(self._reports_dir, report.report_id, report.to_manifest(), clean, dumps)


class PythonErrorHandler(logging.Handler):
    """Turns the CRITICAL record of the global exception hook into a report."""

    def __init__(self, service: DiagnosticsService) -> None:
        super().__init__(level=logging.CRITICAL)
        self._service = service

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._service.record_python_error(record)
        except OSError:
            self.handleError(record)
