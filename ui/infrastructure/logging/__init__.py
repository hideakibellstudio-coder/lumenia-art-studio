"""
ui.infrastructure.logging — Módulo Canônico de Logging e Telemetria (ARCcC).
=============================================================================
Exporta setup_senior_logging, get_logger e decoradores de medição.
"""

from .logger import (
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
