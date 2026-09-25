"""Registro de quedas nativas (motor C++, Qt) que o `sys.excepthook` não vê.

Um acesso inválido no motor derruba o processo sem exceção Python: até
2026-09-25 isso fechava o app sem uma linha no log. O `faulthandler` grava a
pilha Python de todas as threads em `native_crash.log` no momento da queda.
Na abertura seguinte, o arquivo não vazio é guardado com data e hora (os
últimos `KEEP` ficam) e o log principal avisa que a sessão anterior caiu.
"""

from __future__ import annotations

import faulthandler
import time
from pathlib import Path
from typing import TextIO

CRASH_FILE = "native_crash.log"
KEEP = 5

_stream: TextIO | None = None


def _archive_previous_crash(logs_dir: Path) -> Path | None:
    current = logs_dir / CRASH_FILE
    if not current.is_file() or current.stat().st_size == 0:
        return None
    archived = logs_dir / f"native_crash-{time.strftime('%Y%m%d-%H%M%S', time.localtime(current.stat().st_mtime))}.log"
    current.replace(archived)
    for old in sorted(logs_dir.glob("native_crash-*.log"))[:-KEEP]:
        old.unlink()
    return archived


def enable_native_crash_log(logs_dir: Path) -> Path | None:
    """Liga o faulthandler em `logs_dir`; devolve o registro da queda anterior, se houve."""
    global _stream
    previous = _archive_previous_crash(logs_dir)
    if _stream is not None:
        _stream.close()
    # Fica aberto a sessão toda: o faulthandler escreve no descritor na hora da queda.
    _stream = (logs_dir / CRASH_FILE).open("w", encoding="utf-8")
    faulthandler.enable(file=_stream, all_threads=True)
    return previous
