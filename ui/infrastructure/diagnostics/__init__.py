"""Diagnóstico (técnico): pacotes de relatório em disco e envio sem SDK ao Sentry."""

from ui.infrastructure.diagnostics import report_bundle
from ui.infrastructure.diagnostics.sentry_uploader import SentryEndpoint, upload_event, upload_minidump

__all__ = ["SentryEndpoint", "report_bundle", "upload_event", "upload_minidump"]
