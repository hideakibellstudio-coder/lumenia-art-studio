"""DistributionActions — license, crash reports and updates, wired to the window.

Collaborator of the `MainWindow` (see `shell_actions.py`). It builds the three
session services and asks the user when a decision is theirs:

  license       LicenseService       restore at start, Help > License; in free mode a welcome
                                     once and the status bar's "Free version · Activate"
  diagnostics   DiagnosticsService   minidump, last session's crash, Help > Diagnostic report
  updates       UpdateThread         look for a version (every 20 h or on request), download, apply

`start(previous_crash)` runs once the window exists: `app_runner.launch` passes
the native stack the logging setup archived from the previous session.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.diagnostics import AppFacts, CrashReport, DiagnosticsService, PythonErrorHandler, ReportConsent, SendResult
from ui.core.dialogs.crash_report_dialog import CrashReportChoice, CrashReportDialog
from ui.core.dialogs.license_dialog import PURCHASE_URL, LicenseDialog, describe
from ui.core.dialogs.update_dialog import UpdateChoice, UpdateDialog
from ui.core.dialogs.welcome_dialog import WelcomeChoice, WelcomeDialog
from ui.core.engine.backend_protocols import RoleProvider, RuntimeServicesProtocol
from ui.core.licensing import LicenseService, LicenseStatus
from ui.core.updates import UpdateDecision, UpdateOffer, UpdatePreferences, decide
from ui.infrastructure.app_info import APP_UPDATE_REPOSITORY, APP_VERSION, CRASH_REPORT_DSN, SUPPORT_EMAIL
from ui.infrastructure.config import ConfigManager
from ui.infrastructure.i18n import tr
from ui.infrastructure.licensing import LicenseStore
from ui.infrastructure.runtime_paths import is_packaged, user_data_dir, writable_data_dir
from ui.infrastructure.updater import FoundUpdate, UpdateThread, VelopackUpdater

from .shell_actions import ShellActions

FIRST_CHECK_DELAY_MS = 15000
CRASH_LOGGER = "Lumenia.System.Crash"


class DistributionActions(ShellActions):
    freeModeChanged = QtCore.Signal(bool)   # True while exports carry the watermark

    def __init__(self, window: QtWidgets.QWidget, backend: RoleProvider[RuntimeServicesProtocol],
                 config: ConfigManager, logs_dir: Path) -> None:
        super().__init__(window)
        self._window = window
        self._config = config
        self._preferences = UpdatePreferences.from_config(config.get_section("updates"))
        # Installed: the user's data folder (or beside a portable copy); development: %APPDATA%\\Lumenia, never the repository.
        license_dir = writable_data_dir() if is_packaged() else user_data_dir()
        self.license = LicenseService(backend, LicenseStore(license_dir), self)
        self.license.statusChanged.connect(self._on_license_changed)
        self.diagnostics = DiagnosticsService(
            backend, logs_dir,
            AppFacts(APP_VERSION, self._preferences.channel.value, os.environ.get("LUMENIA_CRASH_DSN", CRASH_REPORT_DSN)),
            ReportConsent.parse(config.get("diagnostics", "consent", ReportConsent.ASK.value)))
        self.updates = UpdateThread(VelopackUpdater(APP_UPDATE_REPOSITORY, self._preferences.channel.value), self)
        self.updates.worker.found.connect(self._on_update_found)
        self.updates.worker.progress.connect(self._on_update_progress)
        self.updates.worker.downloaded.connect(self._on_update_downloaded)
        self.updates.worker.failed.connect(self._on_update_failed)
        self._manual_check = False
        self._pending_choice = UpdateChoice.LATER
        self._error_handler = PythonErrorHandler(self.diagnostics)

    # ── Partida e saída ───────────────────────────────────────────────────

    def start(self, previous_crash: Optional[Path]) -> None:
        status = self.license.restore()
        self._on_license_changed(status)
        if status.is_licensed:
            self._say(describe(status), 6000)
        elif not self._config.get("licensing", "welcome_shown", False):
            # After the crash question (queued just below), once the window is on screen.
            QtCore.QTimer.singleShot(0, self, self.show_welcome)
        self.diagnostics.install()
        logging.getLogger(CRASH_LOGGER).addHandler(self._error_handler)
        self.diagnostics.collect_previous_session(previous_crash)
        QtCore.QTimer.singleShot(0, self, self.review_pending_reports)
        if self._preferences.is_check_due(datetime.now()) and self.updates.updater.available:
            QtCore.QTimer.singleShot(FIRST_CHECK_DELAY_MS, self, lambda: self.check_for_updates(manual=False))

    def shutdown(self) -> None:
        logging.getLogger(CRASH_LOGGER).removeHandler(self._error_handler)
        self.updates.stop()

    # ── Licença ───────────────────────────────────────────────────────────

    def open_license_dialog(self) -> None:
        LicenseDialog(self.license, self._window).exec()

    def show_welcome(self) -> None:
        """First start without a license: explain free mode once and offer to activate."""
        self._config.set("licensing", "welcome_shown", True)
        if self.license.status.is_licensed:
            return
        dialog = WelcomeDialog(self._window)
        dialog.exec()
        if dialog.choice is WelcomeChoice.ACTIVATE:
            self.open_license_dialog()
        elif dialog.choice is WelcomeChoice.BUY:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(PURCHASE_URL))

    def _on_license_changed(self, status: LicenseStatus) -> None:
        self.freeModeChanged.emit(not status.is_licensed)

    # ── Relatórios de erro ────────────────────────────────────────────────

    @property
    def auto_send_reports(self) -> bool:
        return self.diagnostics.consent is ReportConsent.ALWAYS

    def set_auto_send_reports(self, enabled: bool) -> None:
        self.diagnostics.consent = ReportConsent.ALWAYS if enabled else ReportConsent.ASK
        self._config.set("diagnostics", "consent", self.diagnostics.consent.value)

    def review_pending_reports(self) -> None:
        for report, bundle in self.diagnostics.pending():
            if self.diagnostics.consent is ReportConsent.NEVER:
                return
            if self.diagnostics.consent is ReportConsent.ALWAYS:
                self._send(report, bundle, quiet=True)
                continue
            self._ask_about(report, bundle)

    def create_diagnostic_report(self) -> None:
        bundle = self.diagnostics.create_manual_report()
        for report, path in self.diagnostics.pending():
            if path == bundle:
                self._ask_about(report, bundle)

    def _ask_about(self, report: CrashReport, bundle: Path) -> None:
        dialog = CrashReportDialog(report, self._window)
        dialog.exec()
        if dialog.always_send:
            self.set_auto_send_reports(True)
        if dialog.choice is CrashReportChoice.SEND:
            self._send(report, bundle, quiet=False)
        elif dialog.choice is CrashReportChoice.DISCARD:
            self.diagnostics.discard(bundle)

    def _send(self, report: CrashReport, bundle: Path, quiet: bool) -> None:
        result = self.diagnostics.send(report, bundle)
        if result is SendResult.SENT:
            self._say(tr("distribution.crash.sent", "Relatório enviado. Obrigado!"), 4000)
        elif result is SendResult.NO_ENDPOINT and not quiet:
            self._hand_over_by_email(report, bundle)
        elif result is SendResult.FAILED:
            self._say(tr("distribution.crash.send_failed", "Não foi possível enviar o relatório agora; ele fica salvo."), 6000)

    def _hand_over_by_email(self, report: CrashReport, bundle: Path) -> None:
        """No crash service configured: show the zip and open an e-mail for the user to attach it."""
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(bundle.parent)))
        subject = f"[Lumenia {report.app_version}] {report.report_id}"
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(f"mailto:{SUPPORT_EMAIL}?subject={QtCore.QUrl.toPercentEncoding(subject).data().decode()}"))
        self._say(tr("distribution.crash.attach", "Anexe o arquivo {name} ao e-mail.", name=bundle.name), 10000)

    # ── Atualizações ──────────────────────────────────────────────────────

    @property
    def auto_check_updates(self) -> bool:
        return self._preferences.auto_check

    def set_auto_check_updates(self, enabled: bool) -> None:
        self._preferences = UpdatePreferences(self._preferences.channel, bool(enabled), self._preferences.last_check)
        self._config.set_section("updates", self._preferences.to_config())

    def check_for_updates(self, manual: bool = True) -> None:
        if not self.updates.updater.available:
            if manual:
                self._say(tr("distribution.update.unavailable",
                             "Esta cópia não foi instalada pelo instalador do Lumenia: atualize baixando a versão nova."), 6000)
            return
        self._manual_check = manual
        if manual:
            self._say(tr("distribution.update.checking", "Procurando atualizações..."), 3000)
        self.updates.check()

    def _remember_check(self) -> None:
        self._preferences = UpdatePreferences(self._preferences.channel, self._preferences.auto_check,
                                              datetime.now().isoformat(timespec="seconds"))
        self._config.set_section("updates", self._preferences.to_config())

    def _on_update_found(self, found: Optional[FoundUpdate]) -> None:
        self._remember_check()
        if found is None:
            if self._manual_check:
                self._say(tr("distribution.update.up_to_date", "Você já tem a versão mais recente."), 4000)
            return
        offer = UpdateOffer(found.version, found.notes_markdown)
        decision = decide(offer, self.license.status)
        dialog = UpdateDialog(offer, decision, self.updates.updater.current_version(), self._window)
        dialog.exec()
        if decision is not UpdateDecision.NOT_COVERED and dialog.choice is not UpdateChoice.LATER:
            self._pending_choice = dialog.choice
            self.updates.download(found)

    def _on_update_progress(self, percent: int) -> None:
        self._say(tr("distribution.update.downloading", "Baixando atualização: {percent}%", percent=percent), 2000)

    def _on_update_downloaded(self, found: FoundUpdate) -> None:
        if self._pending_choice is UpdateChoice.RESTART_NOW:
            self._say(tr("distribution.update.restarting", "Reiniciando para atualizar..."), 3000)
            # Closing the window asks to save open documents; Velopack swaps the folder after the exit.
            self.updates.updater.apply_on_exit(found, restart=True)
            self._window.close()
        else:
            self.updates.updater.apply_on_exit(found, restart=False)
            self._say(tr("distribution.update.on_exit_ready", "A versão {version} será instalada ao fechar o Lumenia.",
                         version=found.version), 8000)

    def _on_update_failed(self, message: str) -> None:
        if self._manual_check:
            self._say(tr("distribution.update.failed", "Não foi possível procurar atualizações: {error}", error=message), 6000)
