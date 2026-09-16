"""MainWindowMenuActionsMixin — Handlers de Ações da MenuBar para MainWindow."""

from __future__ import annotations
import os
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.registry import EngineRegistry
from ui.core.dialogs.modify_selection_dialog import ModifySelectionDialog
from ui.core.dialogs.layer_properties_dialog import LayerPropertiesDialog
from .main_window_dialog_actions import MainWindowDialogActionsMixin
from .main_window_document_actions import MainWindowDocumentActionsMixin


from ui.core.document.history import layer_transaction

from .main_window_image_actions import MainWindowImageActionsMixin

class MainWindowMenuActionsMixin(
    MainWindowDocumentActionsMixin,
    MainWindowDialogActionsMixin,
    MainWindowImageActionsMixin
):
    """Mixin com todos os manipuladores de ações da MenuBar do Lumenia."""

    # ── 1. Área de Transferência (Clipboard) ──────────────────────────────

    def copy_selection_or_layer_to_clipboard(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return
        qimg = backend.get_qimage()
        if qimg and not qimg.isNull():
            QtWidgets.QApplication.clipboard().setImage(qimg)
            self.status_bar.showMessage("Camada / Imagem copiada para a Área de Transferência.", 2500)

    def cut_selection_or_layer_to_clipboard(self) -> None:
        self.copy_selection_or_layer_to_clipboard()
        backend = EngineRegistry.instance().get_backend()
        if backend and backend.has_selection():
            if True:
                backend.delete_selection_on_active_layer()
        else:
            self.clear_screen()
        if self.workspace:
            self.workspace.canvas_widget.update()
        self.status_bar.showMessage("Cortado para a Área de Transferência.", 2500)

    def paste_clipboard(self) -> None:
        clipboard = QtWidgets.QApplication.clipboard()
        qimg = clipboard.image()
        if not qimg.isNull():
            qimg_rgba = qimg.convertToFormat(QtGui.QImage.Format_RGBA8888)
            w, h = qimg_rgba.width(), qimg_rgba.height()
            raw_bytes = bytes(qimg_rgba.constBits()[:w * h * 4])

            backend = EngineRegistry.instance().get_backend()
            if backend and getattr(backend, "available", False):
                backend.paste_rgba_buffer_on_active_layer(0, 0, w, h, raw_bytes)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage(f"Imagem ({w}×{h}) colada na camada ativa.", 2500)
            else:
                doc = self.dm.new_document(width=w, height=h, name="Colado")
                self.status_bar.showMessage(f"Imagem ({w}×{h}) colada em novo documento.", 2500)
        else:
            self.status_bar.showMessage("Nenhuma imagem encontrada na Área de Transferência.", 2000)

    def fill_active_selection_or_canvas(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend:
            return
        color = getattr(self.workspace, "_saved_color", QtGui.QColor("#000000")) if self.workspace else QtGui.QColor("#000000")
        if backend and backend.has_selection():
            if True:
                backend.fill_selection_on_active_layer(color)
        else:
            backend.fill_area(0, 0, color, tolerance=255, contiguous=False)
        if self.workspace:
            self.workspace.canvas_widget.update()
        self.status_bar.showMessage("Preenchimento aplicado.", 2000)

    # ── 2. Seleção ────────────────────────────────────────────────────────

    def select_all(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.select_all()
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Tudo selecionado.", 2000)

    def invert_selection(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.invert_selection()
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Seleção invertida.", 2000)

    def open_modify_selection_dialog(self, mode: str) -> None:
        dialog = ModifySelectionDialog(mode=mode, parent=self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            px = dialog.get_pixels()
            self.status_bar.showMessage(f"Seleção modificada ({mode}: {px} px).", 2000)

    # ── 3. Camadas ────────────────────────────────────────────────────────

    def _active_layer_context(self):
        doc = self.dm.active_document()
        if not doc or not hasattr(doc, "layer_manager"):
            return None, None, None, -1
        lm = doc.layer_manager
        layer = lm.get_active_layer()
        idx = lm.active_index
        backend = EngineRegistry.instance().get_backend()
        return doc, lm, backend, idx

    @staticmethod
    def _backend_ready(backend) -> bool:
        return bool(backend and getattr(backend, "available", False))

    def _refresh_canvas(self) -> None:
        if self.workspace:
            self.workspace.canvas_widget.update()

    @layer_transaction
    def create_new_layer(self) -> None:
        doc, lm, backend, idx = self._active_layer_context()
        if not lm:
            return
        insert_index = idx + 1 if idx >= 0 else -1
        if self._backend_ready(backend):
            native_idx = backend.add_layer("Nova Camada", insert_index)
            if native_idx < 0:
                self.status_bar.showMessage("Não foi possível criar a camada no motor.", 2500)
                return
        uid = lm.add_layer("Nova Camada")
        if uid:
            if self._backend_ready(backend):
                backend.select_layer(lm.active_index)
            self._refresh_canvas()
            self.status_bar.showMessage("Nova camada criada.", 2000)

    @layer_transaction
    def create_new_group(self) -> None:
        doc, lm, backend, idx = self._active_layer_context()
        if not lm:
            return
        insert_index = idx + 1 if idx >= 0 else -1
        if self._backend_ready(backend):
            native_idx = backend.add_group("Novo Grupo", insert_index)
            if native_idx < 0:
                self.status_bar.showMessage("Não foi possível criar o grupo no motor.", 2500)
                return
        uid = lm.add_group("Novo Grupo")
        if uid:
            if self._backend_ready(backend):
                backend.select_layer(lm.active_index)
            self._refresh_canvas()
            self.status_bar.showMessage("Novo grupo de camadas criado.", 2000)

    @layer_transaction
    def duplicate_active_layer(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        if self._backend_ready(backend) and backend.duplicate_layer(act_idx) < 0:
            self.status_bar.showMessage("Não foi possível duplicar a camada no motor.", 2500)
            return
        active = lm.get_active_layer()
        if active and lm.duplicate_layer(active.uid):
            if self._backend_ready(backend):
                backend.select_layer(lm.active_index)
            self._refresh_canvas()
            self.status_bar.showMessage("Camada duplicada.", 2000)

    @layer_transaction
    def delete_active_layer(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        active = lm.get_active_layer()
        if not active:
            return
        if self._backend_ready(backend) and not backend.remove_layer(act_idx):
            self.status_bar.showMessage("Não foi possível remover a camada no motor.", 2500)
            return
        if lm.remove_layer(active.uid):
            if self._backend_ready(backend):
                backend.select_layer(lm.active_index)
            self._refresh_canvas()
            self.status_bar.showMessage("Camada removida.", 2000)

    @layer_transaction
    def merge_layer_down(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx <= 0:
            return
        active = lm.get_active_layer()
        if not active:
            return
        if self._backend_ready(backend) and not backend.merge_layer_down(act_idx):
            self.status_bar.showMessage("Não foi possível mesclar a camada no motor.", 2500)
            return
        if lm.merge_down(active.uid):
            if self._backend_ready(backend):
                backend.select_layer(lm.active_index)
            self._refresh_canvas()
            self.status_bar.showMessage("Camada mesclada para baixo.", 2000)

    @layer_transaction
    def toggle_active_layer_clipping(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        layer = lm.get_layer_at_index(act_idx)
        curr = bool(getattr(layer, "clipping_mask", False))
        value = not curr
        if self._backend_ready(backend):
            backend.set_layer_clipping_mask(act_idx, value)
        lm.set_clipping_mask(act_idx, value)
        self._refresh_canvas()
        state_str = "ativada" if value else "desativada"
        self.status_bar.showMessage(f"Máscara de corte {state_str}.", 2000)

    @layer_transaction
    def toggle_active_layer_alpha_lock(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        layer = lm.get_layer_at_index(act_idx)
        curr = bool(getattr(layer, "alpha_locked", False))
        value = not curr
        if self._backend_ready(backend):
            backend.set_layer_alpha_lock(act_idx, value)
        lm.set_alpha_lock(act_idx, value)
        self._refresh_canvas()
        state_str = "ativado" if value else "desativado"
        self.status_bar.showMessage(f"Bloqueio Alpha {state_str}.", 2000)

    @layer_transaction
    def toggle_active_layer_visibility(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        layer = lm.get_layer_at_index(act_idx)
        curr = bool(getattr(layer, "visible", True))
        value = not curr
        if self._backend_ready(backend):
            backend.set_layer_visibility(act_idx, value)
        lm.set_layer_visibility(act_idx, value)
        self._refresh_canvas()
        state_str = "visível" if value else "oculta"
        self.status_bar.showMessage(f"Camada {state_str}.", 2000)

    @layer_transaction
    def flatten_active_group(self) -> None:
        doc, lm, backend, act_idx = self._active_layer_context()
        if not lm or act_idx < 0:
            return
        layer = lm.get_layer_at_index(act_idx)
        if not layer or not layer.is_group:
            return
        if self._backend_ready(backend) and not backend.flatten_group(act_idx):
            self.status_bar.showMessage("Não foi possível achatar o grupo no motor.", 2500)
            return
        if not lm.flatten_group(act_idx):
            raise RuntimeError("Falha ao atualizar o modelo ao achatar grupo.")
        self._refresh_canvas()
        self.status_bar.showMessage("Grupo achatado com sucesso.", 2000)

    @layer_transaction
    def flatten_entire_image(self) -> None:
        doc, lm, backend, _ = self._active_layer_context()
        if not lm:
            return
        guard = 0
        while any(layer.is_group for layer in lm.layers):
            guard += 1
            if guard > len(lm.layers) + 1:
                raise RuntimeError("Achatar grupos não apresentou progresso.")
            idx = next(i for i, layer in enumerate(lm.layers) if layer.is_group)
            if self._backend_ready(backend) and not backend.flatten_group(idx):
                raise RuntimeError("Falha ao achatar grupo.")
            if not lm.flatten_group(idx):
                raise RuntimeError("Falha ao atualizar o modelo ao achatar grupo.")
        while len(lm.layers) > 1:
            top = lm.layers[-1]
            idx = len(lm.layers) - 1
            if self._backend_ready(backend) and not backend.merge_layer_down(idx):
                self.status_bar.showMessage("Não foi possível achatar a imagem no motor.", 2500)
                return
            before_count = len(lm.layers)
            if not lm.merge_down(top.uid) or len(lm.layers) >= before_count:
                self.status_bar.showMessage("A operação de achatar não avançou.", 2500)
                return
        self._refresh_canvas()
        self.status_bar.showMessage("Imagem achatada completamente.", 2000)

    @layer_transaction
    def open_layer_properties_dialog(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        doc = self.dm.active_document()
        if not doc or not hasattr(doc, "layer_manager"):
            return
        lm = doc.layer_manager
        act_idx = lm.active_index
        if act_idx < 0:
            return
        layer = lm.layers[act_idx]
        dialog = LayerPropertiesDialog(
            name=getattr(layer, "name", "Camada"),
            opacity=getattr(layer, "opacity", 1.0),
            blend_mode=getattr(layer, "blend_mode", 0),
            is_visible=getattr(layer, "visible", True),
            is_alpha_locked=getattr(layer, "alpha_locked", False),
            is_clipping=getattr(layer, "clipping_mask", False),
            parent=self
        )
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            res = dialog.get_results()
            lm.set_layer_name(act_idx, res["name"])
            lm.set_layer_opacity(act_idx, res["opacity"])
            lm.set_layer_blend_mode(act_idx, res["blend_mode"])
            lm.set_layer_visibility(act_idx, res["is_visible"])
            lm.set_alpha_lock(act_idx, res["is_alpha_locked"])
            lm.set_clipping_mask(act_idx, res["is_clipping"])
            if self._backend_ready(backend):
                backend.set_layer_name(act_idx, res["name"])
                backend.set_layer_opacity(act_idx, res["opacity"])
                backend.set_layer_blend_mode(act_idx, res["blend_mode"])
                backend.set_layer_visibility(act_idx, res["is_visible"])
                backend.set_layer_alpha_lock(act_idx, res["is_alpha_locked"])
                backend.set_layer_clipping_mask(act_idx, res["is_clipping"])
            self._refresh_canvas()
            self.status_bar.showMessage("Propriedades da camada atualizadas.", 2000)

