"""BrushEngineWriter — parâmetros AVANÇADOS do pincel que vão direto ao motor.

Só os parâmetros que nenhuma outra tela mostra (mínimos por pressão, ponta,
jitter, textura...). Os rápidos (tamanho, opacidade, estabilizador,
espaçamento, contraste, inverter topografia) vão para o `BrushState`, e o
`BrushEngineSync` é o único que os escreve no motor.

Colaborador com estado próprio (o provedor do motor), entregue às seções do
painel avançado. Substitui o `PanelEngineBridgeMixin`, que lia os widgets
das seções pendurados no painel (`self.chk_follow.isChecked()`).
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from PySide6 import QtCore, QtGui, QtWidgets

from .texture_file import read_texture_file

logger = logging.getLogger(__name__)

_PREVIEW = 46


class BrushEngineWriter:
    def __init__(self, backend: Callable[[], Any]) -> None:
        self._backend = backend

    # ── Perfil (motor → tela) ─────────────────────────────────────────────

    def profile(self) -> Optional[dict]:
        backend = self._backend()
        return backend.get_brush_profile_dict() if backend else None

    def engine_type(self) -> Optional[int]:
        backend = self._backend()
        return backend.get_active_engine_type() if backend else None

    # ── Escrita ───────────────────────────────────────────────────────────

    def root(self, name: str, value) -> None:
        """Parâmetro do perfil do pincel (mínimos por pressão, mesclagem...)."""
        backend = self._backend()
        if backend:
            backend.set_brush_param("root", name, value)

    def tip(self, name: str, value) -> None:
        """Parâmetro da ponta (ângulo, proporção, jitter...)."""
        backend = self._backend()
        if backend:
            backend.set_brush_param("tip", name, value)

    def hardness(self, value: float) -> None:
        backend = self._backend()
        if backend:
            backend.set_brush_hardness(value)

    def shape_preset(self, index: int) -> None:
        backend = self._backend()
        if backend:
            backend.set_shape_preset(index)

    def height_preset(self, index: int) -> None:
        backend = self._backend()
        if backend:
            backend.set_brush_height_preset(index)

    def grain_enabled(self, enabled: bool) -> None:
        backend = self._backend()
        if backend:
            backend.set_brush_grain_enabled(enabled)

    def grain_scale(self, value: float) -> None:
        backend = self._backend()
        if backend:
            backend.set_brush_grain_scale(value)

    def load_texture(self, dialog_parent: QtWidgets.QWidget, is_shape: bool) -> bool:
        """Lê uma imagem do disco e aplica como forma da ponta ou topografia (liga o grão)."""
        backend = self._backend()
        loaded = read_texture_file(dialog_parent)
        if loaded is None or backend is None:
            return False
        pixels, width, height, _path = loaded
        if is_shape:
            backend.set_shape_texture(pixels, width, height)
        else:
            backend.set_heightmap_texture(pixels, width, height)
            backend.set_brush_grain_enabled(True)
        return True

    # ── Miniaturas ────────────────────────────────────────────────────────

    def shape_preview(self) -> Optional[QtGui.QPixmap]:
        backend = self._backend()
        if not backend:
            return None
        return _preview(backend.get_shape_preview_buffer, backend.get_shape_preview_dimensions)

    def height_preview(self) -> Optional[QtGui.QPixmap]:
        backend = self._backend()
        if not backend:
            return None
        return _preview(backend.get_brush_height_preview_buffer, backend.get_brush_height_preview_dimensions)


def _preview(read_buffer, read_size) -> Optional[QtGui.QPixmap]:
    try:
        buf = read_buffer()
        w, h = read_size()
    except (RuntimeError, TypeError, ValueError) as exc:
        logger.debug("Miniatura do motor indisponível: %s", exc)
        return None
    if not buf or w <= 0 or h <= 0:
        return None
    image = QtGui.QImage(bytes(buf), w, h, w, QtGui.QImage.Format_Grayscale8)
    return QtGui.QPixmap.fromImage(image).scaled(
        _PREVIEW, _PREVIEW, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation
    )
