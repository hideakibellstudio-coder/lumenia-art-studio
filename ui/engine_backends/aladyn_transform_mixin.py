"""Transform and raster manipulation operations mixin for AladynBackend."""

from typing import Optional
from PySide6.QtGui import QImage


class AladynTransformMixin:
    """Mixin contendo operações de transformação livre, rotação, espelhamento e colagem."""

    def begin_transform(self) -> bool:
        if self._facade and hasattr(self._facade, "begin_transform"):
            return self._facade.begin_transform()
        return False

    def is_transform_active(self) -> bool:
        if self._facade and hasattr(self._facade, "is_transform_active"):
            return self._facade.is_transform_active()
        return False

    def get_transform_source_bounds(self) -> tuple[float, float, float, float]:
        if self._facade and hasattr(self._facade, "get_transform_source_bounds"):
            b = self._facade.get_transform_source_bounds()
            if len(b) >= 4:
                return (b[0], b[1], b[2], b[3])
        return (0.0, 0.0, 0.0, 0.0)

    def get_transform_pivot(self) -> tuple[float, float]:
        if self._facade and hasattr(self._facade, "get_transform_pivot"):
            p = self._facade.get_transform_pivot()
            if len(p) >= 2:
                return (p[0], p[1])
        return (0.0, 0.0)

    def commit_transform(
        self,
        dx: float, dy: float,
        scale_x: float, scale_y: float,
        rotation_deg: float,
        pivot_x: float, pivot_y: float,
        flip_h: bool = False,
        flip_v: bool = False,
        interp_mode: int = 2
    ) -> bool:
        if self._facade and hasattr(self._facade, "commit_transform"):
            return self._facade.commit_transform(
                float(dx), float(dy),
                float(scale_x), float(scale_y),
                float(rotation_deg),
                float(pivot_x), float(pivot_y),
                bool(flip_h), bool(flip_v),
                int(interp_mode)
            )
        return False

    def cancel_transform(self) -> bool:
        if self._facade and hasattr(self._facade, "cancel_transform"):
            return self._facade.cancel_transform()
        return False

    def flip_active_layer(self, horizontal: bool) -> bool:
        if self._facade and hasattr(self._facade, "flip_active_layer"):
            return self._facade.flip_active_layer(bool(horizontal))
        return False

    def rotate_active_layer_90(self, clockwise: bool) -> bool:
        if self._facade and hasattr(self._facade, "rotate_active_layer_90"):
            return self._facade.rotate_active_layer_90(bool(clockwise))
        return False

    def get_transform_source_qimage(self) -> Optional[QImage]:
        if self._facade and hasattr(self._facade, "get_transform_source_buffer"):
            memview = self._facade.get_transform_source_buffer()
            if memview:
                sz = self._facade.get_transform_source_buffer_size()
                if sz[0] > 0 and sz[1] > 0:
                    return QImage(memview, sz[0], sz[1], sz[0] * 4, QImage.Format_RGBA8888)
        return None

    def paste_rgba_buffer_on_active_layer(
        self, x: int, y: int, width: int, height: int, data: bytes, blend_mode: int = 0, opacity: float = 1.0
    ) -> bool:
        if self._facade and hasattr(self._facade, "paste_rgba_buffer_on_active_layer"):
            self._facade.paste_rgba_buffer_on_active_layer(
                int(x), int(y), int(width), int(height), data, int(blend_mode), float(opacity)
            )
            return True
        return False
