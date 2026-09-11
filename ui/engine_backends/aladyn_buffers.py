"""Pixel format conversion at the canonical RGBA / native intensity boundary."""

from PIL import Image, ImageChops


def texture_intensity(pixels: bytes, width: int, height: int) -> bytes:
    """Pack luminance multiplied by alpha; transparent pixels contribute zero."""
    if width <= 0 or height <= 0 or width * height * 4 > 2**31 - 1:
        raise ValueError("Dimensões de textura fora do limite suportado.")
    if len(pixels) != width * height * 4:
        raise ValueError("A textura deve conter exatamente width * height * 4 bytes RGBA.")
    image = Image.frombytes("RGBA", (width, height), pixels)
    return ImageChops.multiply(image.convert("L"), image.getchannel("A")).tobytes()
