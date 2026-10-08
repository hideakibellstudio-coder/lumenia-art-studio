"""Diagnóstico: o que um relatório de queda contém, quando ele sai da máquina e o serviço que o conduz."""

from ui.core.diagnostics.crash_report import CrashKind, CrashReport
from ui.core.diagnostics.report_privacy import ReportConsent, scrub
from ui.core.diagnostics.diagnostics_service import AppFacts, DiagnosticsService, PythonErrorHandler, SendResult

__all__ = ["AppFacts", "CrashKind", "CrashReport", "DiagnosticsService", "PythonErrorHandler", "ReportConsent",
           "SendResult", "scrub"]
