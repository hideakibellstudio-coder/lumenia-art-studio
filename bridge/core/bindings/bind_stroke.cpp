#include "BindingsCommon.hpp"
#include "BufferContract.hpp"
#include "../../../engine/core/raster/LargeBrushOptimizer.hpp"

namespace aladyn::bridge {

using namespace aladyn::engine;

void bind_stroke(py::module_& m, FacadeClass& facade) {
    // ─── TELEMETRY & DIAGNOSTICS TYPES ─────────────────────────────────────────
    py::class_<telemetry::RealTimeStrokeMetrics>(m, "RealTimeStrokeMetrics")
        .def(py::init<>())
        .def_readwrite("last_segment_latency_us",  &telemetry::RealTimeStrokeMetrics::lastSegmentLatencyUs)
        .def_readwrite("stroke_total_time_ms",     &telemetry::RealTimeStrokeMetrics::strokeTotalTimeMs)
        .def_readwrite("total_dabs_in_stroke",     &telemetry::RealTimeStrokeMetrics::totalDabsInStroke)
        .def_readwrite("total_dabs_per_second",    &telemetry::RealTimeStrokeMetrics::totalDabsPerSecond)
        .def_readwrite("input_event_rate_hz",      &telemetry::RealTimeStrokeMetrics::inputEventRateHz)
        // Decomposição Granular do Pipeline (µs)
        .def_readwrite("time_kinematics_us",       &telemetry::RealTimeStrokeMetrics::timeKinematicsUs)
        .def_readwrite("time_interpolation_us",   &telemetry::RealTimeStrokeMetrics::timeInterpolationUs)
        .def_readwrite("time_raster_dab_us",       &telemetry::RealTimeStrokeMetrics::timeRasterDabUs)
        .def_readwrite("time_undo_record_us",      &telemetry::RealTimeStrokeMetrics::timeUndoRecordUs)
        .def_readwrite("time_composite_us",        &telemetry::RealTimeStrokeMetrics::timeCompositeUs)
        // Pegada Geométrica e Densidade Instantânea
        .def_readwrite("last_dabs_rendered",       &telemetry::RealTimeStrokeMetrics::lastDabsRendered)
        .def_readwrite("last_dirty_width",         &telemetry::RealTimeStrokeMetrics::lastDirtyWidth)
        .def_readwrite("last_dirty_height",        &telemetry::RealTimeStrokeMetrics::lastDirtyHeight)
        .def_readwrite("last_dirty_area_px",       &telemetry::RealTimeStrokeMetrics::lastDirtyAreaPx)
        .def_readwrite("last_tiles_recorded",      &telemetry::RealTimeStrokeMetrics::lastTilesRecorded)
        .def_readwrite("last_tiles_composited",    &telemetry::RealTimeStrokeMetrics::lastTilesComposited)
        // Memória e Gestão de Blocos (Tiles)
        .def_readwrite("active_tile_count",        &telemetry::RealTimeStrokeMetrics::activeTileCount)
        .def_readwrite("dirty_tiles_last_stroke",  &telemetry::RealTimeStrokeMetrics::dirtyTilesLastStroke)
        .def_readwrite("tile_grid_memory_mb",      &telemetry::RealTimeStrokeMetrics::tileGridMemoryMB)
        .def_readwrite("undo_stack_memory_mb",     &telemetry::RealTimeStrokeMetrics::undoStackMemoryMB)
        .def_readwrite("undo_steps_count",         &telemetry::RealTimeStrokeMetrics::undoStepsCount)
        // Cinemática e Estabilização
        .def_readwrite("raw_pressure",             &telemetry::RealTimeStrokeMetrics::rawPressure)
        .def_readwrite("dynamic_pressure",         &telemetry::RealTimeStrokeMetrics::dynamicPressure)
        .def_readwrite("stroke_velocity",          &telemetry::RealTimeStrokeMetrics::strokeVelocity)
        .def_readwrite("stabilizer_lag_px",        &telemetry::RealTimeStrokeMetrics::stabilizerLagPx)
        // Mini-Motor & SIMD
        .def_readwrite("active_engine_id",         &telemetry::RealTimeStrokeMetrics::activeEngineId)
        .def_readwrite("simd_active",              &telemetry::RealTimeStrokeMetrics::simdActive);

    facade
        // Troca de motor em tempo real
        .def("set_engine_type",        &boundary::PaintEngineFacade::setEngineType)
        .def("get_active_engine_type", &boundary::PaintEngineFacade::getActiveEngineType)
        // Traço
        .def("begin_stroke",     &boundary::PaintEngineFacade::beginStroke)
        .def("update_stroke",    &boundary::PaintEngineFacade::updateStroke)
        .def("end_stroke",       &boundary::PaintEngineFacade::endStroke)
        .def("begin_stroke_raw",  &boundary::PaintEngineFacade::beginStrokeRaw,
             py::arg("x"), py::arg("y"), py::arg("pressure") = 1.0, py::arg("timestamp") = 0.0,
             py::arg("tilt_x") = 0.0, py::arg("tilt_y") = 0.0, py::arg("twist") = 0.0)
        .def("update_stroke_raw", &boundary::PaintEngineFacade::updateStrokeRaw,
             py::arg("x"), py::arg("y"), py::arg("pressure") = 1.0, py::arg("timestamp") = 0.0,
             py::arg("tilt_x") = 0.0, py::arg("tilt_y") = 0.0, py::arg("twist") = 0.0)
        .def("end_stroke_raw",    &boundary::PaintEngineFacade::endStrokeRaw,
             py::arg("end_x") = -1e9, py::arg("end_y") = -1e9)
        // Texturas e presets
        .def("set_shape_preset", &boundary::PaintEngineFacade::setShapePreset)
        .def("set_brush_height_preset", &boundary::PaintEngineFacade::setBrushHeightPreset)
        .def("set_canvas_height_preset", &boundary::PaintEngineFacade::setCanvasHeightPreset)
        .def("load_shape_texture", [](boundary::PaintEngineFacade& self, int w, int h, py::bytes data) {
            std::string s = data;
            validateRasterInput(s, w, h, 1);
            self.loadShapeTextureFromBuffer(w, h, reinterpret_cast<const uint8_t*>(s.data()));
        })
        .def("load_brush_height_texture", [](boundary::PaintEngineFacade& self, int w, int h, py::bytes data) {
            std::string s = data;
            validateRasterInput(s, w, h, 1);
            self.loadBrushHeightTextureFromBuffer(w, h, reinterpret_cast<const uint8_t*>(s.data()));
        })
        .def("load_canvas_height_texture", [](boundary::PaintEngineFacade& self, int w, int h, py::bytes data) {
            std::string s = data;
            validateRasterInput(s, w, h, 1);
            self.loadCanvasHeightTextureFromBuffer(w, h, reinterpret_cast<const uint8_t*>(s.data()));
        })
        // Preview buffers
        .def("get_shape_preview_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            const auto tex = self.getBrushProfile().shapeTexture;
            if (!tex) {
                constexpr int sz = 64;
                const double center = 32.0;
                const double maxDist = 30.0;
                const double hardness = std::clamp(self.getBrushProfile().hardness, 0.0, 0.99);
                const double hardSpan = hardness * maxDist;
                const double invSoftSpan = 1.0 / std::max(0.001, maxDist - hardSpan);
                std::vector<uint8_t> preview(sz * sz, 0);
                for (int y = 0; y < sz; ++y) {
                    const double dy = static_cast<double>(y) + 0.5 - center;
                    for (int x = 0; x < sz; ++x) {
                        const double dx = static_cast<double>(x) + 0.5 - center;
                        const double dist = std::sqrt(dx * dx + dy * dy);
                        if (dist > maxDist) continue;
                        double a = 1.0;
                        if (dist > hardSpan) {
                            const double t = (maxDist - dist) * invSoftSpan;
                            a = raster::LargeBrushOptimizer::smoothHermite(t);
                        }
                        preview[static_cast<size_t>(y * sz + x)] = static_cast<uint8_t>(std::clamp(a * 255.0, 0.0, 255.0));
                    }
                }
                return py::bytes(reinterpret_cast<const char*>(preview.data()), preview.size());
            }
            return pixelSnapshot(tex->getData(), checkedRasterBytes(tex->getWidth(), tex->getHeight(), 1));
        })
        .def("get_shape_preview_dimensions", [](boundary::PaintEngineFacade& self) {
            const auto tex = self.getBrushProfile().shapeTexture;
            return tex ? std::make_pair(tex->getWidth(), tex->getHeight()) : std::make_pair(64, 64);
        })
        .def("get_brush_height_preview_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            const auto tex = self.getBrushProfile().brushHeightTexture;
            if (!tex) return py::none();
            return pixelSnapshot(tex->getData(), checkedRasterBytes(tex->getWidth(), tex->getHeight(), 1));
        })
        .def("get_brush_height_preview_dimensions", [](boundary::PaintEngineFacade& self) {
            const auto tex = self.getBrushProfile().brushHeightTexture;
            return tex ? std::make_pair(tex->getWidth(), tex->getHeight()) : std::make_pair(0, 0);
        })
        .def("get_canvas_height_preview_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            const auto tex = self.getCanvasTexture().canvasHeightTexture;
            if (!tex) return py::none();
            return pixelSnapshot(tex->getData(), checkedRasterBytes(tex->getWidth(), tex->getHeight(), 1));
        })
        .def("get_canvas_height_preview_dimensions", [](boundary::PaintEngineFacade& self) {
            const auto tex = self.getCanvasTexture().canvasHeightTexture;
            return tex ? std::make_pair(tex->getWidth(), tex->getHeight()) : std::make_pair(0, 0);
        })
        // Acesso ao estado
        .def("get_brush_profile",  [](boundary::PaintEngineFacade& self) -> brush::BrushProfile& {
            return self.getBrushProfile();
        }, py::return_value_policy::reference_internal)
        .def("get_canvas_texture", [](boundary::PaintEngineFacade& self) -> canvas::CanvasTexture& {
            return self.getCanvasTexture();
        }, py::return_value_policy::reference_internal)
        .def("get_stabilizer", [](boundary::PaintEngineFacade& self) -> stroke::DynamicStabilizer& {
            return self.getStabilizer();
        }, py::return_value_policy::reference_internal)
        // ─── TELEMETRIA E DIAGNÓSTICO EM TEMPO REAL ──────────────────────────
        .def("set_telemetry_enabled", &boundary::PaintEngineFacade::setTelemetryEnabled)
        .def("is_telemetry_enabled", &boundary::PaintEngineFacade::isTelemetryEnabled)
        .def("set_detailed_logging_enabled", &boundary::PaintEngineFacade::setDetailedLoggingEnabled)
        .def("is_detailed_logging_enabled", &boundary::PaintEngineFacade::isDetailedLoggingEnabled)
        .def("get_telemetry_snapshot", &boundary::PaintEngineFacade::getTelemetrySnapshot)
        .def("reset_telemetry", &boundary::PaintEngineFacade::resetTelemetry);
}

} // namespace aladyn::bridge
