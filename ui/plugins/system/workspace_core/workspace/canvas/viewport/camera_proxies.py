"""CanvasCameraProxies — zoom/pan/rotação/espelhamento do canvas lidos da câmera.

O estado mora no `CameraController`; estas propriedades só deixam o resto do
workspace escrever `canvas.zoom = ...` sem conhecer a câmera. Depois de mudar
zoom/pan/rotação, quem escreveu chama `canvas.publish_view()`; o
espelhamento publica sozinho porque o Navigator o altera por um setter só.

Até 2026-09-24 este arquivo era `canvas_compat.py`: além da câmera tinha 17
apelidos privados (`_sel_drag_active`, `_lasso_points`, ...) para controladores
das ferramentas, que ninguém mais lia, e `renderer`/`input_adapter`, dois
caminhos paralelos ao motor substituídos por `publish_view()`.
"""

from __future__ import annotations


class CanvasCameraProxies:
    """Mixin do RenderWidget: exige `self.camera` e `self.publish_view()`."""

    @property
    def zoom(self) -> float: return self.camera.zoom
    @zoom.setter
    def zoom(self, v: float): self.camera.zoom = v

    @property
    def pan_x(self) -> float: return self.camera.pan_x
    @pan_x.setter
    def pan_x(self, v: float): self.camera.pan_x = v

    @property
    def pan_y(self) -> float: return self.camera.pan_y
    @pan_y.setter
    def pan_y(self, v: float): self.camera.pan_y = v

    @property
    def rotation(self) -> float: return self.camera.rotation
    @rotation.setter
    def rotation(self, v: float): self.camera.rotation = v

    @property
    def flip_x(self) -> bool: return self.camera.flip_horizontal
    @flip_x.setter
    def flip_x(self, v: bool) -> None:
        if self.camera.flip_horizontal != bool(v):
            self.camera.flip_horizontal = bool(v)
            self.publish_view()

    @property
    def flip_y(self) -> bool: return self.camera.flip_vertical
    @flip_y.setter
    def flip_y(self, v: bool) -> None:
        if self.camera.flip_vertical != bool(v):
            self.camera.flip_vertical = bool(v)
            self.publish_view()
