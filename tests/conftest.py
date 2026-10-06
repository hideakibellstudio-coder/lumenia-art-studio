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
# The offscreen platform has no OpenGL: a QOpenGLWidget there cannot create its context
# and every QPainter on it is inactive, so the canvas paint code ran as a silent no-op in
# the tests (found 2026-10-01, while checking that the viewport draws what it should).
# The raster widget is the production fallback and it really paints.
os.environ.setdefault("LUMENIA_DISABLE_OPENGL", "1")
os.environ.setdefault("OMP_NUM_THREADS", "2")


# O pytest copia o nome de cada teste em PYTEST_CURRENT_TEST, e o Windows recusa variável de ambiente acima de
# 32767 caracteres. O id automático de um parâmetro `bytes`/`str` é o conteúdo inteiro: um bloco de 80 MiB virou
# um nome de ~84 MB que só quebrava no Windows (achado 2026-10-01). Aqui quebra em qualquer sistema, na coleta.
MAX_NODEID_CHARS = 1000


def pytest_collection_modifyitems(items):
    too_long = [item.nodeid for item in items if len(item.nodeid) > MAX_NODEID_CHARS]
    if too_long:
        raise pytest.UsageError(
            f"{len(too_long)} teste(s) com nome acima de {MAX_NODEID_CHARS} caracteres; dê `ids=[...]` ao "
            f"parametrize. Primeiro: {too_long[0][:160]!r} ({len(too_long[0])} caracteres)"
        )


@pytest.fixture(scope="session")
def qapp():
    """QApplication única da sessão de testes.

    Fonte única do fixture: antes existiam nove cópias idênticas espalhadas
    pelos módulos e um módulo (test_tools_signal_symmetry_and_flip.py) que
    dependia do `qapp` do pytest-qt. Desde 2026-09-25 o pytest-qt está no
    requirements-dev (reprova exceção dentro de slot do Qt), mas o `qapp` que
    vale é este: fixture do conftest tem precedência sobre o do plugin.
    """
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture(autouse=True)
def _interface_in_portuguese():
    """Todo teste começa com a interface em pt_BR, qualquer que seja o sistema.

    Sem preferência salva, o idioma segue o sistema operacional: os testes que
    conferem texto (escritos em português) passavam no Windows do dono e
    reprovavam num sistema em inglês (o Linux do agente, um runner do CI), e
    um teste que trocava o idioma sem voltar deixava o próximo em japonês.
    Achado em 2026-09-25, ao traduzir o plugin de gravação.
    """
    from ui.infrastructure.i18n import I18nManager

    i18n = I18nManager.instance()
    if i18n.get_current_locale() != "pt_BR":
        i18n.set_locale("pt_BR", is_auto=False)
    yield


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

    from tests.qt_windows import top_level_widgets

    with top_level_widgets() as widgets:
        antes = {_ptr(w) for w in widgets}
    yield
    if QtWidgets.QApplication.instance() is None:
        return
    with top_level_widgets() as widgets:
        _descartar_orfas(widgets, antes, _ptr)
        # Ainda com o GC desligado: as órfãs morrem em C++ antes de qualquer
        # coleta dos wrappers (ver tests/qt_windows.py).
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    QtWidgets.QApplication.processEvents()


def _descartar_orfas(widgets, antes, _ptr):
    for widget in widgets:
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
