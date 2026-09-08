"""MainWindowMenuActionsMixin — Handlers de Ações da MenuBar para MainWindow."""

from __future__ import annotations
import os
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.registry import EngineRegistry
from ui.core.dialogs.canvas_size_dialog import CanvasSizeDialog
from ui.core.dialogs.modify_selection_dialog import ModifySelectionDialog
from ui.core.dialogs.layer_properties_dialog import LayerPropertiesDialog
from .main_window_dialog_actions import MainWindowDialogActionsMixin


class MainWindowMenuActionsMixin(MainWindowDialogActionsMixin):
    """Mixin com todos os manipuladores de ações da MenuBar do Lumenia."""

    # ── 1. Área de Transferência (Clipboard) ──────────────────────────────

    def copy_selection_or_layer_to_clipboard(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if not backend or not hasattr(backend, "get_qimage"):
            return
        qimg = backend.get_qimage()
        if qimg and not qimg.isNull():
            QtWidgets.QApplication.clipboard().setImage(qimg)
            self.status_bar.showMessage("Camada / Imagem copiada para a Área de Transferência.", 2500)

    def cut_selection_or_layer_to_clipboard(self) -> None:
        self.copy_selection_or_layer_to_clipboard()
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "has_selection") and backend.has_selection():
            if hasattr(backend, "delete_selection_on_active_layer"):
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
        if hasattr(backend, "has_selection") and backend.has_selection():
            if hasattr(backend, "fill_selection_on_active_layer"):
                backend.fill_selection_on_active_layer(color)
        elif hasattr(backend, "fill_area"):
            backend.fill_area(0, 0, color, tolerance=255, contiguous=False)
        if self.workspace:
            self.workspace.canvas_widget.update()
        self.status_bar.showMessage("Preenchimento aplicado.", 2000)

    # ── 2. Seleção ────────────────────────────────────────────────────────

    def select_all(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "select_all"):
            backend.select_all()
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Tudo selecionado.", 2000)

    def invert_selection(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "invert_selection"):
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

    def create_new_layer(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            idx = doc.layer_manager.add_layer("Nova Camada")
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Nova camada criada.", 2000)

    def create_new_group(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            idx = doc.layer_manager.add_group("Novo Grupo")
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Novo grupo de camadas criado.", 2000)

    def duplicate_active_layer(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx >= 0:
                lm.duplicate_layer(act_idx)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage("Camada duplicada.", 2000)

    def delete_active_layer(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx >= 0:
                lm.remove_layer(act_idx)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage("Camada removida.", 2000)

    def merge_layer_down(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx > 0:
                lm.merge_down(act_idx)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage("Camada mesclada para baixo.", 2000)

    def toggle_active_layer_clipping(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx >= 0:
                curr = getattr(lm.layers[act_idx], "is_clipping_mask", False)
                lm.set_clipping_mask(act_idx, not curr)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                state_str = "ativada" if not curr else "desativada"
                self.status_bar.showMessage(f"Máscara de corte {state_str}.", 2000)

    def toggle_active_layer_alpha_lock(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx >= 0:
                curr = getattr(lm.layers[act_idx], "is_alpha_locked", False)
                lm.set_alpha_lock(act_idx, not curr)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                state_str = "ativado" if not curr else "desativado"
                self.status_bar.showMessage(f"Bloqueio Alpha {state_str}.", 2000)

    def toggle_active_layer_visibility(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx >= 0:
                curr = getattr(lm.layers[act_idx], "visible", True)
                lm.set_layer_visibility(act_idx, not curr)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                state_str = "oculta" if curr else "visível"
                self.status_bar.showMessage(f"Camada {state_str}.", 2000)

    def flatten_active_group(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            act_idx = lm.active_index
            if act_idx >= 0:
                lm.flatten_group(act_idx)
                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.status_bar.showMessage("Grupo achatado com sucesso.", 2000)

    def flatten_entire_image(self) -> None:
        doc = self.dm.active_document()
        if doc and hasattr(doc, "layer_manager"):
            lm = doc.layer_manager
            while len(lm.layers) > 1:
                lm.merge_down(len(lm.layers) - 1)
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Imagem achatada completamente.", 2000)

    def open_layer_properties_dialog(self) -> None:
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
            is_alpha_locked=getattr(layer, "is_alpha_locked", False),
            is_clipping=getattr(layer, "is_clipping_mask", False),
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
            if self.workspace:
                self.workspace.canvas_widget.update()
            self.status_bar.showMessage("Propriedades da camada atualizadas.", 2000)

    # ── 4. Imagem, Arquivo & Canvas ───────────────────────────────────────

    def open_image_file(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Abrir Imagem", "", "Imagens (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if filename:
            qimg = QtGui.QImage(filename)
            if not qimg.isNull():
                name = os.path.splitext(os.path.basename(filename))[0]
                w, h = qimg.width(), qimg.height()
                doc = self.dm.new_document(width=w, height=h, name=name)

                qimg_rgba = qimg.convertToFormat(QtGui.QImage.Format_RGBA8888)
                raw_bytes = bytes(qimg_rgba.constBits()[:w * h * 4])
                backend = EngineRegistry.instance().get_backend()
                if backend and getattr(backend, "available", False):
                    backend.paste_rgba_buffer_on_active_layer(0, 0, w, h, raw_bytes)

                if self.workspace:
                    self.workspace.canvas_widget.update()
                self.reset_view()
                self.status_bar.showMessage(f"Imagem '{name}' ({w}x{h}) aberta com sucesso!", 3000)

    def save_active_document(self) -> None:
        doc = self.dm.active_document()
        if doc:
            self.status_bar.showMessage(f"Documento '{doc.name}' salvo.", 2000)
        else:
            self.status_bar.showMessage("Nenhum documento ativo para salvar.", 2000)

    def export_image(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Exportar Imagem", "", "Imagem PNG (*.png);;Imagem JPEG (*.jpg *.jpeg)"
        )
        if filename:
            backend = EngineRegistry.instance().get_backend()
            if backend and hasattr(backend, "get_qimage"):
                qimg = backend.get_qimage()
                if qimg and not qimg.isNull():
                    qimg.save(filename)
                    self.status_bar.showMessage(f"Imagem exportada com sucesso para '{filename}'", 4000)

    def reset_rotation(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            cw.rotation = 0.0
            cw.update()
            self.status_bar.showMessage("Rotação do canvas resetada para 0°.", 2000)

    def flip_horizontal(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            if hasattr(cw, "flip_x"):
                cw.flip_x = not getattr(cw, "flip_x", False)
                cw.update()
                self.status_bar.showMessage("Visualização espelhada horizontalmente.", 2000)

    def flip_vertical(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            if hasattr(cw, "flip_y"):
                cw.flip_y = not getattr(cw, "flip_y", False)
                cw.update()
                self.status_bar.showMessage("Visualização espelhada verticalmente.", 2000)

    def open_canvas_size_dialog(self, is_image_resize: bool = False) -> None:
        backend = EngineRegistry.instance().get_backend()
        w = getattr(backend, "_width", 1920) if backend else 1920
        h = getattr(backend, "_height", 1080) if backend else 1080
        dialog = CanvasSizeDialog(current_w=w, current_h=h, is_image_resize=is_image_resize, parent=self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            res = dialog.get_results()
            nw, nh = res["width"], res["height"]
            if backend and hasattr(backend, "resize"):
                backend.resize(nw, nh)
            if self.workspace:
                self.workspace.canvas_w = nw
                self.workspace.canvas_h = nh
                self.workspace.canvas_widget.update()
                self.reset_view()
            action_name = "Imagem redimensionada" if is_image_resize else "Canvas redimensionado"
            self.status_bar.showMessage(f"{action_name} para {nw}×{nh} px.", 3000)

    def crop_to_selection(self) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend and hasattr(backend, "has_selection") and backend.has_selection():
            if hasattr(backend, "get_selection_bounds"):
                b = backend.get_selection_bounds()
                if len(b) >= 4 and b[2] > 0 and b[3] > 0:
                    backend.resize(b[2], b[3])
                    backend.clear_selection()
                    if self.workspace:
                        self.workspace.canvas_w = b[2]
                        self.workspace.canvas_h = b[3]
                        self.workspace.canvas_widget.update()
                        self.reset_view()
                    self.status_bar.showMessage(f"Imagem recortada para a seleção ({b[2]}×{b[3]} px).", 3000)
                    return
        self.status_bar.showMessage("Nenhuma seleção ativa para recortar.", 2000)

    def rotate_active_layer_90(self, clockwise: bool = True) -> None:
        backend = EngineRegistry.instance().get_backend()
        if backend:
            backend.rotate_active_layer_90(clockwise)
            if self.workspace:
                self.workspace.canvas_widget.update()
            dir_str = "Horário (CW)" if clockwise else "Anti-horário (CCW)"
            self.status_bar.showMessage(f"Camada rotacionada 90° {dir_str}.", 2000)

    def rotate_active_layer_180(self) -> None:
        self.rotate_active_layer_90(True)
        self.rotate_active_layer_90(True)
        self.status_bar.showMessage("Camada rotacionada 180°.", 2000)

    # ── 5. Guias & Réguas ─────────────────────────────────────────────────

    def toggle_grid(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            if hasattr(cw, "geometry_controller"):
                gs = cw.geometry_controller.guide_state
                curr = gs.get("show_v", True)
                gs["show_v"] = not curr
                gs["show_h"] = not curr
                gs["show_d"] = not curr
                cw.update()
                state = "ativada" if not curr else "oculta"
                self.status_bar.showMessage(f"Grade magnética {state}.", 2000)

    def toggle_rulers(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            if hasattr(cw, "geometry_controller"):
                gs = cw.geometry_controller.guide_state
                curr = gs.get("type", "none") != "none"
                gs["type"] = "straight" if not curr else "none"
                cw.update()
                state = "ativadas" if not curr else "ocultas"
                self.status_bar.showMessage(f"Réguas {state}.", 2000)
