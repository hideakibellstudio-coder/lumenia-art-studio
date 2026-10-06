"""The largest canvas side, asked of the engine (S0.2, D13).

New Document, Canvas Size, Open Image and the geometry change used to carry
their own numbers (16384, 32000, 2 GB of payload, Qt's 256 MB). The engine owns
the limit; everyone else asks here.
"""

from ui.core.engine.backend import SHELL_MODE_MAX_CANVAS_DIMENSION, SHELL_MODE_MAX_CANVAS_DIMENSION_RGBA16
from ui.core.engine.registry import EngineRegistry


def max_canvas_dimension(pixel_format: int = 0) -> int:
    """The engine's limit, or the shell-mode value while no engine is registered."""
    backend = EngineRegistry.instance().get_backend()
    if backend is not None:
        return backend.max_canvas_dimension(int(pixel_format))
    return SHELL_MODE_MAX_CANVAS_DIMENSION_RGBA16 if int(pixel_format) == 1 else SHELL_MODE_MAX_CANVAS_DIMENSION
