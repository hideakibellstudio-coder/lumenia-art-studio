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
        w: KeyCanvas = self.widget
        modifiers = event.modifiers()
        from ui.core.engine.registry import EngineRegistry
        from ui.core.shortcut_bindings import ShortcutBindings
        backend = EngineRegistry.instance().get_backend()

        if w.transform_ctrl.active:
            if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                w.commit_transform()
                return True
            elif event.key() == QtCore.Qt.Key_Escape:
                w.cancel_transform()
                return True
            elif event.key() in (QtCore.Qt.Key_Left, QtCore.Qt.Key_Right, QtCore.Qt.Key_Up, QtCore.Qt.Key_Down):
                step = 10.0 if (modifiers & QtCore.Qt.ShiftModifier) else 1.0
                if event.key() == QtCore.Qt.Key_Left:
                    w.transform_ctrl.dx -= step
                elif event.key() == QtCore.Qt.Key_Right:
                    w.transform_ctrl.dx += step
                elif event.key() == QtCore.Qt.Key_Up:
                    w.transform_ctrl.dy -= step
                elif event.key() == QtCore.Qt.Key_Down:
                    w.transform_ctrl.dy += step
                w.update()
                return True

        if ShortcutBindings.matches("tool_transform", event):
            w.start_transform_mode()
            return True
        if ShortcutBindings.matches("select_deselect", event):
            if backend:
                backend.clear_selection()
                w.selection_ctrl.selection_timer.stop()
                w.update()
                return True
        if ShortcutBindings.matches("select_invert", event):
            if backend:
                backend.invert_selection()
                if backend.has_selection():
                    w.selection_ctrl.selection_timer.start()
                w.update()
                return True
        if ShortcutBindings.matches("select_all", event):
            if backend:
                backend.select_all()
                w.selection_ctrl.selection_timer.start()
                w.update()
                return True

        # ── Barra de Espaço: Ativa navegação de câmera (Mão Livre / Pan) ──
        if event.key() == QtCore.Qt.Key_Space:
            if w.active_text_editor and w.active_text_editor.isVisible():
                return False
            if event.isAutoRepeat():
                return True
            w.is_space_held = True
            if not w.is_panning and not w.drawing:
                w.setCursor(QtCore.Qt.OpenHandCursor)
                w.update()
            return True

        if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
            if backend and backend.has_selection():
                w.strokeStarted.emit()
                try:
                    if backend.delete_selection_on_active_layer():
                        w.update()
                finally:
                    w.strokeFinished.emit()
                return True
        return False

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
