"""Keep application preferences and recovery files out of the real user profile."""

import os
import tempfile
import gc
from pathlib import Path

import pytest

_profile = tempfile.TemporaryDirectory(prefix="lumenia-test-profile-")
_previous = os.environ.get("LUMENIA_CONFIG_PATH")
_previous_plugins = os.environ.get("LUMENIA_PLUGINS_CONFIG_PATH")
os.environ["LUMENIA_PLUGINS_CONFIG_PATH"] = str(Path(_profile.name) / "plugins_config.json")
os.environ["LUMENIA_CONFIG_PATH"] = str(Path(_profile.name) / "config.json")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OMP_NUM_THREADS", "2")


@pytest.fixture(scope="session")
def qapp():
    """QApplication única da sessão de testes.

    Fonte única do fixture: antes existiam nove cópias idênticas espalhadas
    pelos módulos e um módulo (test_tools_signal_symmetry_and_flip.py) que
    dependia do `qapp` do pytest-qt, que não está no requirements-dev.lock.
    """
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture(autouse=True, scope="module")
def _descartar_janelas_criadas_pelo_modulo():
    """Destroi as janelas de topo que um módulo de teste deixou vivas.

    Sem isto, centenas de widgets de módulos anteriores continuam existindo, e
    todo `app.setStyleSheet(...)` (troca de tema/escala) repinta todos eles:
    tests/test_theme_system.py levava ~220 s na suíte completa contra ~1,5 s
    isolado (medido em 2026-09-22). Janelas que já existiam antes do módulo
    (criadas na coleta) são preservadas -- a identidade é o ponteiro C++, não o
    wrapper Python, que o PySide pode recriar a cada chamada.
    """
    try:
        import shiboken6
        from PySide6 import QtCore, QtWidgets
    except Exception:
        yield
        return

    def _ptr(widget) -> int:
        return shiboken6.getCppPointer(widget)[0]

    app = QtWidgets.QApplication.instance()
    antes = {_ptr(w) for w in QtWidgets.QApplication.topLevelWidgets()} if app else set()
    yield
    app = QtWidgets.QApplication.instance()
    if app is None:
        return
    for widget in QtWidgets.QApplication.topLevelWidgets():
        try:
            # A MainWindow fica: o app real tem uma por processo e vários
            # singletons (PluginManager, ServiceRegistry) presumem isso.
            # Popups (QMenu, tooltips) aparecem em topLevelWidgets() mas têm dono;
            # só janelas órfãs de verdade (sem parentWidget) são descartadas.
            if widget.parentWidget() is not None:
                continue
            if _ptr(widget) in antes or any(
                c.__name__ in ("MainWindow", "QMainWindow") for c in type(widget).__mro__
            ):
                continue
            widget.hide()
            widget.deleteLater()
        except RuntimeError:
            continue
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    QtWidgets.QApplication.processEvents()


def pytest_unconfigure(config):
    # Ensure MainWindow-owned recovery stores release QLockFile before the
    # temporary profile is removed on Windows (open handles cannot be unlinked).
    # Documentos sujos fazem a MainWindow pedir confirmação no closeEvent -- um
    # diálogo modal que, em modo offscreen, trava a suíte para sempre. Os testes
    # não salvam nada: fecha os documentos direto no DocumentManager antes.
    try:
        from ui.core.document.manager import DocumentManager
        dm = DocumentManager.instance()
        for doc in list(dm.documents()):
            dm.close_document(doc.uid)
    except Exception:
        pass
    try:
        from PySide6 import QtWidgets
        # Sem QApplication (rodando só testes puros) o Qt imprime
        # "Must construct a QGuiApplication first." -- não há janela a fechar.
        if QtWidgets.QApplication.instance() is not None:
            QtWidgets.QApplication.closeAllWindows()
            QtWidgets.QApplication.processEvents()
    except Exception:
        pass
    try:
        from ui.core.document.recovery import RecoveryStore
        RecoveryStore.close_all()
    except Exception:
        pass
    gc.collect()
    if _previous is None:
        os.environ.pop("LUMENIA_CONFIG_PATH", None)
    else:
        os.environ["LUMENIA_CONFIG_PATH"] = _previous
    try:
        _profile.cleanup()
    except Exception:
        pass
    if _previous_plugins is None:
        os.environ.pop("LUMENIA_PLUGINS_CONFIG_PATH", None)
    else:
        os.environ["LUMENIA_PLUGINS_CONFIG_PATH"] = _previous_plugins
