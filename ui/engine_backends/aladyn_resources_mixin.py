"""Document-owned canvas assets crossing the canonical backend boundary."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aladyn_engine_native import CanvasTexture


class AladynResourcesMixin:
    def get_canvas_resource(self):
        if not self._facade:
            return None
        texture = self._facade.get_canvas_height_texture()
        if texture is None:
            return None
        canvas: "CanvasTexture" = self._facade.get_canvas_texture()
        width, height, pixels = texture
        return {"width": width, "height": height, "pixels": bytes(pixels),
                "enabled": canvas.canvas_grain_enabled,
                "scale": canvas.canvas_grain_scale,
                "contrast": canvas.canvas_grain_contrast,
                "invert": canvas.canvas_grain_invert,
                "curve": list(canvas.canvas_texture_curve.get_lut())}

    def set_canvas_resource(self, state):
        if not self._facade:
            return False
        self._facade.load_canvas_height_texture(state["width"], state["height"], state["pixels"])
        canvas: "CanvasTexture" = self._facade.get_canvas_texture()
        canvas.canvas_grain_enabled = state["enabled"]
        canvas.canvas_grain_scale = state["scale"]
        canvas.canvas_grain_contrast = state["contrast"]
        canvas.canvas_grain_invert = state["invert"]
        canvas.canvas_texture_curve.set_lut(state["curve"])
        canvas.invalidate_lut()
        return self.get_canvas_resource() == state
