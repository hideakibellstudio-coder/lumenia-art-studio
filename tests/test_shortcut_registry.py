import pytest
from PySide6 import QtCore, QtGui, QtTest, QtWidgets
from ui.core.components.menu_bar import MenuBar
from ui.core.shortcut_registry import ShortcutRegistry
from ui.core.shortcut_catalog import DEFAULT_SHORTCUTS
from ui.core.shortcut_bindings import ShortcutBindings

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["--platform", "offscreen"])


def test_remap_disable_and_conflict_are_atomic():
    window = QtWidgets.QMainWindow()
    window.menu_bar = MenuBar(window)
    window.select_tool_by_id = lambda tool: None
    for suffix in ("b", "e", "u", "t"):
        setattr(window, f"shortcut_tool_{suffix}", QtGui.QShortcut(window))
    registry = ShortcutRegistry(window)
    try:
        assert set(registry.targets) == {item["id"] for item in DEFAULT_SHORTCUTS}
        registry.apply({})
        registry.apply({"file_save": "Ctrl+Alt+S", "tool_brush": ""})
        assert window.menu_bar.file_menu.action_save.shortcut().toString() == "Ctrl+Alt+S"
        assert window.shortcut_tool_b.key().isEmpty()
        with pytest.raises(ValueError):
            registry.apply({"file_save": "Ctrl+O"})
        assert window.menu_bar.file_menu.action_save.shortcut().toString() == "Ctrl+Alt+S"
    finally:
        registry.apply({})
        window.close()


def test_text_editor_and_canvas_local_commands_keep_their_context():
    window = QtWidgets.QMainWindow()
    window.menu_bar = MenuBar(window)
    selected_tools = []
    window.select_tool_by_id = selected_tools.append
    canvas = QtWidgets.QWidget(window)
    canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
    window.canvas_widget = canvas
    window.setCentralWidget(canvas)
    for suffix in ("b", "e", "u", "t"):
        setattr(window, f"shortcut_tool_{suffix}", QtGui.QShortcut(window))
    registry = ShortcutRegistry(window)
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
        window.menu_bar.select_menu.selectAllRequested.connect(lambda: selection_actions.append("global"))
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
        window.close()


def test_native_pressure_power_curve():
    import aladyn_engine_native as native
    curve = native.BezierCurve()
    curve.set_power(2.0)
    assert curve.sample(0.5) == pytest.approx(0.25, abs=0.005)
    curve.set_power(0.5)
    assert curve.sample(0.5) == pytest.approx(0.7071, abs=0.005)
    with pytest.raises(ValueError):
        curve.set_power(float("nan"))


def test_backend_dispatch_changes_native_brush_state():
    from ui.engine_backends.aladyn import AladynBackend
    from ui.core.engine.commands import SetBrushOpacityCommand
    backend = AladynBackend()
    backend.dispatch(SetBrushOpacityCommand(0.37))
    assert backend.get_brush_profile_dict()["opacity"] == pytest.approx(0.37)
    with pytest.raises(TypeError):
        backend.dispatch(object())
