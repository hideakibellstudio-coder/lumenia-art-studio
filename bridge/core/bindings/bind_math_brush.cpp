#include "BindingsCommon.hpp"
#include "../../../engine/core/math/ViewportTransform.hpp"

namespace aladyn::bridge {

using namespace aladyn::engine;

void bind_math_brush(py::module_& m, FacadeClass& /*facade*/) {
    // ─── MATH ────────────────────────────────────────────────────────────────
    py::class_<math::Point2D>(m, "Point2D")
        .def(py::init<>())
        .def(py::init<double, double>())
        .def_readwrite("x", &math::Point2D::x)
        .def_readwrite("y", &math::Point2D::y)
        .def("distance_to", &math::Point2D::distanceTo);

    py::enum_<math::CurvePreset>(m, "CurvePreset")
        .value("Linear", math::CurvePreset::Linear)
        .value("Soft", math::CurvePreset::Soft)
        .value("Hard", math::CurvePreset::Hard)
        .value("S", math::CurvePreset::S)
        .value("Threshold", math::CurvePreset::Threshold)
        .export_values();

    py::class_<math::BezierCurve>(m, "BezierCurve")
        .def(py::init<>())
        .def(py::init<math::CurvePreset>())
        .def("set_control_points", &math::BezierCurve::setControlPoints)
        .def("set_preset", &math::BezierCurve::setPreset)
        .def("set_power", &math::BezierCurve::setPower)
        .def("get_lut", &math::BezierCurve::getLut)
        .def("set_lut", &math::BezierCurve::setLut)
        .def("invert", &math::BezierCurve::invert)
        .def("sample", &math::BezierCurve::sample);

    py::enum_<math::SymmetryMode>(m, "SymmetryMode")
        .value("None", math::SymmetryMode::None)
        .value("Mirror", math::SymmetryMode::Mirror)
        .value("DoubleMirror", math::SymmetryMode::DoubleMirror)
        .value("Radial", math::SymmetryMode::Radial)
        .value("Kaleidoscope", math::SymmetryMode::Kaleidoscope)
        .export_values();

    py::enum_<math::GuideType>(m, "GuideType")
        .value("None", math::GuideType::None)
        .value("Straight", math::GuideType::Straight)
        .value("CurveRuler", math::GuideType::CurveRuler)
        .value("Curvilinear", math::GuideType::Curvilinear)
        .value("OnePoint", math::GuideType::OnePoint)
        .value("TwoPoint", math::GuideType::TwoPoint)
        .value("ThreePoint", math::GuideType::ThreePoint)
        .value("Isometric", math::GuideType::Isometric)
        .export_values();

    py::class_<math::ViewportTransform>(m, "ViewportTransform")
        .def(py::init<double, double, double, double>(),
             py::arg("viewport_width") = 1920.0,
             py::arg("viewport_height") = 1080.0,
             py::arg("canvas_width") = 1920.0,
             py::arg("canvas_height") = 1080.0)
        .def("set_viewport_size", &math::ViewportTransform::setViewportSize)
        .def("set_canvas_size", &math::ViewportTransform::setCanvasSize)
        .def("set_camera", &math::ViewportTransform::setCamera,
             py::arg("pan_x"), py::arg("pan_y"), py::arg("zoom"), py::arg("rotation_deg"),
             py::arg("flip_h") = false, py::arg("flip_v") = false)
        .def("canvas_to_screen", [](const math::ViewportTransform& self, double cx, double cy) {
            auto pt = self.canvasToScreen(cx, cy);
            return std::make_pair(pt.x, pt.y);
        })
        .def("screen_to_canvas", [](const math::ViewportTransform& self, double sx, double sy) {
            auto pt = self.screenToCanvas(sx, sy);
            return std::make_pair(pt.x, pt.y);
        })
        .def("get_visible_canvas_bounds", [](const math::ViewportTransform& self) {
            auto r = self.getVisibleCanvasBounds();
            return std::make_tuple(r.x, r.y, r.width, r.height);
        })
        .def("get_visible_tile_range", &math::ViewportTransform::getVisibleTileRange)
        .def("is_tile_visible", &math::ViewportTransform::isTileVisible)
        .def_property_readonly("zoom", &math::ViewportTransform::getZoom)
        .def_property_readonly("pan_x", &math::ViewportTransform::getPanX)
        .def_property_readonly("pan_y", &math::ViewportTransform::getPanY)
        .def_property_readonly("rotation_deg", &math::ViewportTransform::getRotationDeg);

    // ─── ENGINE TYPE (CATEGORIAS DE MOTOR) ───────────────────────────────────
    py::enum_<brush::EngineType>(m, "EngineType")
        .value("Brush", brush::EngineType::Brush)
        .value("Pencil", brush::EngineType::Pencil)
        .value("Inker", brush::EngineType::Inker)
        .value("Eraser", brush::EngineType::Eraser)
        .value("Marker", brush::EngineType::Marker)
        .value("Blur", brush::EngineType::Blur)
        .value("Smudge", brush::EngineType::Smudge)
        .value("Watercolor", brush::EngineType::Watercolor)
        .value("OilImpasto", brush::EngineType::OilImpasto)
        .export_values();

    // ─── DAB BLEND MODE (APENAS O QUE O MOTOR SUPORTA) ──────────────────────
    py::enum_<raster::DabBlendMode>(m, "DabBlendMode")
        .value("Normal",   raster::DabBlendMode::Normal)
        .value("Multiply", raster::DabBlendMode::Multiply)
        .value("Additive", raster::DabBlendMode::Additive)
        .value("Erase",    raster::DabBlendMode::Erase)
        .export_values();

    // ─── LAYER BLEND MODE (MODO DE MESCLAGEM DAS CAMADAS DO DOCUMENTO) ───────
    // Os 13 valores completos de document::LayerBlendMode (LayerNode.hpp) --
    // antes só os 7 primeiros (Normal..Erase) estavam expostos aqui, mesmo
    // o motor (BlendEquations.hpp) e a UI (layers_plugin/header.py) já
    // suportando os 13. ui/engine_backends/aladyn_layer_mixin.py não depende
    // mais deste binding para converter (passa int puro para
    // PaintEngineFacade::setLayerBlendMode), mas o binding devia documentar
    // o contrato completo mesmo assim -- ver
    // claude/verificacao-cruzada-planos-solidificacao.md (Fase C5).
    py::enum_<document::LayerBlendMode>(m, "LayerBlendMode")
        .value("Normal",      document::LayerBlendMode::Normal)
        .value("Multiply",    document::LayerBlendMode::Multiply)
        .value("Screen",      document::LayerBlendMode::Screen)
        .value("Overlay",     document::LayerBlendMode::Overlay)
        .value("Darken",      document::LayerBlendMode::Darken)
        .value("Lighten",     document::LayerBlendMode::Lighten)
        .value("Erase",       document::LayerBlendMode::Erase)
        .value("PassThrough", document::LayerBlendMode::PassThrough)
        .value("ColorDodge",  document::LayerBlendMode::ColorDodge)
        .value("ColorBurn",   document::LayerBlendMode::ColorBurn)
        .value("Difference",  document::LayerBlendMode::Difference)
        .value("Exclusion",   document::LayerBlendMode::Exclusion)
        .value("Add",         document::LayerBlendMode::Add)
        .export_values();

    // ─── SELECTION MODE ──────────────────────────────────────────────────────
    py::enum_<raster::SelectionMode>(m, "SelectionMode")
        .value("New",       raster::SelectionMode::New)
        .value("Add",       raster::SelectionMode::Add)
        .value("Subtract",  raster::SelectionMode::Subtract)
        .value("Intersect", raster::SelectionMode::Intersect)
        .export_values();

    py::class_<raster::ColorRGBA>(m, "ColorRGBA")
        .def(py::init<>())
        .def(py::init<uint8_t, uint8_t, uint8_t, uint8_t>(),
             py::arg("r"), py::arg("g"), py::arg("b"), py::arg("a") = 255)
        .def_readwrite("r", &raster::ColorRGBA::r)
        .def_readwrite("g", &raster::ColorRGBA::g)
        .def_readwrite("b", &raster::ColorRGBA::b)
        .def_readwrite("a", &raster::ColorRGBA::a);

    // ─── STROKE ──────────────────────────────────────────────────────────────
    py::enum_<stroke::PointerEventType>(m, "PointerEventType")
        .value("Press",   stroke::PointerEventType::Press)
        .value("Move",    stroke::PointerEventType::Move)
        .value("Release", stroke::PointerEventType::Release)
        .export_values();

    py::class_<stroke::PointerEvent>(m, "PointerEvent")
        .def(py::init<>())
        .def(py::init<stroke::PointerEventType, math::Point2D, double, double, double, double, double>(),
             py::arg("type"), py::arg("position"),
             py::arg("pressure") = 1.0, py::arg("timestamp") = 0.0,
             py::arg("tilt_x") = 0.0, py::arg("tilt_y") = 0.0, py::arg("twist") = 0.0)
        .def_readwrite("type",      &stroke::PointerEvent::type)
        .def_readwrite("position",  &stroke::PointerEvent::position)
        .def_readwrite("pressure",  &stroke::PointerEvent::pressure)
        .def_readwrite("timestamp", &stroke::PointerEvent::timestamp)
        .def_readwrite("tilt_x",    &stroke::PointerEvent::tiltX)
        .def_readwrite("tilt_y",    &stroke::PointerEvent::tiltY)
        .def_readwrite("twist",     &stroke::PointerEvent::twist)
        .def_readwrite("altitude",  &stroke::PointerEvent::altitude)
        .def_readwrite("azimuth",   &stroke::PointerEvent::azimuth)
        .def("compute_altitude_azimuth_from_tilt", &stroke::PointerEvent::computeAltitudeAzimuthFromTilt);

    py::class_<stroke::DynamicStabilizer>(m, "DynamicStabilizer")
        .def(py::init<double>(), py::arg("stabilization_percentage") = 40.0)
        .def("set_stabilization_percentage", &stroke::DynamicStabilizer::setStabilizationPercentage)
        .def("get_stabilization_percentage", &stroke::DynamicStabilizer::getStabilizationPercentage)
        .def("reset", &stroke::DynamicStabilizer::reset)
        .def("reanchor_initial_position", &stroke::DynamicStabilizer::reanchorInitialPosition, py::arg("new_initial_position"))
        .def("update", &stroke::DynamicStabilizer::update, py::arg("raw_position"), py::arg("normalized_velocity") = 0.0)
        .def("flush", &stroke::DynamicStabilizer::flush, py::arg("end_position"), py::arg("steps") = 3)
        .def("get_taper_points", &stroke::DynamicStabilizer::getTaperPoints, py::arg("steps") = 4, py::arg("max_distance") = 30.0)
        .def("get_stabilized_position", &stroke::DynamicStabilizer::getStabilizedPosition)
        .def("get_last_movement_delta", &stroke::DynamicStabilizer::getLastMovementDelta);

    // ─── BRUSH TIP GEOMETRY ──────────────────────────────────────────────────
    py::class_<brush::BrushTip>(m, "BrushTip")
        .def(py::init<>())
        .def_readwrite("angle",               &brush::BrushTip::angle)
        .def_readwrite("aspect_ratio",        &brush::BrushTip::aspectRatio)
        .def_readwrite("follow_stroke",       &brush::BrushTip::followStroke)
        .def_readwrite("jitter_size",         &brush::BrushTip::jitterSize)
        .def_readwrite("jitter_angle",        &brush::BrushTip::jitterAngle)
        .def_readwrite("jitter_position",     &brush::BrushTip::jitterPosition)
        .def_readwrite("jitter_hue",          &brush::BrushTip::jitterHue)
        .def_readwrite("jitter_saturation",   &brush::BrushTip::jitterSaturation)
        .def_readwrite("jitter_brightness",   &brush::BrushTip::jitterBrightness)
        .def_readwrite("use_twist_for_angle", &brush::BrushTip::useTwistForAngle)
        .def_readwrite("tilt_to_angle",       &brush::BrushTip::tiltToAngle)
        .def_readwrite("tilt_to_aspect",      &brush::BrushTip::tiltToAspect);

    // ─── PARÂMETROS EXCLUSIVOS POR MOTOR ─────────────────────────────────────
    py::class_<brush::PencilParams>(m, "PencilParams")
        .def(py::init<>())
        .def_readwrite("graphite_hardness",   &brush::PencilParams::graphiteHardness)
        .def_readwrite("tilt_shading_enabled",&brush::PencilParams::tiltShadingEnabled);

    py::class_<brush::InkerParams>(m, "InkerParams")
        .def(py::init<>())
        .def_readwrite("ink_flow_rate",    &brush::InkerParams::inkFlowRate)
        .def_readwrite("taper_smoothing",  &brush::InkerParams::taperSmoothing);

    py::class_<brush::MarkerParams>(m, "MarkerParams")
        .def(py::init<>())
        .def_readwrite("solvent_wetness",  &brush::MarkerParams::solventWetness)
        .def_readwrite("edge_darkening",   &brush::MarkerParams::edgeDarkening);

    py::class_<brush::BlurParams>(m, "BlurParams")
        .def(py::init<>())
        .def_readwrite("blur_radius",   &brush::BlurParams::blurRadius)
        .def_readwrite("blur_strength", &brush::BlurParams::blurStrength);

    py::class_<brush::SmudgeParams>(m, "SmudgeParams")
        .def(py::init<>())
        .def_readwrite("color_pickup",    &brush::SmudgeParams::colorPickup)
        .def_readwrite("mix_ratio",       &brush::SmudgeParams::mixRatio)
        .def_readwrite("smudge_stretch",  &brush::SmudgeParams::smudgeStretch);

    py::class_<brush::WatercolorParams>(m, "WatercolorParams")
        .def(py::init<>())
        .def_readwrite("water_level",       &brush::WatercolorParams::waterLevel)
        .def_readwrite("pigment_bleed",     &brush::WatercolorParams::pigmentBleed)
        .def_readwrite("fringe_intensity",  &brush::WatercolorParams::fringeIntensity)
        .def_readwrite("granulation",       &brush::WatercolorParams::granulation);

    py::class_<brush::OilParams>(m, "OilParams")
        .def(py::init<>())
        .def_readwrite("impasto_depth",       &brush::OilParams::impastoDepth)
        .def_readwrite("bristle_grooves",     &brush::OilParams::bristleGrooves)
        .def_readwrite("viscosity",           &brush::OilParams::viscosity)
        .def_readwrite("specular_brilliance", &brush::OilParams::specularBrilliance);

    // ─── BRUSH PROFILE COMPLETO ───────────────────────────────────────────────
    py::class_<brush::BrushProfile>(m, "BrushProfile")
        .def(py::init<>())
        // Motor ativo
        .def_readwrite("engine_type",           &brush::BrushProfile::engineType)
        // Tamanho e opacidade
        .def_readwrite("brush_size",            &brush::BrushProfile::brushSize)
        .def_readwrite("min_size_percent",      &brush::BrushProfile::minSizePercent)
        .def_readwrite("opacity",               &brush::BrushProfile::opacity)
        .def_readwrite("min_opacity_percent",   &brush::BrushProfile::minOpacityPercent)
        .def_readwrite("hardness",              &brush::BrushProfile::hardness)
        .def_readwrite("blend_mode",            &brush::BrushProfile::blendMode)
        .def_readwrite("spacing_factor",        &brush::BrushProfile::spacingFactor)
        .def_readwrite("base_color",            &brush::BrushProfile::baseColor)
        // Ativadores
        .def_readwrite("pressure_size_enabled", &brush::BrushProfile::pressureSizeEnabled)
        .def_readwrite("pressure_flow_enabled", &brush::BrushProfile::pressureFlowEnabled)
        .def_readwrite("velocity_size_enabled", &brush::BrushProfile::velocitySizeEnabled)
        .def_readwrite("stroke_taper_enabled",  &brush::BrushProfile::strokeTaperEnabled)
        // LUT Curves
        .def_readwrite("pressure_size_curve",   &brush::BrushProfile::pressureSizeCurve)
        .def_readwrite("pressure_flow_curve",   &brush::BrushProfile::pressureFlowCurve)
        .def_readwrite("velocity_size_curve",   &brush::BrushProfile::velocitySizeCurve)
        // Geometria da ponta
        .def_readwrite("tip",                   &brush::BrushProfile::tip)
        .def_readwrite("pressure_to_angle",     &brush::BrushProfile::pressureToAngle)
        .def_readwrite("pressure_to_aspect",    &brush::BrushProfile::pressureToAspect)
        .def_readwrite("scatter_count",         &brush::BrushProfile::scatterCount)
        // Emissão temporal
        .def_readwrite("time_spacing_enabled",  &brush::BrushProfile::timeSpacingEnabled)
        .def_readwrite("dabs_per_second",       &brush::BrushProfile::dabsPerSecond)
        // Textura do pincel
        .def_readwrite("brush_grain_enabled",   &brush::BrushProfile::brushGrainEnabled)
        .def_readwrite("brush_grain_scale",     &brush::BrushProfile::brushGrainScale)
        .def_readwrite("brush_grain_contrast",  &brush::BrushProfile::brushGrainContrast)
        .def_readwrite("brush_grain_invert",    &brush::BrushProfile::brushGrainInvert)
        .def_readwrite("brush_texture_curve",   &brush::BrushProfile::brushTextureCurve)
        // Parâmetros exclusivos por motor
        .def_readwrite("pencil_params",     &brush::BrushProfile::pencilParams)
        .def_readwrite("inker_params",      &brush::BrushProfile::inkerParams)
        .def_readwrite("marker_params",     &brush::BrushProfile::markerParams)
        .def_readwrite("blur_params",       &brush::BrushProfile::blurParams)
        .def_readwrite("smudge_params",     &brush::BrushProfile::smudgeParams)
        .def_readwrite("watercolor_params", &brush::BrushProfile::watercolorParams)
        .def_readwrite("oil_params",        &brush::BrushProfile::oilParams);

    // ─── CANVAS TEXTURE ───────────────────────────────────────────────────────
    py::class_<canvas::CanvasTexture>(m, "CanvasTexture")
        .def(py::init<>())
        .def_readwrite("background_color",        &canvas::CanvasTexture::backgroundColor)
        .def_readwrite("canvas_grain_enabled",    &canvas::CanvasTexture::canvasGrainEnabled)
        .def_readwrite("canvas_grain_scale",      &canvas::CanvasTexture::canvasGrainScale)
        .def_readwrite("canvas_grain_contrast",   &canvas::CanvasTexture::canvasGrainContrast)
        .def_readwrite("canvas_grain_invert",     &canvas::CanvasTexture::canvasGrainInvert)
        .def_readwrite("canvas_texture_curve",    &canvas::CanvasTexture::canvasTextureCurve)
        .def("invalidate_lut", &canvas::CanvasTexture::invalidateLUT);

    // ─── TELEMETRY DATA ───────────────────────────────────────────────────────
    py::class_<boundary::TelemetryData>(m, "TelemetryData")
        .def_readonly("pressure",    &boundary::TelemetryData::pressure)
        .def_readonly("velocity",    &boundary::TelemetryData::velocity)
        .def_readonly("output_flow", &boundary::TelemetryData::outputFlow);
}

} // namespace aladyn::bridge
