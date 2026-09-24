"""Capacidades efetivas publicadas pelo backend nativo Aladyn."""

from __future__ import annotations
import logging
import os
from pathlib import Path


class AladynCapabilitiesMixin:
    """Expõe suporte real sem fazer a UI inferir detalhes da fachada nativa."""

    def get_capabilities(self) -> dict[str, object]:
        facade = self._facade
        native = bool(self.available and facade)

        def has(*methods: str) -> bool:
            return native and all(hasattr(facade, method) for method in methods)

        return {
            "native_engine": native,
            "render": has("refresh_display", "get_display_pixel_buffer"),
            "stroke": has("begin_stroke_raw", "update_stroke_raw", "end_stroke_raw"),
            # Os parâmetros são expostos por referência no BrushProfile;
            # não existe um setter genérico na fachada nativa.
            "brush_controls": has("get_brush_profile", "set_engine_type"),
            "raster_document": has("get_pixel_buffer", "paste_rgba_buffer_on_active_layer"),
            "multi_document": native,
            "layers": has("add_layer", "remove_layer", "reorder_layers"),
            "groups": has("add_group", "set_layer_parents", "flatten_group"),
            "filters": has("add_filter_layer", "set_filter_params"),
            "selection": has("select_rect", "get_selection_mask_buffer"),
            "transform": has("begin_transform", "commit_transform"),
            "guides": has("set_guide_config", "set_symmetry_config"),
            "canvas_texture": has("get_canvas_height_texture", "load_canvas_height_texture"),
            "history": has("undo", "redo", "begin_layer_transaction"),
            "scratch_history": has("set_scratch_disk_enabled", "get_history_error"),
            "lod": has("get_display_pixel_buffer_lod", "get_best_lod_level"),
            "telemetry": has("set_telemetry_enabled", "get_telemetry_snapshot"),
            "low_latency": has("set_low_latency", "get_low_latency"),
            "linear_gamma": has("set_linear_gamma", "get_linear_gamma"),
            "deep_color": has("set_deep_color", "get_deep_color"),
            "color_profiles": has("set_color_profile", "get_available_color_profiles"),
            "color_profile_preview": has("transform_rgba_for_profile"),
            "embedded_icc_profiles": False,
            "rgba16_document": False,
            "export_image": native,
            "document_pixel_format": "RGBA8",
            "soft_proofing": True,
            "custom_color_profiles": True,
        }

    def supports_capability(self, capability: str) -> bool:
        return bool(self.get_capabilities().get(str(capability), False))

    def export_image(self, path: str | os.PathLike[str], embed_icc: bool = True) -> bool:
        """Exporta a composição ativa incorporando metadados ICC quando suportado."""
        target_path = Path(path)
        ext = target_path.suffix.lower()

        # Exportação enriquecida com perfil ICC para PNG, JPEG, TIFF e WebP
        if embed_icc and ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}:
            get_icc = getattr(self, "get_active_profile_icc_bytes", None)
            icc_bytes = get_icc() if callable(get_icc) else None
            if icc_bytes:
                image = self.get_qimage()
                if image and not image.isNull():
                    try:
                        from PIL import Image
                        w, h = image.width(), image.height()
                        img = Image.frombuffer("RGBA", (w, h), bytes(image.bits()), "raw", "RGBA", 0, 1)
                        if ext in {".jpg", ".jpeg"}:
                            img = img.convert("RGB")
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        img.save(str(target_path), icc_profile=icc_bytes)
                        return True
                    except Exception:
                        # Qualquer anomalia no Pillow: registra e usa o fallback QImage abaixo.
                        logging.getLogger(__name__).debug("Export via Pillow falhou; usando QImage.", exc_info=True)

        image = self.get_qimage()
        return bool(image and not image.isNull() and image.save(str(target_path)))
