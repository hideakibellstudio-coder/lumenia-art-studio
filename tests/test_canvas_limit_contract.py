"""One canvas limit, declared by the engine and asked by everyone else (S0.2, D13).

Until 2026-10-01 the limit had no owner: New Document offered up to 16384 px
per side, Canvas Size offered up to 32000, `change_geometry` refused above 2 GB
of payload, opening an image was refused by Qt above 256 MB with a message that
blamed the file, and the engine itself computed `width * height * 4` in `int`
before widening it: 32000 x 32000 overflowed (undefined behaviour) instead of
being refused.

Now the engine declares `PaintEngineFacade.max_canvas_dimension()` (16384: a
full layer is 1 GiB and every pixel index still fits in 32 bits), refuses a
canvas outside it with ValueError before allocating anything, and the dialogs
and actions ask for it.
"""

from __future__ import annotations

import os

import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="native module not built in this environment"
)

from ui.core.engine.backend import SHELL_MODE_MAX_CANVAS_DIMENSION  # noqa: E402
from ui.core.engine.limits import max_canvas_dimension  # noqa: E402

LIMIT = native.PaintEngineFacade.max_canvas_dimension()


def test_the_shell_mode_fallback_is_the_engine_limit():
    """The Python constant only serves while no engine is registered; the engine wins."""
    assert SHELL_MODE_MAX_CANVAS_DIMENSION == LIMIT


@pytest.mark.parametrize(
    "width,height",
    [(LIMIT + 1, 100), (100, LIMIT + 1), (0, 100), (100, -5), (32000, 32000)],
    ids=["too_wide", "too_tall", "zero_width", "negative_height", "the_old_dialog_maximum"],
)
def test_the_engine_refuses_a_canvas_outside_the_limit_before_allocating(width, height):
    with pytest.raises(ValueError):
        native.PaintEngineFacade(width, height)


def test_a_canvas_inside_the_limit_is_created():
    engine = native.PaintEngineFacade(64, 48)
    assert (engine.get_width(), engine.get_height()) == (64, 48)


def test_resizing_beyond_the_limit_is_refused_and_keeps_the_canvas():
    engine = native.PaintEngineFacade(64, 48)
    with pytest.raises(ValueError):
        engine.resize_canvas(LIMIT + 1, 10)
    assert (engine.get_width(), engine.get_height()) == (64, 48)


def test_the_backend_answers_with_the_engine_limit():
    from ui.infrastructure.bridge_client.aladyn import AladynBackend

    assert AladynBackend().max_canvas_dimension() == LIMIT


def test_the_new_document_dialog_offers_exactly_the_engine_limit(qapp):
    from ui.core.screens.new_document_dialog import NewDocumentDialog

    dialog = NewDocumentDialog()
    assert (dialog.spn_width.maximum(), dialog.spn_height.maximum()) == (max_canvas_dimension(),) * 2


def test_the_canvas_size_dialog_offers_exactly_the_engine_limit(qapp):
    from ui.core.dialogs.canvas_size_dialog import CanvasSizeDialog

    dialog = CanvasSizeDialog(current_w=800, current_h=600)
    assert (dialog.width_spin.maximum(), dialog.height_spin.maximum()) == (max_canvas_dimension(),) * 2


def test_change_geometry_names_the_limit_when_it_is_exceeded():
    from ui.core.document.geometry import change_geometry

    class Backend:
        available = True

        def max_canvas_dimension(self):
            return 100

    with pytest.raises(ValueError, match="100"):
        change_geometry(object(), Backend(), 101, 50)


@pytest.fixture()
def window(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("LUMENIA_CONFIG_PATH", os.fspath(tmp_path / "config.json"))
    from tests.main_window_fixture import main_window_com_workspace

    win = main_window_com_workspace()
    already_open = {doc.uid for doc in win.dm.documents()}
    yield win
    for doc in list(win.dm.documents()):
        if doc.uid not in already_open:
            win.dm.close_document(doc.uid)


def _save_png(tmp_path, width, height):
    from PySide6 import QtGui

    image = QtGui.QImage(width, height, QtGui.QImage.Format_RGBA8888)
    image.fill(QtGui.QColor(30, 120, 200))
    path = tmp_path / f"{width}x{height}.png"
    assert image.save(os.fspath(path))
    return os.fspath(path)


def test_an_image_over_the_limit_is_refused_with_the_limit_in_the_message(window, tmp_path):
    documents_before = [doc.uid for doc in window.dm.documents()]
    window.documents.open_image(_save_png(tmp_path, LIMIT + 1, 1))
    assert [doc.uid for doc in window.dm.documents()] == documents_before
    message = window.status_bar.currentMessage()
    assert str(LIMIT) in message and "não foi possível ler" not in message.lower()


def test_an_image_inside_the_limit_still_opens(window, tmp_path):
    window.documents.open_image(_save_png(tmp_path, 300, 200))
    document = window.dm.active_document()
    assert (document.width, document.height) == (300, 200)
