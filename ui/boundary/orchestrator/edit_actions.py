"""EditActions — área de transferência, preenchimento e seleção (menus Editar e Seleção).

Colaborador da `MainWindow` (ver `shell_actions.py`). Edição de pixels vinda
do menu roda por `canvas.run_as_stroke(...)`: para o resto do programa ela é
um traço (documento sujo, miniaturas, desfazer).
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtGui, QtWidgets

from ui.core.dialogs.modify_selection_dialog import ModifySelectionDialog
from ui.core.document.layer_commands import LayerCommands
from ui.core.i18n import tr
from ui.core.state import BrushState

from .shell_actions import BackendProvider, ShellActions, backend_ready
from .workspace_port import ShellCanvas


class EditActions(ShellActions):
    def __init__(
        self,
        window: QtWidgets.QWidget,
        backend: BackendProvider,
        brush: BrushState,
        canvas: Optional[ShellCanvas],
        layers: LayerCommands,
    ) -> None:
        super().__init__(window)
        self._window = window
        self._backend = backend
        self._brush = brush
        self._canvas = canvas
        self._layers = layers

    def _as_stroke(self, action: Callable[[], object]) -> object:
        if self._canvas is None:
            return action()
        return self._canvas.run_as_stroke(action)

    # ── Área de transferência ─────────────────────────────────────────────

    def copy(self) -> None:
        backend = self._backend()
        if not backend:
            return
        image = backend.get_qimage()
        if image and not image.isNull():
            QtWidgets.QApplication.clipboard().setImage(image)
            self._say("Camada / Imagem copiada para a Área de Transferência.", 2500)

    def cut(self) -> None:
        self.copy()
        backend = self._backend()
        if backend and backend.has_selection():
            self._as_stroke(backend.delete_selection_on_active_layer)
        else:
            self._layers.clear_active_pixels()
        self._say("Cortado para a Área de Transferência.", 2500)

    def paste(self) -> None:
        image = QtWidgets.QApplication.clipboard().image()
        if image.isNull():
            self._say("Nenhuma imagem encontrada na Área de Transferência.", 2000)
            return
        backend = self._backend()
        if not backend_ready(backend):
            self._say("Motor indisponível: não há onde colar a imagem.", 2500)
            return
        rgba = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
        w, h = rgba.width(), rgba.height()
        raw_bytes = bytes(rgba.constBits()[: w * h * 4])
        self._as_stroke(lambda: backend.paste_rgba_buffer_on_active_layer(0, 0, w, h, raw_bytes))
        self._say(f"Imagem ({w}×{h}) colada na camada ativa.", 2500)

    def fill(self) -> None:
        backend = self._backend()
        if not backend:
            return
        # Editar → Preencher usa a cor ativa do usuário (fonte única: BrushState).
        color = self._brush.color

        def _fill() -> None:
            if backend.has_selection():
                backend.fill_selection_on_active_layer(color)
            else:
                backend.fill_area(0, 0, color, tolerance=255, contiguous=False)

        self._as_stroke(_fill)
        self._say("Preenchimento aplicado.", 2000)

    # ── Seleção ───────────────────────────────────────────────────────────

    def select_all(self) -> None:
        if self._canvas is not None:
            self._canvas.select_all()
        elif self._backend():
            self._backend().select_all()
        self._say("Tudo selecionado.", 2000)

    def invert_selection(self) -> None:
        if self._canvas is not None:
            self._canvas.invert_selection()
        elif self._backend():
            self._backend().invert_selection()
        self._say("Seleção invertida.", 2000)

    def deselect(self) -> None:
        if self._canvas is None:
            return
        self._canvas.clear_selection()
        self._say("Seleção desmarcada.", 2000)

    def modify_selection(self, mode: str) -> None:
        backend = self._backend()
        if not backend or not backend.has_selection() or self._canvas is None:
            self._say(tr("status.no_selection_to_modify", "Não há seleção para modificar."), 2500)
            return
        dialog = ModifySelectionDialog(mode=mode, parent=self._window)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        px = dialog.get_pixels()
        if self._canvas.modify_selection(mode, px):
            self._say(tr("status.selection_modified", "Seleção modificada ({px} px).").format(px=px), 2000)
        else:
            self._say(tr("status.selection_modify_failed", "Não foi possível modificar a seleção."), 2500)
