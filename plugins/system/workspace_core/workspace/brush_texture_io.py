"""BrushTextureIO — Loading and applying custom brush textures and heightmaps from disk.

Strictly decoupled in compliance with ARCcC v2.
"""

from typing import Any, Optional, Tuple
from PySide6 import QtGui, QtWidgets


class BrushTextureIO:
    """Manages file dialogs, RGBA conversion, and backend/renderer texture loading."""

    @staticmethod
    def prompt_and_load_texture(parent_widget: Optional[QtWidgets.QWidget] = None) -> Optional[Tuple[bytes, int, int, str]]:
        """Prompts user for image file and returns (raw_rgba_bytes, width, height, filepath) or None."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            parent_widget,
            "Selecionar Imagem de Textura",
            "",
            "Imagens (*.png *.jpg *.jpeg *.bmp *.tga)",
        )
        if not file_path:
            return None

        image = QtGui.QImage(file_path)
        if image.isNull():
            QtWidgets.QMessageBox.warning(
                parent_widget, "Erro", "Não foi possível carregar a imagem selecionada."
            )
            return None

        image = image.convertToFormat(QtGui.QImage.Format_RGBA8888)
        width = image.width()
        height = image.height()
        ptr = image.constBits()
        return ptr.tobytes(), width, height, file_path

    @classmethod
    def load_and_apply_to_workspace(cls, workspace: Any, is_shape: bool) -> bool:
        """Loads custom texture from disk and applies it to canvas renderer, backend, and dock."""
        res = cls.prompt_and_load_texture(parent_widget=workspace)
        if res is None:
            return False

        px_bytes, width, height, file_path = res

        cw = getattr(workspace, "canvas_widget", None)
        renderer = getattr(cw, "renderer", None)
        if renderer:
            if is_shape:
                renderer.set_shape_texture(px_bytes, width, height)
            else:
                renderer.set_heightmap_texture(px_bytes, width, height)

        from ui.core.engine.registry import EngineRegistry
        backend = EngineRegistry.instance().get_backend()
        if backend:
            if is_shape:
                backend.set_shape_texture(px_bytes, width, height)
            elif not is_shape:
                backend.set_heightmap_texture(px_bytes, width, height)
                if True:
                    backend.set_brush_grain_enabled(True)

        brush_dock = getattr(workspace, "_brush_dock", None)
        if brush_dock and hasattr(brush_dock, "update_thumbnail"):
            brush_dock.update_thumbnail(is_shape, file_path)

        if cw:
            cw.update()

        return True
