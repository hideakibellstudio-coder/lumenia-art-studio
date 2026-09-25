"""CanvasKeyRouter — teclado do canvas: espaço (mão), Delete, atalhos de seleção
e Enter/Esc/setas na transformação.

Separado de `input_router.py` em 2026-09-25, quando o roteador de ponteiro e
teclado chegou à parede dos 450 linhas; cada um tem o seu contrato com o canvas.
"""

from typing import Any, Protocol, runtime_checkable
from PySide6 import QtCore, QtGui


@runtime_checkable
class KeyCanvas(Protocol):
    """O que o teclado usa do canvas. Membro novo usado aqui entra neste contrato;
    `tests/test_canvas_contracts.py` confere que o `RenderWidget` o cumpre."""
    drawing: bool
    is_panning: bool
    is_space_held: bool
    active_text_editor: Any
    cursor_ctrl: Any
    selection_ctrl: Any
    transform_ctrl: Any
    strokeStarted: Any
    strokeFinished: Any

    def start_transform_mode(self) -> bool: ...
    def commit_transform(self) -> Any: ...
    def cancel_transform(self) -> Any: ...
    def setCursor(self, cursor: Any) -> None: ...
    def update(self) -> None: ...


class CanvasKeyRouter:
    """Roteador dos eventos de teclado do canvas."""

    def __init__(self, widget: KeyCanvas):
        self.widget = widget

    def handle_key_press(self, event: QtGui.QKeyEvent) -> bool:
        """Devolve se a tecla foi consumida. Ordem: teclas da transformação ativa,
        atalhos (transformar, desmarcar, inverter, selecionar tudo), espaço,
        Delete/Backspace. Dividido em passos em 2026-09-25 (complexidade 24)."""
        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if self.widget.transform_ctrl.active and self._transform_key(event):
            return True
        if self._shortcut(event, backend):
            return True
        if event.key() == QtCore.Qt.Key_Space:
            return self._space_pressed(event)
        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            return self._delete_selection(backend)
        return False

    _NUDGE = {
        QtCore.Qt.Key_Left: (-1.0, 0.0), QtCore.Qt.Key_Right: (1.0, 0.0),
        QtCore.Qt.Key_Up: (0.0, -1.0), QtCore.Qt.Key_Down: (0.0, 1.0),
    }

    def _transform_key(self, event: QtGui.QKeyEvent) -> bool:
        w = self.widget
        key = event.key()
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            w.commit_transform()
            return True
        if key == QtCore.Qt.Key_Escape:
            w.cancel_transform()
            return True
        if key in self._NUDGE:
            step = 10.0 if (event.modifiers() & QtCore.Qt.ShiftModifier) else 1.0
            dx, dy = self._NUDGE[key]
            w.transform_ctrl.dx += dx * step
            w.transform_ctrl.dy += dy * step
            w.update()
            return True
        return False

    def _shortcut(self, event: QtGui.QKeyEvent, backend: Any) -> bool:
        from ui.core.shortcut_bindings import ShortcutBindings
        w = self.widget
        if ShortcutBindings.matches("tool_transform", event):
            w.start_transform_mode()
            return True
        if not backend:
            return False
        timer = w.selection_ctrl.selection_timer
        if ShortcutBindings.matches("select_deselect", event):
            backend.clear_selection()
            timer.stop()
        elif ShortcutBindings.matches("select_invert", event):
            backend.invert_selection()
            if backend.has_selection():
                timer.start()
        elif ShortcutBindings.matches("select_all", event):
            backend.select_all()
            timer.start()
        else:
            return False
        w.update()
        return True

    def _space_pressed(self, event: QtGui.QKeyEvent) -> bool:
        """Espaço: mão para navegar (a não ser que o editor de texto esteja aberto)."""
        w = self.widget
        if w.active_text_editor and w.active_text_editor.isVisible():
            return False
        if event.isAutoRepeat():
            return True
        w.is_space_held = True
        if not w.is_panning and not w.drawing:
            w.setCursor(QtCore.Qt.OpenHandCursor)
            w.update()
        return True

    def _delete_selection(self, backend: Any) -> bool:
        w = self.widget
        if not (backend and backend.has_selection()):
            return False
        w.strokeStarted.emit()
        try:
            if backend.delete_selection_on_active_layer():
                w.update()
        finally:
            w.strokeFinished.emit()
        return True

    def handle_key_release(self, event: QtGui.QKeyEvent) -> bool:
        """Chamado quando uma tecla é liberada na viewport."""
        w: KeyCanvas = self.widget
        if event.key() == QtCore.Qt.Key_Space:
            if event.isAutoRepeat():
                return True
            w.is_space_held = False
            if not w.is_panning:
                w.cursor_ctrl.restore_tool_cursor()
                w.update()
            return True
        return False

    def handle_focus_out(self) -> None:
        """Chamado na perda de foco para evitar estados presos de teclas modificadoras."""
        w: KeyCanvas = self.widget
        if w.is_space_held:
            w.is_space_held = False
            if not w.is_panning:
                w.cursor_ctrl.restore_tool_cursor()
                w.update()
