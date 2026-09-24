import pytest
from PySide6 import QtCore, QtGui, QtTest, QtWidgets
from ui.core.components.menu_bar import MenuBar
from ui.core.shortcut_registry import ShortcutRegistry
from ui.core.shortcut_catalog import DEFAULT_SHORTCUTS
from ui.core.shortcut_bindings import ShortcutBindings

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])


def _destroy(window, registry):
    from tests.qt_windows import destroy_now
    registry.cleanup()
    destroy_now(window)


def test_remap_disable_and_conflict_are_atomic():
    window = QtWidgets.QMainWindow()
    menu = MenuBar(window)
    registry = ShortcutRegistry(window, menu, lambda tool: None)
    try:
        assert set(registry.targets) == {item["id"] for item in DEFAULT_SHORTCUTS}
        registry.apply({})
        registry.apply({"file_save": "Ctrl+Alt+S", "tool_brush": ""})
        assert menu.file_menu.action_save.shortcut().toString() == "Ctrl+Alt+S"
        assert registry.targets["tool_brush"].key().isEmpty()
        with pytest.raises(ValueError):
            registry.apply({"file_save": "Ctrl+O"})
        assert menu.file_menu.action_save.shortcut().toString() == "Ctrl+Alt+S"
    finally:
        registry.apply({})
        _destroy(window, registry)


def test_text_editor_and_canvas_local_commands_keep_their_context():
    window = QtWidgets.QMainWindow()
    menu = MenuBar(window)
    window.setMenuBar(menu)
    selected_tools = []
    canvas = QtWidgets.QWidget(window)
    canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
    window.setCentralWidget(canvas)
    registry = ShortcutRegistry(window, menu, selected_tools.append, canvas)
    registry.apply({})

    editor = QtWidgets.QTextEdit(canvas)
    editor.show()
    window.show()
    try:
        editor.setFocus()
        app.processEvents()
        QtTest.QTest.keyClick(editor, QtCore.Qt.Key_B)
        QtTest.QTest.keyClick(editor, QtCore.Qt.Key_S, QtCore.Qt.ControlModifier)
        app.processEvents()
        assert editor.toPlainText() == "b"
        assert selected_tools == []

        selection_actions = []
        menu.select_menu.selectAllRequested.connect(lambda: selection_actions.append("global"))
        canvas.setFocus()
        app.processEvents()
        QtTest.QTest.keyClick(canvas, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        app.processEvents()
        assert selection_actions == []

        registry.apply({"select_all": "Ctrl+Alt+A"})
        custom_event = QtGui.QKeyEvent(
            QtCore.QEvent.ShortcutOverride,
            QtCore.Qt.Key_A,
            QtCore.Qt.ControlModifier | QtCore.Qt.AltModifier,
        )
        custom_event.ignore()
        registry.eventFilter(canvas, custom_event)
        assert custom_event.isAccepted()
        assert ShortcutBindings.matches("select_all", custom_event)
    finally:
        registry.apply({})
        _destroy(window, registry)


def test_native_pressure_power_curve():
    import aladyn_engine_native as native
    curve = native.BezierCurve()
    curve.set_power(2.0)
    assert curve.sample(0.5) == pytest.approx(0.25, abs=0.005)
    curve.set_power(0.5)
    assert curve.sample(0.5) == pytest.approx(0.7071, abs=0.005)
    with pytest.raises(ValueError):
        curve.set_power(float("nan"))
