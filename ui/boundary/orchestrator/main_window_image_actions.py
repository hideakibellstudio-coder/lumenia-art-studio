"""MainWindowImageActionsMixin — Handlers de Ações de Imagem, Canvas e Guias."""

from __future__ import annotations
from typing import TYPE_CHECKING
from PySide6 import QtCore, QtGui, QtWidgets
from ui.core.engine.registry import EngineRegistry
from ui.core.dialogs.canvas_size_dialog import CanvasSizeDialog

if TYPE_CHECKING:
    from plugins.system.workspace_core.workspace.canvas.render_widget import RenderWidget


class MainWindowImageActionsMixin:
    """Mixin para operações de imagem, redimensionamento de canvas e guias/réguas."""

    # ── Imagem, Arquivo & Canvas ──────────────────────────────────────────
    def export_image(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Exportar Imagem", "", "Imagem PNG (*.png);;Imagem JPEG (*.jpg *.jpeg)"
        )
        if filename:
            backend = EngineRegistry.instance().get_backend()
            if backend and backend.supports_capability("export_image"):
                if backend.export_image(filename):
                    self.status_bar.showMessage(f"Imagem exportada com sucesso para '{filename}'", 4000)
                else:
                    self.status_bar.showMessage("Falha ao exportar a imagem.", 5000)
            else:
                self.status_bar.showMessage("O backend ativo não suporta exportação de imagem.", 5000)

    def reset_rotation(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw: "RenderWidget" = self.workspace.canvas_widget
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
            doc = self.dm.active_document()
            if doc and self._backend_ready(backend):
                from ui.core.document.geometry import change_geometry
                try:
                    change_geometry(
                        doc, backend, nw, nh,
                        anchor=res.get("anchor", (1, 1)),
                        resample=res.get("resample_mode") if is_image_resize else None,
                    )
                except Exception as exc:
                    self.status_bar.showMessage(f"Falha ao redimensionar: {exc}", 5000)
                    return
            elif backend:
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
        if backend and backend.has_selection():
            if True:
                b = backend.get_selection_bounds()
                if len(b) >= 4 and b[2] > 0 and b[3] > 0:
                    doc = self.dm.active_document()
                    if not doc or not self._backend_ready(backend):
                        return
                    from ui.core.document.geometry import change_geometry
                    try:
                        change_geometry(doc, backend, b[2], b[3], crop=(b[0], b[1]))
                    except Exception as exc:
                        self.status_bar.showMessage(f"Falha ao recortar: {exc}", 5000)
                        return
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

    # ── Guias & Réguas ────────────────────────────────────────────────────

    def toggle_grid(self) -> None:
        if self.workspace and hasattr(self.workspace, "canvas_widget"):
            cw = self.workspace.canvas_widget
            geo_ctrl = getattr(cw, "geometry_ctrl", getattr(cw, "geometry_controller", None))
            if geo_ctrl and hasattr(geo_ctrl, "guide_state"):
                gs = geo_ctrl.guide_state
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
            geo_ctrl = getattr(cw, "geometry_ctrl", getattr(cw, "geometry_controller", None))
            if geo_ctrl and hasattr(geo_ctrl, "guide_state"):
                gs = geo_ctrl.guide_state
                curr = gs.get("type", "none") != "none"
                gs["type"] = "straight" if not curr else "none"
                cw.update()
                state = "ativadas" if not curr else "ocultas"
                self.status_bar.showMessage(f"Réguas {state}.", 2000)

