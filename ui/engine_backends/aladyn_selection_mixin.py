"""Selection operations mixin for AladynBackend."""

from typing import Optional
from PySide6.QtGui import QImage, QColor


class AladynSelectionMixin:
    """Mixin contendo operações de seleção raster e vetorial."""

    def magic_wand_select(
        self, seed_x: int, seed_y: int, tolerance: int = 20, contiguous: bool = True,
        expand_px: int = 0, anti_aliasing: bool = True, mode: int = 0,
        sample_all_layers: bool = True
    ) -> bool:
        if self._facade:
            self._mark_document_dirty("selection")
            return self._facade.magic_wand_select(
                int(seed_x), int(seed_y), int(tolerance), bool(contiguous),
                int(expand_px), bool(anti_aliasing), int(mode), bool(sample_all_layers)
            )
        return False

    def select_rect(self, x: int, y: int, w: int, h: int, mode: int = 0, feather_px: int = 0, corner_radius_px: int = 0) -> bool:
        if self._facade:
            self._mark_document_dirty("selection")
            return self._facade.select_rect(int(x), int(y), int(w), int(h), int(mode), int(feather_px), int(corner_radius_px))
        return False

    def select_ellipse(self, cx: int, cy: int, rx: int, ry: int, mode: int = 0, anti_aliasing: bool = True, feather_px: int = 0) -> bool:
        if self._facade:
            self._mark_document_dirty("selection")
            return self._facade.select_ellipse(int(cx), int(cy), int(rx), int(ry), int(mode), bool(anti_aliasing), int(feather_px))
        return False

    def select_polygon(self, flat_points: list[int], mode: int = 0, anti_aliasing: bool = True, feather_px: int = 0) -> bool:
        if self._facade:
            self._mark_document_dirty("selection")
            return self._facade.select_polygon([int(p) for p in flat_points], int(mode), bool(anti_aliasing), int(feather_px))
        return False

    def clear_selection(self) -> None:
        if self._facade:
            if self._facade.has_selection():
                self._mark_document_dirty("selection")
            self._facade.clear_selection()

    def invert_selection(self) -> None:
        if self._facade:
            self._mark_document_dirty("selection")
            self._facade.invert_selection()

    def select_all(self) -> None:
        if self._facade:
            self._mark_document_dirty("selection")
            self._facade.select_all()

    def has_selection(self) -> bool:
        if self._facade:
            return self._facade.has_selection()
        return False

    def delete_selection_on_active_layer(self) -> bool:
        if self._facade:
            return self._facade.delete_selection_on_active_layer()
        return False

    def fill_selection_on_active_layer(self, fill_color: QColor) -> bool:
        if self._facade and self._native:
            c = self._native.ColorRGBA(int(fill_color.red()), int(fill_color.green()), int(fill_color.blue()), int(fill_color.alpha()))
            return self._facade.fill_selection_on_active_layer(c)
        return False

    def get_selection_bounds(self) -> tuple[int, int, int, int]:
        if self._facade:
            b = self._facade.get_selection_bounds()
            if len(b) >= 4:
                return (b[0], b[1], b[2], b[3])
        return (0, 0, 0, 0)

    def get_selection_contour_segments(self) -> list[int]:
        if self._facade:
            return self._facade.get_selection_contour_segments()
        return []

    def get_selection_contour_loops(self) -> list[list[int]]:
        if self._facade:
            return self._facade.get_selection_contour_loops()
        return []

    def get_selection_mask_qimage(self) -> Optional[QImage]:
        if self._facade:
            memview = self._facade.get_selection_mask_buffer()
            if memview:
                w, h = self._facade.get_width(), self._facade.get_height()
                return QImage(memview, w, h, w, QImage.Format_Grayscale8).copy()
        return None

    def get_selection_mask_buffer(self) -> Optional[bytes]:
        if self._facade:
            raw = self._facade.get_selection_mask_buffer()
            return bytes(raw) if raw is not None else None
        return None

    def set_selection_mask_buffer(self, pixels: bytes) -> bool:
        return bool(self._facade and self._facade.set_selection_mask_buffer(bytes(pixels)))
