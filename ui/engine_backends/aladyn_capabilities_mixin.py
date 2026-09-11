"""Capacidades efetivas publicadas pelo backend nativo Aladyn."""

from __future__ import annotations


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
        }

    def supports_capability(self, capability: str) -> bool:
        return bool(self.get_capabilities().get(str(capability), False))

    def export_image(self, path: str) -> bool:
        image = self.get_qimage()
        return bool(image and not image.isNull() and image.save(str(path)))
