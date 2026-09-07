"""SecondaryToolbarHandlersMixin — Composed event handlers for SecondaryToolBar options.

Clean composition of domain-specific option handlers adhering strictly to ARCcC v2 (< 25 LOC).
"""

from .handlers.selection_toolbar_handlers import SelectionToolbarHandlersMixin
from .handlers.shape_text_toolbar_handlers import ShapeTextToolbarHandlersMixin
from .handlers.brush_fill_toolbar_handlers import BrushFillToolbarHandlersMixin


class SecondaryToolbarHandlersMixin(
    SelectionToolbarHandlersMixin,
    ShapeTextToolbarHandlersMixin,
    BrushFillToolbarHandlersMixin
):
    """Composed mixin with all event handlers and configuration dispatchers for active tools."""
    pass


__all__ = ["SecondaryToolbarHandlersMixin"]
