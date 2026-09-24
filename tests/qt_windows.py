"""Enumeração segura das janelas de topo do Qt nos testes.

`QApplication.topLevelWidgets()` cria um wrapper Python para cada janela. Se
o coletor de lixo do Python rodar nesse momento (a própria alocação do wrapper
pode dispará-lo) e coletar o wrapper antigo de uma janela sem pai presa num
ciclo de referências, ele apaga a janela em C++ no meio da criação do wrapper
novo: segfault ou abort dentro do PySide, em ponto aleatório da suíte.

Achado em 2026-09-24 com gdb + valgrind ("Invalid free" em
PySide::getWrapperForQObject; bloco liberado pelo dealloc do shiboken a
partir de SbkObject_tp_new -> _PyObject_GC_NewVar). Reprodução mínima: criar
três `NewDocumentDialog()` sem pai, soltar as referências e chamar
`gc.collect()` -- derruba o interpretador (PySide6 6.11.1). Uma mudança sem
relação (tirar um QPixmap do LocalLayer) mudou o momento do GC automático e
fez a limpeza entre módulos cair em 4 de 6 execuções de um subconjunto.

Regra: com o GC DESLIGADO, enumerar as janelas E apagá-las em C++
(`deleteLater` + `sendPostedEvents(DeferredDelete)`). Depois disso os
wrappers ficam inválidos e coletá-los é inofensivo. Nunca chamar
`gc.collect()` antes: é a coleta com o C++ ainda vivo que derruba.
"""
from __future__ import annotations

import contextlib
import gc
from collections.abc import Iterator


@contextlib.contextmanager
def top_level_widgets() -> Iterator[list]:
    """Janelas de topo com o GC desligado até o fim do bloco `with`."""
    from PySide6.QtWidgets import QApplication

    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield list(QApplication.topLevelWidgets()) if QApplication.instance() else []
    finally:
        if was_enabled:
            gc.enable()


def destroy_now(*widgets) -> None:
    """Apaga janelas sem pai em C++ agora, com o GC desligado.

    Para testes que criam uma janela própria (`QMainWindow()` sem pai): deixar
    o wrapper para o coletor reabre o risco descrito no topo deste módulo.
    """
    from PySide6.QtCore import QCoreApplication, QEvent

    was_enabled = gc.isenabled()
    gc.disable()
    try:
        for widget in widgets:
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    finally:
        if was_enabled:
            gc.enable()
