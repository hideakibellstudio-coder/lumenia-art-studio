"""One application point for menu and tool shortcuts, with collision checks."""

from PySide6 import QtCore, QtGui, QtWidgets
from .shortcut_catalog import DEFAULT_SHORTCUTS
from .shortcut_bindings import ShortcutBindings
from ui.core.components.menu_bar.menu_bar import MenuBar


class ShortcutRegistry(QtCore.QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.contexts = {item["id"]: item.get("context", "window") for item in DEFAULT_SHORTCUTS}
        menu: MenuBar = window.menu_bar
        self.targets = {}
        groups = {
            "file": (menu.file_menu, {"new": "action_new", "open": "action_open", "save": "action_save",
                "save_as": "action_save_as", "export": "action_export", "close": "action_close", "exit": "action_exit"}),
            "edit": (menu.edit_menu, {"undo": "act_undo", "redo": "act_redo", "cut": "act_cut", "copy": "act_copy",
                "paste": "act_paste", "clear_layer": "act_clear_layer"}),
            "layer": (menu.layer_menu, {"new": "act_new_layer", "group": "act_new_group", "duplicate": "act_dup",
                "delete": "act_del", "merge": "act_merge"}),
            "view": (menu.view_menu, {"zoom_in": "action_zoom_in", "zoom_out": "action_zoom_out",
                "zoom_100": "action_reset", "reset_rot": "action_reset_rot", "grid": "action_grid",
                "fullscreen": "action_fullscreen"}),
            "select": (menu.select_menu, {"all": "act_all", "deselect": "act_desel", "invert": "act_inv"}),
        }
        for prefix, (owner, names) in groups.items():
            for key, attribute in names.items():
                self.targets[f"{prefix}_{key}"] = getattr(owner, attribute)
        for key, attribute in {"brush": "b", "eraser": "e", "shapes": "u", "text": "t"}.items():
            self.targets[f"tool_{key}"] = getattr(window, f"shortcut_tool_{attribute}")
        self.targets["tool_wand"] = menu.select_menu.act_wand
        self.targets["tool_transform"] = menu.edit_menu.act_transform
        for key, tool in (("eyedropper", "eyedrop"), ("fill", "bucket")):
            shortcut = QtGui.QShortcut(window)
            shortcut.activated.connect(lambda tool=tool: window.select_tool_by_id(tool))
            self.targets[f"tool_{key}"] = shortcut

        application = QtWidgets.QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def cleanup(self) -> None:
        """Remove o eventFilter global da QApplication para prevenir ponteiros pendentes."""
        app = QtWidgets.QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except Exception:
                pass

    def validate(self, overrides):
        defaults = {item["id"]: item["default"] for item in DEFAULT_SHORTCUTS}
        effective = {key: overrides.get(key, value) for key, value in defaults.items()}
        occupied = {}
        for obj in self.window.findChildren(QtGui.QAction) + self.window.findChildren(QtGui.QShortcut):
            if obj in self.targets.values():
                continue
            sequence = obj.shortcut() if isinstance(obj, QtGui.QAction) else obj.key()
            key = sequence.toString(QtGui.QKeySequence.PortableText)
            if key:
                occupied[key] = "atalho reservado"
        for command, sequence in effective.items():
            if not isinstance(sequence, str):
                raise ValueError(f"Atalho inválido: {command}")
            key = QtGui.QKeySequence(sequence).toString(QtGui.QKeySequence.PortableText)
            if sequence and not key:
                raise ValueError(f"Atalho inválido: {command}")
            if key and key in occupied:
                raise ValueError(f"Conflito em {key}: {command} / {occupied[key]}")
            if key:
                occupied[key] = command
        return effective

    def apply(self, overrides):
        effective = self.validate(overrides)
        for command, sequence in effective.items():
            target = self.targets[command]
            key = QtGui.QKeySequence(sequence)
            if isinstance(target, QtGui.QAction):
                target.setShortcut(key)
            else:
                target.setKey(key)
        ShortcutBindings.configure(effective)

    def eventFilter(self, watched, event):
        """Protege edição textual e deixa comandos nativos chegarem ao canvas."""
        if event.type() != QtCore.QEvent.ShortcutOverride:
            return False

        focused = QtWidgets.QApplication.focusWidget()
        if not self._belongs_to_window(focused):
            return False
        if self._is_text_input(focused):
            event.accept()
            return False
        command = ShortcutBindings.command_for_event(event)
        if command and self.contexts.get(command) == "canvas" and not self._is_canvas_focus(focused):
            event.accept()
            return False
        if self._is_canvas_focus(focused) and command in {
            "tool_transform", "select_all", "select_deselect", "select_invert",
        }:
            event.accept()
        return False

    def _belongs_to_window(self, widget) -> bool:
        current = widget
        while current is not None:
            if current is self.window:
                return True
            current = current.parentWidget()
        return False

    @staticmethod
    def _is_text_input(widget) -> bool:
        text_widgets = (
            QtWidgets.QLineEdit,
            QtWidgets.QTextEdit,
            QtWidgets.QPlainTextEdit,
            QtWidgets.QAbstractSpinBox,
            QtWidgets.QKeySequenceEdit,
        )
        if isinstance(widget, text_widgets):
            return True
        return isinstance(widget, QtWidgets.QComboBox) and widget.isEditable()

    def _is_canvas_focus(self, widget) -> bool:
        canvas = getattr(self.window, "canvas_widget", None)
        return bool(canvas and (widget is canvas or canvas.isAncestorOf(widget)))
