"""
ui.core.logger — Shim de Retrocompatibilidade para ui.infrastructure.logging (ARCcC).
======================================================================================
Reexporta todas as APIs de logging para manter compatibilidade absoluta de imports.
"""

from ui.infrastructure.logging import (
    setup_senior_logging,
    get_logger,
    log_execution_time,
    ANSI,
    SeniorConsoleFormatter,
    SeniorFileFormatter,
)

__all__ = [
    "setup_senior_logging",
    "get_logger",
    "log_execution_time",
    "ANSI",
    "SeniorConsoleFormatter",
    "SeniorFileFormatter",
]
