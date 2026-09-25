"""
Senior Enterprise Logging Infrastructure (Lumenia V2) — ARCcC Infrastructure.
==============================================================================
Sistema de logging avançado para diagnóstico em tempo real, depuração em terminal ANSI,
captura de exceções globais (sys.excepthook) e integração com Qt Message Handler.
"""

from __future__ import annotations

import sys
import time
import functools
import logging
from logging.handlers import RotatingFileHandler
from PySide6 import QtCore
from ui.infrastructure.runtime_paths import writable_data_dir
from ui.infrastructure.logging.crash_log import enable_native_crash_log


# ── ANSI COLORS PARA TERMINAL ───────────────────────────────────────────────

class ANSI:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Níveis
    DEBUG = "\033[36m"          # Ciano
    INFO = "\033[32m"           # Verde
    WARNING = "\033[33m"        # Amarelo
    ERROR = "\033[31m"          # Vermelho
    CRITICAL = "\033[1;37;41m"  # Fundo Vermelho / Texto Branco

    # Subsistemas
    TAG_MODULE = "\033[1;35m"   # Magenta
    TIMESTAMP = "\033[90m"     # Cinza escuro
    LOCATION = "\033[34m"      # Azul


# ── FORMATADOR COLORIDO PARA O TERMINAL ──────────────────────────────────────

class SeniorConsoleFormatter(logging.Formatter):
    """Formatador de console com cores ANSI e metadados estruturados."""

    def format(self, record: logging.LogRecord) -> str:
        level_color = getattr(ANSI, record.levelname, ANSI.RESET)
        level_badge = f"{level_color}[{record.levelname:<8}]{ANSI.RESET}"

        created_dt = self.formatTime(record, "%H:%M:%S")
        msecs = int(record.msecs)
        time_str = f"{ANSI.TIMESTAMP}[{created_dt}.{msecs:03d}]{ANSI.RESET}"

        logger_name = record.name
        if logger_name.startswith("Lumenia."):
            tag_name = logger_name.replace("Lumenia.", "")
        else:
            tag_name = logger_name
        module_tag = f"{ANSI.TAG_MODULE}[{tag_name}]{ANSI.RESET}"

        file_line = f"{ANSI.LOCATION}({record.filename}:{record.lineno}){ANSI.RESET}"
        message = record.getMessage()

        formatted = f"{time_str} {level_badge} {module_tag} {file_line} - {message}"

        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            formatted += f"\n{ANSI.ERROR}{exc_text}{ANSI.RESET}"

        return formatted


# ── FORMATADOR LIMPO PARA ARQUIVO LOG ────────────────────────────────────────

class SeniorFileFormatter(logging.Formatter):
    """Formatador de arquivo de log em formato estruturado sem ANSI."""

    def format(self, record: logging.LogRecord) -> str:
        created_dt = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        msecs = int(record.msecs)
        time_str = f"[{created_dt}.{msecs:03d}]"

        formatted = f"{time_str} [{record.levelname:<8}] [{record.name}] ({record.filename}:{record.lineno}) - {record.getMessage()}"
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        return formatted


# ── DECORADOR PARA MEDIÇÃO DE PERFORMANCE ────────────────────────────────────

def log_execution_time(logger: logging.Logger | None = None):
    """Decorador para medir o tempo exato de execução de funções críticas em ms."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = logging.getLogger(f"Lumenia.Perf.{func.__module__}")
            start_t = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            logger.debug(f"⚡ Execution time of '{func.__name__}': {elapsed_ms:.2f} ms")
            return result

        return wrapper

    return decorator


# ── CONFIGURAÇÃO GLOBAL E INICIALIZAÇÃO ──────────────────────────────────────

def get_logger(subsystem: str) -> logging.Logger:
    """Retorna um logger dentro do namespace 'Lumenia.<subsystem>'."""
    if not subsystem.startswith("Lumenia"):
        name = f"Lumenia.{subsystem}"
    else:
        name = subsystem
    return logging.getLogger(name)


def _global_exception_hook(exctype, value, traceback_obj):
    """Captura exceções globais não tratadas no sistema e registra com stacktrace completo."""
    logger = get_logger("System.Crash")
    logger.critical(
        "🚨 UNHANDLED EXCEPTION CAUGHT BY SENIOR LOGGING HOOK:",
        exc_info=(exctype, value, traceback_obj),
    )


def _qt_message_handler(mode, context, message):
    """Redireciona avisos internos da biblioteca PySide6 / Qt para o Logger."""
    qt_logger = get_logger("QtInternal")
    if mode == QtCore.QtMsgType.QtDebugMsg:
        qt_logger.debug(f"Qt: {message}")
    elif mode == QtCore.QtMsgType.QtInfoMsg:
        qt_logger.info(f"Qt: {message}")
    elif mode == QtCore.QtMsgType.QtWarningMsg:
        qt_logger.warning(f"Qt: {message} ({context.file}:{context.line})")
    elif mode == QtCore.QtMsgType.QtCriticalMsg:
        qt_logger.error(f"Qt: {message} ({context.file}:{context.line})")
    elif mode == QtCore.QtMsgType.QtFatalMsg:
        qt_logger.critical(f"Qt FATAL: {message} ({context.file}:{context.line})")


def setup_senior_logging(log_level: int = logging.DEBUG) -> None:
    """
    Inicializa o sistema completo de logging sênior da aplicação Lumenia V2.
    - Console Stream com ANSI Colors.
    - Arquivo com Rotação (5MB / 5 backups em logs/lumenia_latest.log).
    - Exception Hook Global.
    - Qt Message Handler.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            h_stdout = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode)):
                kernel32.SetConsoleMode(h_stdout, mode.value | 0x0004)
        except (AttributeError, OSError):
            pass  # sem console do Windows (serviço, redirecionamento): cores ANSI ficam de fora

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    # 1. Console Stream Handler
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass  # fluxo já em uso ou não reconfigurável
    if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass  # fluxo já em uso ou não reconfigurável
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(SeniorConsoleFormatter())
    root_logger.addHandler(console_handler)

    # 2. Rotating File Handler
    logs_dir = None
    try:
        logs_dir = writable_data_dir() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_file_path = str(logs_dir / "lumenia_latest.log")
        file_handler = RotatingFileHandler(
            log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(SeniorFileFormatter())
        root_logger.addHandler(file_handler)
    except Exception as e:
        sys.stderr.write(f"Aviso: Não foi possível criar o arquivo de log: {e}\n")

    # 3. Interceptadores Globais
    sys.excepthook = _global_exception_hook
    QtCore.qInstallMessageHandler(_qt_message_handler)

    logger = get_logger("Bootstrap")
    logger.info("🚀 Senior Logging System initialized successfully (Console ANSI + File Rotating).")

    # 4. Quedas nativas (motor C++, Qt), que o excepthook não vê
    if logs_dir is not None:
        try:
            previous_crash = enable_native_crash_log(logs_dir)
        except OSError as exc:
            logger.warning("Registro de quedas nativas indisponível: %s", exc)
        else:
            if previous_crash is not None:
                logger.warning("A sessão anterior terminou com uma queda nativa; pilha em %s", previous_crash)
