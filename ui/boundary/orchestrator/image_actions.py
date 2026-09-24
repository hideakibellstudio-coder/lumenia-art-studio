"""ImageActions — menu Imagem e parte do Exibir: tamanho, recorte, rotação e guias.

Colaborador da `MainWindow` (ver `shell_actions.py`). Mudanças de tamanho do
documento passam por `change_geometry`, que emite `Document.geometry_changed`:
o workspace se ajusta sozinho (antes a janela escrevia `workspace.canvas_w`).
"""
from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from ui.core.dialogs.canvas_size_dialog import CanvasSizeDialog
from ui.core.document.geometry import change_geometry
from ui.core.document.manager import DocumentManager

from .shell_actions import BackendProvider, ShellActions, backend_ready
from .workspace_port import ShellCanvas, ShellWorkspace


class ImageActions(ShellActions):
    def __init__(
        self,
        window: QtWidgets.QWidget,
        dm: DocumentManager,
        backend: BackendProvider,
        workspace: Optional[ShellWorkspace],
    ) -> None:
        super().__init__(window)
        self._window = window
        self._dm = dm
        self._backend = backend
        self._workspace = workspace
        self._canvas: Optional[ShellCanvas] = workspace.canvas_widget if workspace is not None else None

    # ── Arquivo ───────────────────────────────────────────────────────────

    def export_image(self) -> None:
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self._window, "Exportar Imagem", "", "Imagem PNG (*.png);;Imagem JPEG (*.jpg *.jpeg)"
        )
        if not filename:
            return
        backend = self._backend()
        if not (backend and backend.supports_capability("export_image")):
            self._say("O backend ativo não suporta exportação de imagem.", 5000)
        elif backend.export_image(filename):
            self._say(f"Imagem exportada com sucesso para '{filename}'", 4000)
        else:
            self._say("Falha ao exportar a imagem.", 5000)

    # ── Tamanho e recorte ─────────────────────────────────────────────────

    def resize_dialog(self, is_image_resize: bool = False) -> None:
        doc = self._dm.active_document()
        backend = self._backend()
        if doc is None or not backend_ready(backend):
            self._say("Nenhum documento ativo para redimensionar.", 2500)
            return
        dialog = CanvasSizeDialog(current_w=doc.width, current_h=doc.height,
                                  is_image_resize=is_image_resize, parent=self._window)
        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return
        res = dialog.get_results()
        nw, nh = res["width"], res["height"]
        try:
            change_geometry(
                doc, backend, nw, nh,
                anchor=res.get("anchor", (1, 1)),
                resample=res.get("resample_mode") if is_image_resize else None,
            )
        except Exception as exc:
            self._say(f"Falha ao redimensionar: {exc}", 5000)
            return
        self._reset_view()
        action_name = "Imagem redimensionada" if is_image_resize else "Canvas redimensionado"
        self._say(f"{action_name} para {nw}×{nh} px.", 3000)

    def crop_to_selection(self) -> None:
        backend = self._backend()
        doc = self._dm.active_document()
        bounds = backend.get_selection_bounds() if backend and backend.has_selection() else []
        if len(bounds) < 4 or bounds[2] <= 0 or bounds[3] <= 0:
            self._say("Nenhuma seleção ativa para recortar.", 2000)
            return
        if doc is None or not backend_ready(backend):
            return
        x, y, w, h = bounds[:4]
        try:
            change_geometry(doc, backend, w, h, crop=(x, y))
        except Exception as exc:
            self._say(f"Falha ao recortar: {exc}", 5000)
            return
        backend.clear_selection()
        self._reset_view()
        self._say(f"Imagem recortada para a seleção ({w}×{h} px).", 3000)

    # ── Rotação da camada ─────────────────────────────────────────────────

    def rotate_layer_90(self, clockwise: bool = True) -> None:
        backend = self._backend()
        if not backend:
            return
        backend.rotate_active_layer_90(clockwise)
        if self._canvas is not None:
            self._canvas.update()
        dir_str = "Horário (CW)" if clockwise else "Anti-horário (CCW)"
        self._say(f"Camada rotacionada 90° {dir_str}.", 2000)

    def rotate_layer_180(self) -> None:
        self.rotate_layer_90(True)
        self.rotate_layer_90(True)
        self._say("Camada rotacionada 180°.", 2000)

    # ── Vista (rotação e espelhamento só da tela) ─────────────────────────

    def reset_view_rotation(self) -> None:
        if self._canvas is None:
            return
        self._canvas.rotation = 0.0
        self._canvas.publish_view()  # antes só repintava: o Navigator ficava girado
        self._say("Rotação do canvas resetada para 0°.", 2000)

    def flip_view_horizontal(self) -> None:
        if self._canvas is None:
            return
        self._canvas.flip_x = not self._canvas.flip_x
        self._say("Visualização espelhada horizontalmente.", 2000)

    def flip_view_vertical(self) -> None:
        if self._canvas is None:
            return
        self._canvas.flip_y = not self._canvas.flip_y
        self._say("Visualização espelhada verticalmente.", 2000)

    # ── Guias, réguas e prova de cores ────────────────────────────────────

    def toggle_grid(self) -> None:
        if self._canvas is None:
            return
        visible = self._canvas.toggle_grid()
        self._say(f"Grade magnética {'ativada' if visible else 'oculta'}.", 2000)

    def toggle_rulers(self) -> None:
        if self._canvas is None:
            return
        visible = self._canvas.toggle_rulers()
        self._say(f"Réguas {'ativadas' if visible else 'ocultas'}.", 2000)

    def toggle_soft_proof(self, enabled: bool) -> None:
        """Liga/desliga a prova de cores sem abrir diálogo (Exibir > Prova de Cores).

        Só alterna `enabled`; perfil, intent e gamut continuam os configurados em
        Configurações > Renderização & Modos de Cor.
        """
        backend = self._backend()
        if not backend_ready(backend):
            return
        config = backend.get_soft_proofing()
        config.enabled = bool(enabled)
        backend.set_soft_proofing(config)
        if self._canvas is not None:
            self._canvas.update()
        self._say("Prova de cores ativada." if enabled else "Prova de cores desativada.", 2000)

    def _reset_view(self) -> None:
        if self._workspace is not None:
            self._workspace.reset_view()
