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
        if self._facade and hasattr(self._facade, "magic_wand_select"):
            return self._facade.magic_wand_select(
                int(seed_x), int(seed_y), int(tolerance), bool(contiguous),
                int(expand_px), bool(anti_aliasing), int(mode), bool(sample_all_layers)
            )
        return False

    def select_rect(self, x: int, y: int, w: int, h: int, mode: int = 0, feather_px: int = 0, corner_radius_px: int = 0) -> bool:
        if self._facade and hasattr(self._facade, "select_rect"):
            return self._facade.select_rect(int(x), int(y), int(w), int(h), int(mode), int(feather_px), int(corner_radius_px))
        return False

    def select_ellipse(self, cx: int, cy: int, rx: int, ry: int, mode: int = 0, anti_aliasing: bool = True, feather_px: int = 0) -> bool:
        if self._facade and hasattr(self._facade, "select_ellipse"):
            return self._facade.select_ellipse(int(cx), int(cy), int(rx), int(ry), int(mode), bool(anti_aliasing), int(feather_px))
        return False

    def select_polygon(self, flat_points: list[int], mode: int = 0, anti_aliasing: bool = True, feather_px: int = 0) -> bool:
        if self._facade and hasattr(self._facade, "select_polygon"):
            return self._facade.select_polygon([int(p) for p in flat_points], int(mode), bool(anti_aliasing), int(feather_px))
        return False

    def clear_selection(self) -> None:
        if self._facade and hasattr(self._facade, "clear_selection"):
            self._facade.clear_selection()

    def invert_selection(self) -> None:
        if self._facade and hasattr(self._facade, "invert_selection"):
            self._facade.invert_selection()

    def select_all(self) -> None:
        if self._facade and hasattr(self._facade, "select_all"):
            self._facade.select_all()

    def has_selection(self) -> bool:
        if self._facade and hasattr(self._facade, "has_selection"):
            return self._facade.has_selection()
        return False

    def delete_selection_on_active_layer(self) -> bool:
        if self._facade and hasattr(self._facade, "delete_selection_on_active_layer"):
            return self._facade.delete_selection_on_active_layer()
        return False

    def fill_selection_on_active_layer(self, fill_color: QColor) -> bool:
        if self._facade and self._native and hasattr(self._facade, "fill_selection_on_active_layer"):
            c = self._native.ColorRGBA(int(fill_color.red()), int(fill_color.green()), int(fill_color.blue()), int(fill_color.alpha()))
            return self._facade.fill_selection_on_active_layer(c)
        return False

    def get_selection_bounds(self) -> tuple[int, int, int, int]:
        if self._facade and hasattr(self._facade, "get_selection_bounds"):
            b = self._facade.get_selection_bounds()
            if len(b) >= 4:
                return (b[0], b[1], b[2], b[3])
        return (0, 0, 0, 0)

    def get_selection_contour_segments(self) -> list[int]:
        if self._facade and hasattr(self._facade, "get_selection_contour_segments"):
            return self._facade.get_selection_contour_segments()
        return []

    def get_selection_contour_loops(self) -> list[list[int]]:
        if self._facade and hasattr(self._facade, "get_selection_contour_loops"):
            return self._facade.get_selection_contour_loops()
        return []

    def get_selection_mask_qimage(self) -> Optional[QImage]:
        if self._facade and hasattr(self._facade, "get_selection_mask_buffer"):
            memview = self._facade.get_selection_mask_buffer()
            if memview:
                w, h = self._facade.get_width(), self._facade.get_height()
                return QImage(memview, w, h, w, QImage.Format_Grayscale8)
        return None
