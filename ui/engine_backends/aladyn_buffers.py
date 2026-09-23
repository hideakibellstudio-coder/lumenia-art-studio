"""Pixel format conversion at the canonical RGBA / native intensity boundary."""

import logging
from typing import Any
from PIL import Image, ImageChops


def texture_intensity(pixels: bytes, width: int, height: int) -> bytes:
    """Pack luminance multiplied by alpha; transparent pixels contribute zero."""
    if width <= 0 or height <= 0 or width * height * 4 > 2**31 - 1:
        raise ValueError("Dimensões de textura fora do limite suportado.")
    if len(pixels) != width * height * 4:
        raise ValueError("A textura deve conter exatamente width * height * 4 bytes RGBA.")
    image = Image.frombytes("RGBA", (width, height), pixels)
    return ImageChops.multiply(image.convert("L"), image.getchannel("A")).tobytes()


def to_native_color_rgba(native: Any, color: Any):
    """Converte defensivamente qualquer representação de cor em ColorRGBA nativo."""
    if native is None:
        return None
    if isinstance(color, native.ColorRGBA):
        return color
    if hasattr(color, "red") and hasattr(color, "green") and hasattr(color, "blue"):
        a = color.alpha() if hasattr(color, "alpha") else 255
        return native.ColorRGBA(int(color.red()), int(color.green()), int(color.blue()), int(a))
    if isinstance(color, (tuple, list)) and len(color) >= 3:
        r = int(color[0] * 255) if isinstance(color[0], float) else int(color[0])
        g = int(color[1] * 255) if isinstance(color[1], float) else int(color[1])
        b = int(color[2] * 255) if isinstance(color[2], float) else int(color[2])
        if len(color) > 3:
            a = int(color[3] * 255) if isinstance(color[3], float) else int(color[3])
        else:
            a = 255
        return native.ColorRGBA(r, g, b, a)
    if hasattr(color, "r") and hasattr(color, "g") and hasattr(color, "b"):
        a = getattr(color, "a", 255)
        return native.ColorRGBA(int(color.r), int(color.g), int(color.b), int(a))
    # Entrada irreconhecível: mantém o preto histórico, mas sem silêncio -- um
    # preenchimento preto inesperado já foi um bug real (rodada 9, balde de tinta).
    logging.getLogger(__name__).warning(
        "to_native_color_rgba: cor de tipo %s não reconhecida; usando preto.", type(color).__name__
    )
    return native.ColorRGBA(0, 0, 0, 255)

