"""Fechar um documento libera o documento e os widgets da aba.

Achado em 2026-09-22 pelo gate de sessão longa (scripts/soak_full_session.py):
cada abrir/fechar de documento vazava ~89 KB. Duas causas:
  1. Document conectava lambdas (que capturavam `self`) em sinais do próprio
     LocalLayerManager -- ciclo guardado no lado C++ que o gc não enxerga;
  2. QTabBar.removeTab não destrói o botão de fechar da aba.
"""

from __future__ import annotations

import gc

from PySide6 import QtCore, QtWidgets

from tests.main_window_fixture import main_window_com_workspace
from ui.core.document.document import Document
from ui.core.document.manager import DocumentManager

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])


def _contar(cls_nome: str) -> int:
    return sum(1 for o in gc.get_objects() if type(o).__name__ == cls_nome)


def _abrir_e_fechar(dm: DocumentManager, base_uid: str, n: int) -> None:
    for i in range(n):
        doc = dm.new_document(320, 240, f"vazamento {i}")
        app.processEvents()
        dm.set_active_document(base_uid)
        dm.close_document(doc.uid)
        app.processEvents()
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


def test_documentos_e_botoes_de_aba_nao_se_acumulam():
    main_window_com_workspace()
    dm = DocumentManager.instance()
    base = dm.new_document(320, 240, "base vazamento")
    app.processEvents()
    try:
        _abrir_e_fechar(dm, base.uid, 3)
        gc.collect()
        docs_antes = sum(1 for o in gc.get_objects() if isinstance(o, Document))
        botoes_antes = _contar("TabCloseButton")

        _abrir_e_fechar(dm, base.uid, 20)
        gc.collect()

        assert sum(1 for o in gc.get_objects() if isinstance(o, Document)) <= docs_antes
        assert _contar("TabCloseButton") <= botoes_antes
    finally:
        dm.close_document(base.uid)
