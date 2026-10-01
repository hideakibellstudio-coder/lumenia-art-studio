"""display_image — the pixels the screen asks the engine for, and where they sit.

The viewport used to ask for the whole canvas on every repaint and then draw only
the dirty rectangle: at zoom 100% on a 4K document that was 34 ms of copying to
paint a few pixels (D4, found 2026-09-26). It now asks for what it paints:
`EngineBackend.get_display_image(zoom, region)` returns a `DisplayImage` that
covers `region` at working zoom, or the pre-filtered pyramid level when zoomed
out (the pyramid level is small and shared, so it still comes whole).

`source_rect` is the one place that maps "the canvas rectangle I am painting" to
"the rectangle of this image", so the viewport does not repeat the scale and
offset arithmetic for each case.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6 import QtCore

# The region asked from the engine is this much larger on every side than the
# rectangle drawn. Qt's raster engine clamps to the source rectangle, so for it the
# margin changes nothing (tests/test_display_region.py draws the same pixels with 0).
# The OpenGL engine samples the texels next to the source rectangle: there the margin
# keeps the border of a repainted rectangle blended with real neighbours, as it was
# when the whole canvas was the texture. That path cannot be exercised where the
# tests run (offscreen has no OpenGL), so the margin is a precaution, not a proof.
FILTER_MARGIN_PX = 2


@dataclass(frozen=True)
class DisplayImage:
    """RGBA pixels for the screen.

    `scale` is image pixels per canvas pixel (1.0 at working zoom; 0.5, 0.25 or
    0.125 for a pyramid level). `origin` is where this image starts inside the
    image of the whole canvas at that scale: (0, 0) for a pyramid level, the
    region's corner for a region. `pixels` keeps the native bytes alive for as
    long as `image` points into them.
    """

    image: Any  # QImage
    scale: float = 1.0
    origin: tuple[int, int] = (0, 0)
    pixels: Any = None

    def source_rect(self, canvas_rect: QtCore.QRect) -> QtCore.QRect:
        """The part of `image` that shows `canvas_rect` (canvas pixels), kept inside the image."""
        ox, oy = self.origin
        scale = self.scale
        wanted = QtCore.QRect(
            int(canvas_rect.x() * scale) - ox,
            int(canvas_rect.y() * scale) - oy,
            max(1, int(canvas_rect.width() * scale)),
            max(1, int(canvas_rect.height() * scale)),
        )
        return wanted.intersected(QtCore.QRect(0, 0, self.image.width(), self.image.height()))


def region_to_request(dirty: QtCore.QRect, canvas: QtCore.QRect) -> QtCore.QRect:
    """What to ask the engine for so that `dirty` can be drawn: it plus the filter margin, inside the canvas."""
    return dirty.adjusted(-FILTER_MARGIN_PX, -FILTER_MARGIN_PX, FILTER_MARGIN_PX, FILTER_MARGIN_PX).intersected(canvas)
