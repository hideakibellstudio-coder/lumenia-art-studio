"""Contrato de capacidades reais entre a UI e os backends de pintura."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.core.dialogs.render_settings_components import EnginePipelineGroup
from ui.engine_backends.aladyn import AladynBackend


app = QApplication.instance() or QApplication(["--platform", "offscreen"])


def test_aladyn_capabilities_describe_the_active_native_facade(tmp_path):
    backend = AladynBackend()
    try:
        capabilities = backend.get_capabilities()
        expected = (
            "native_engine", "render", "stroke", "brush_controls", "raster_document", "multi_document", "layers", "groups",
            "filters", "selection", "transform", "guides", "canvas_texture", "history",
            "scratch_history", "lod", "telemetry", "low_latency", "linear_gamma",
            "deep_color", "color_profiles", "color_profile_preview", "export_image",
        )
        assert all(capabilities[name] for name in expected)
        assert capabilities["document_pixel_format"] == "RGBA8"
        assert not capabilities["embedded_icc_profiles"]
        assert not capabilities["rgba16_document"]
        assert backend.supports_capability("export_image")
        assert not backend.supports_capability("not_a_capability")

        output = tmp_path / "composition.png"
        assert backend.export_image(output)
        assert output.is_file() and output.stat().st_size > 0
    finally:
        backend.close_document_context("default_doc")


def test_render_pipeline_controls_follow_backend_capabilities():
    disabled = EnginePipelineGroup({}, {"history": False})
    assert not disabled.switch_lat.isEnabled()
    assert not disabled.switch_gam.isEnabled()
    assert not disabled.switch_deep.isEnabled()
    assert not disabled.combo_undo.isEnabled()

    enabled = EnginePipelineGroup({}, {
        "low_latency": True,
        "linear_gamma": True,
        "deep_color": True,
        "history": True,
    })
    assert enabled.switch_lat.isEnabled()
    assert enabled.switch_gam.isEnabled()
    assert enabled.switch_deep.isEnabled()
    assert enabled.combo_undo.isEnabled()
