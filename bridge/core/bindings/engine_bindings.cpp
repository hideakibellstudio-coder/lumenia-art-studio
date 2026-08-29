#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "../../../engine/boundary/public-api/PaintEngineFacade.hpp"
#include "../../../engine/core/canvas/Tile.hpp"

namespace py = pybind11;
using namespace aladyn::engine;

PYBIND11_MODULE(aladyn_engine_native, m) {
    m.doc() = "ALADYN ENGINE — Mini-Motores, Categorias de Receitas e UI Dinâmica";

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
    py::enum_<document::LayerBlendMode>(m, "LayerBlendMode")
        .value("Normal",   document::LayerBlendMode::Normal)
        .value("Multiply", document::LayerBlendMode::Multiply)
        .value("Screen",   document::LayerBlendMode::Screen)
        .value("Overlay",  document::LayerBlendMode::Overlay)
        .value("Darken",   document::LayerBlendMode::Darken)
        .value("Lighten",  document::LayerBlendMode::Lighten)
        .value("Erase",    document::LayerBlendMode::Erase)
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
        .def(py::init<stroke::PointerEventType, math::Point2D, double, double>(),
             py::arg("type"), py::arg("position"),
             py::arg("pressure") = 1.0, py::arg("timestamp") = 0.0)
        .def_readwrite("type",      &stroke::PointerEvent::type)
        .def_readwrite("position",  &stroke::PointerEvent::position)
        .def_readwrite("pressure",  &stroke::PointerEvent::pressure)
        .def_readwrite("timestamp", &stroke::PointerEvent::timestamp);

    py::class_<stroke::DynamicStabilizer>(m, "DynamicStabilizer")
        .def("set_stabilization_percentage", &stroke::DynamicStabilizer::setStabilizationPercentage)
        .def("get_stabilization_percentage", &stroke::DynamicStabilizer::getStabilizationPercentage)
        .def("reset", &stroke::DynamicStabilizer::reset);

    // ─── BRUSH TIP GEOMETRY ──────────────────────────────────────────────────
    py::class_<brush::BrushTip>(m, "BrushTip")
        .def(py::init<>())
        .def_readwrite("angle",           &brush::BrushTip::angle)
        .def_readwrite("aspect_ratio",    &brush::BrushTip::aspectRatio)
        .def_readwrite("follow_stroke",   &brush::BrushTip::followStroke)
        .def_readwrite("jitter_size",     &brush::BrushTip::jitterSize)
        .def_readwrite("jitter_angle",    &brush::BrushTip::jitterAngle)
        .def_readwrite("jitter_position", &brush::BrushTip::jitterPosition);

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
        .def_readwrite("canvas_texture_curve",    &canvas::CanvasTexture::canvasTextureCurve);

    // ─── TELEMETRY ────────────────────────────────────────────────────────────
    py::class_<boundary::TelemetryData>(m, "TelemetryData")
        .def_readonly("pressure",    &boundary::TelemetryData::pressure)
        .def_readonly("velocity",    &boundary::TelemetryData::velocity)
        .def_readonly("output_flow", &boundary::TelemetryData::outputFlow);

    // ─── ENGINE FACADE ────────────────────────────────────────────────────────
    py::class_<boundary::PaintEngineFacade>(m, "PaintEngineFacade")
        .def(py::init<int, int>())
        .def("resize_canvas", &boundary::PaintEngineFacade::resizeCanvas)
        .def("clear_canvas",  &boundary::PaintEngineFacade::clearCanvas)
        // Troca de motor em tempo real
        .def("set_engine_type",        &boundary::PaintEngineFacade::setEngineType)
        .def("get_active_engine_type", &boundary::PaintEngineFacade::getActiveEngineType)
        // Gerenciamento de Camadas e Grupos
        .def("add_layer",               &boundary::PaintEngineFacade::addLayer, py::arg("name") = "")
        .def("add_group",               &boundary::PaintEngineFacade::addGroup, py::arg("name") = "Novo Grupo")
        .def("add_filter_layer",        &boundary::PaintEngineFacade::addFilterLayer)
        .def("set_filter_params",       &boundary::PaintEngineFacade::setFilterParams)
        .def("get_filter_params",       &boundary::PaintEngineFacade::getFilterParams)
        .def("get_filter_type",         &boundary::PaintEngineFacade::getFilterType)
        .def("is_filter_layer",         &boundary::PaintEngineFacade::isFilterLayer)
        .def("is_group",                &boundary::PaintEngineFacade::isGroup)
        .def("set_group_pass_through",  &boundary::PaintEngineFacade::setGroupPassThrough)
        .def("remove_layer",            &boundary::PaintEngineFacade::removeLayer)
        .def("duplicate_layer",         &boundary::PaintEngineFacade::duplicateLayer)
        .def("select_layer",            &boundary::PaintEngineFacade::selectLayer)
        .def("reorder_layer",           &boundary::PaintEngineFacade::reorderLayer)
        .def("reorder_layers",          &boundary::PaintEngineFacade::reorderLayers)
        .def("set_layer_parents",       &boundary::PaintEngineFacade::setLayerParents)
        .def("set_layer_name",          &boundary::PaintEngineFacade::setLayerName)
        .def("set_layer_opacity",       &boundary::PaintEngineFacade::setLayerOpacity)
        .def("set_layer_blend_mode",    &boundary::PaintEngineFacade::setLayerBlendMode)
        .def("set_layer_visibility",        &boundary::PaintEngineFacade::setLayerVisibility)
        .def("set_layer_lock",              &boundary::PaintEngineFacade::setLayerLock)
        .def("set_layer_alpha_lock",        &boundary::PaintEngineFacade::setLayerAlphaLock)
        .def("is_layer_alpha_locked",      &boundary::PaintEngineFacade::isLayerAlphaLocked)
        .def("set_layer_clipping_mask",     &boundary::PaintEngineFacade::setLayerClippingMask)
        .def("is_layer_clipping_mask",     &boundary::PaintEngineFacade::isLayerClippingMask)
        .def("flatten_group",              &boundary::PaintEngineFacade::flattenGroup)
        .def("merge_layer_down",           &boundary::PaintEngineFacade::mergeLayerDown)
        .def("clear_layer",                &boundary::PaintEngineFacade::clearLayer)
        .def("set_background_visibility",   &boundary::PaintEngineFacade::setBackgroundVisibility)
        .def("is_background_visible",       &boundary::PaintEngineFacade::isBackgroundVisible)
        .def("set_background_color",        &boundary::PaintEngineFacade::setBackgroundColor, py::arg("r"), py::arg("g"), py::arg("b"), py::arg("a") = 255)
        .def("get_active_layer_index",      &boundary::PaintEngineFacade::getActiveLayerIndex)
        .def("get_drawing_layer_count",     &boundary::PaintEngineFacade::getDrawingLayerCount)
        .def("get_layer_info", [](boundary::PaintEngineFacade& self, int index) -> py::dict {
            py::dict d;
            if (const auto* l = self.getLayerStack().getDrawingLayer(index)) {
                d["name"] = l->getName(); d["opacity"] = l->getOpacity();
                d["visible"] = l->isVisible(); d["locked"] = l->isLocked();
                d["alpha_locked"] = l->isAlphaLocked(); d["clipping_mask"] = l->isClippingMask();
                d["blend_mode"] = static_cast<int>(l->getBlendMode());
                d["is_group"] = l->isGroup(); d["is_filter"] = l->isFilter();
            }
            return d;
        })
        // Traço
        .def("begin_stroke",     &boundary::PaintEngineFacade::beginStroke)
        .def("update_stroke",    &boundary::PaintEngineFacade::updateStroke)
        .def("end_stroke",       &boundary::PaintEngineFacade::endStroke)
        .def("begin_stroke_raw",  &boundary::PaintEngineFacade::beginStrokeRaw, py::arg("x"), py::arg("y"), py::arg("pressure") = 1.0)
        .def("update_stroke_raw", &boundary::PaintEngineFacade::updateStrokeRaw, py::arg("x"), py::arg("y"), py::arg("pressure") = 1.0)
        .def("end_stroke_raw",    &boundary::PaintEngineFacade::endStrokeRaw)
        // Preenchimento (Flood Fill / Balde de Tinta Nativo)
        .def("flood_fill", [](boundary::PaintEngineFacade& self, int seedX, int seedY, const raster::ColorRGBA& fillColor,
                              int tolerance, bool contiguous, int expandPx, int gapClosingPx, bool antiAliasing, bool sampleAllLayers) {
            return self.floodFill(seedX, seedY, fillColor, tolerance, contiguous, expandPx, gapClosingPx, antiAliasing, sampleAllLayers);
        }, py::arg("seed_x"), py::arg("seed_y"), py::arg("fill_color"),
           py::arg("tolerance") = 20, py::arg("contiguous") = true,
           py::arg("expand_px") = 1, py::arg("gap_closing_px") = 0,
           py::arg("anti_aliasing") = true, py::arg("sample_all_layers") = true)
        // Desfazer / Refazer
        .def("undo", &boundary::PaintEngineFacade::undo)
        .def("redo", &boundary::PaintEngineFacade::redo)
        .def("set_undo_memory_limit_mb", &boundary::PaintEngineFacade::setUndoMemoryLimitMB)
        .def("get_undo_memory_limit_mb", &boundary::PaintEngineFacade::getUndoMemoryLimitMB)
        .def("set_undo_max_steps", &boundary::PaintEngineFacade::setUndoMaxSteps)
        .def("get_undo_max_steps", &boundary::PaintEngineFacade::getUndoMaxSteps)
        // Texturas e presets
        .def("set_shape_preset", &boundary::PaintEngineFacade::setShapePreset)
        .def("set_brush_height_preset", &boundary::PaintEngineFacade::setBrushHeightPreset)
        .def("set_canvas_height_preset", &boundary::PaintEngineFacade::setCanvasHeightPreset)
        .def("load_shape_texture", [](boundary::PaintEngineFacade& self, int w, int h, py::bytes data) {
            std::string s = data;
            self.loadShapeTextureFromBuffer(w, h, reinterpret_cast<const uint8_t*>(s.data()));
        })
        .def("load_brush_height_texture", [](boundary::PaintEngineFacade& self, int w, int h, py::bytes data) {
            std::string s = data;
            self.loadBrushHeightTextureFromBuffer(w, h, reinterpret_cast<const uint8_t*>(s.data()));
        })
        .def("load_canvas_height_texture", [](boundary::PaintEngineFacade& self, int w, int h, py::bytes data) {
            std::string s = data;
            self.loadCanvasHeightTextureFromBuffer(w, h, reinterpret_cast<const uint8_t*>(s.data()));
        })
        // Preview buffers
        .def("get_shape_preview_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            const auto tex = self.getBrushProfile().shapeTexture;
            if (!tex) return py::none();
            return py::memoryview::from_memory(tex->getData(), (size_t)(tex->getWidth() * tex->getHeight()), true);
        })
        .def("get_shape_preview_dimensions", [](boundary::PaintEngineFacade& self) {
            const auto tex = self.getBrushProfile().shapeTexture;
            return tex ? std::make_pair(tex->getWidth(), tex->getHeight()) : std::make_pair(0, 0);
        })
        .def("get_brush_height_preview_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            const auto tex = self.getBrushProfile().brushHeightTexture;
            if (!tex) return py::none();
            return py::memoryview::from_memory(tex->getData(), (size_t)(tex->getWidth() * tex->getHeight()), true);
        })
        .def("get_brush_height_preview_dimensions", [](boundary::PaintEngineFacade& self) {
            const auto tex = self.getBrushProfile().brushHeightTexture;
            return tex ? std::make_pair(tex->getWidth(), tex->getHeight()) : std::make_pair(0, 0);
        })
        .def("get_canvas_height_preview_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            const auto tex = self.getCanvasTexture().canvasHeightTexture;
            if (!tex) return py::none();
            return py::memoryview::from_memory(tex->getData(), (size_t)(tex->getWidth() * tex->getHeight()), true);
        })
        .def("get_canvas_height_preview_dimensions", [](boundary::PaintEngineFacade& self) {
            const auto tex = self.getCanvasTexture().canvasHeightTexture;
            return tex ? std::make_pair(tex->getWidth(), tex->getHeight()) : std::make_pair(0, 0);
        })
        // Acesso ao estado
        .def("get_brush_profile",  [](boundary::PaintEngineFacade& self) -> brush::BrushProfile& {
            return self.getBrushProfile();
        }, py::return_value_policy::reference)
        .def("get_canvas_texture", [](boundary::PaintEngineFacade& self) -> canvas::CanvasTexture& {
            return self.getCanvasTexture();
        }, py::return_value_policy::reference)
        .def("get_stabilizer", [](boundary::PaintEngineFacade& self) -> stroke::DynamicStabilizer& {
            return self.getStabilizer();
        }, py::return_value_policy::reference)
        .def("get_width",  &boundary::PaintEngineFacade::getWidth)
        .def("get_height", &boundary::PaintEngineFacade::getHeight)
        .def("set_color_profile", &boundary::PaintEngineFacade::setColorProfile)
        .def("get_color_profile", &boundary::PaintEngineFacade::getColorProfile)
        .def("get_pixel_buffer", [](boundary::PaintEngineFacade& self) {
            return py::memoryview::from_memory(
                self.getRawPixelData(), self.getPixelDataSize(), true);
        })
        .def("get_display_pixel_buffer", [](boundary::PaintEngineFacade& self) {
            return py::memoryview::from_memory(
                self.getDisplayRawPixelData(), self.getDisplayPixelDataSize(), true);
        })
        // Seleção & Varinha Mágica
        .def("magic_wand_select", &boundary::PaintEngineFacade::magicWandSelect,
             py::arg("seed_x"), py::arg("seed_y"),
             py::arg("tolerance") = 20, py::arg("contiguous") = true,
             py::arg("expand_px") = 0, py::arg("anti_aliasing") = true,
             py::arg("mode") = 0, py::arg("sample_all_layers") = true)
        .def("select_rect", &boundary::PaintEngineFacade::selectRect,
             py::arg("x"), py::arg("y"), py::arg("w"), py::arg("h"),
             py::arg("mode") = 0, py::arg("feather_px") = 0, py::arg("corner_radius_px") = 0)
        .def("select_ellipse", &boundary::PaintEngineFacade::selectEllipse,
             py::arg("cx"), py::arg("cy"), py::arg("rx"), py::arg("ry"),
             py::arg("mode") = 0, py::arg("anti_aliasing") = true, py::arg("feather_px") = 0)
        .def("select_polygon", &boundary::PaintEngineFacade::selectPolygon,
             py::arg("flat_points"), py::arg("mode") = 0,
             py::arg("anti_aliasing") = true, py::arg("feather_px") = 0)
        .def("clear_selection", &boundary::PaintEngineFacade::clearSelection)
        .def("invert_selection", &boundary::PaintEngineFacade::invertSelection)
        .def("select_all", &boundary::PaintEngineFacade::selectAll)
        .def("has_selection", &boundary::PaintEngineFacade::hasSelection)
        .def("delete_selection_on_active_layer", &boundary::PaintEngineFacade::deleteSelectionOnActiveLayer)
        .def("fill_selection_on_active_layer", &boundary::PaintEngineFacade::fillSelectionOnActiveLayer, py::arg("fill_color"))
        .def("get_selection_mask_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            if (!self.hasSelection()) return py::none();
            return py::memoryview::from_memory(
                self.getSelectionMaskData(), self.getSelectionMaskSize(), true);
        })
        .def("get_selection_bounds", &boundary::PaintEngineFacade::getSelectionBounds)
        .def("get_selection_contour_segments", &boundary::PaintEngineFacade::getSelectionContourSegments)
        .def("get_selection_contour_loops", &boundary::PaintEngineFacade::getSelectionContourLoops)
        // Transform Tool bindings
        .def("begin_transform", &boundary::PaintEngineFacade::beginTransform)
        .def("is_transform_active", &boundary::PaintEngineFacade::isTransformActive)
        .def("get_transform_source_bounds", &boundary::PaintEngineFacade::getTransformSourceBounds)
        .def("get_transform_pivot", &boundary::PaintEngineFacade::getTransformPivot)
        .def("commit_transform", &boundary::PaintEngineFacade::commitTransform,
             py::arg("dx"), py::arg("dy"), py::arg("scale_x"), py::arg("scale_y"),
             py::arg("rotation_deg"), py::arg("pivot_x"), py::arg("pivot_y"),
             py::arg("flip_h") = false, py::arg("flip_v") = false, py::arg("interp_mode") = 2)
        .def("cancel_transform", &boundary::PaintEngineFacade::cancelTransform)
        .def("flip_active_layer", &boundary::PaintEngineFacade::flipActiveLayer, py::arg("horizontal"))
        .def("rotate_active_layer_90", &boundary::PaintEngineFacade::rotateActiveLayer90, py::arg("clockwise"))
        .def("get_transform_source_buffer_size", &boundary::PaintEngineFacade::getTransformSourceBufferSize)
        .def("get_transform_source_buffer", [](boundary::PaintEngineFacade& self) -> py::object {
            uint8_t* ptr = self.getTransformSourceBufferData();
            if (!ptr) return py::none();
            auto sz = self.getTransformSourceBufferSize();
            if (sz[0] <= 0 || sz[1] <= 0) return py::none();
            return py::memoryview::from_memory(ptr, static_cast<size_t>(sz[0] * sz[1] * 4), true);
        })
        // Miniatura de camada: lê os tiles do TileGrid e escalona para thumbW×thumbH (RGBA)
        .def("get_layer_thumbnail_buffer", [](boundary::PaintEngineFacade& self, int layerIdx, int thumbW, int thumbH) -> py::object {
            const auto* layer = self.getLayerStack().getDrawingLayer(layerIdx);
            if (!layer) return py::none();

            const auto& grid = layer->getTileGrid();
            int srcW = grid.getWidth();
            int srcH = grid.getHeight();
            if (srcW <= 0 || srcH <= 0 || thumbW <= 0 || thumbH <= 0) return py::none();

            // Buffer de saída RGBA (thumbW × thumbH)
            std::vector<uint8_t> out(static_cast<size_t>(thumbW * thumbH * 4), 0);

            float scaleX = static_cast<float>(srcW) / thumbW;
            float scaleY = static_cast<float>(srcH) / thumbH;

            for (int dy = 0; dy < thumbH; ++dy) {
                int sy = static_cast<int>(dy * scaleY);
                if (sy >= srcH) sy = srcH - 1;
                for (int dx = 0; dx < thumbW; ++dx) {
                    int sx = static_cast<int>(dx * scaleX);
                    if (sx >= srcW) sx = srcW - 1;

                    // Localiza o tile correspondente ao pixel (sx, sy)
                    int tileX = sx / canvas::Tile::TILE_SIZE;
                    int tileY = sy / canvas::Tile::TILE_SIZE;
                    int localX = sx % canvas::Tile::TILE_SIZE;
                    int localY = sy % canvas::Tile::TILE_SIZE;

                    const auto* tile = const_cast<canvas::TileGrid&>(grid).getTile(tileX, tileY);
                    raster::ColorRGBA px = tile ? tile->getBuffer().getPixel(localX, localY) : raster::ColorRGBA{0,0,0,0};

                    size_t outIdx = static_cast<size_t>((dy * thumbW + dx) * 4);
                    out[outIdx + 0] = px.r;
                    out[outIdx + 1] = px.g;
                    out[outIdx + 2] = px.b;
                    out[outIdx + 3] = px.a;
                }
            }
            return py::bytes(reinterpret_cast<const char*>(out.data()), out.size());
        })
        .def("paste_rgba_buffer_on_active_layer", [](boundary::PaintEngineFacade& self, int x, int y, int w, int h, py::bytes buffer, int blendMode, double opacity) {
            std::string s = buffer;
            return self.pasteRgbaBufferOnActiveLayer(x, y, w, h, reinterpret_cast<const uint8_t*>(s.data()), blendMode, opacity);
        }, py::arg("x"), py::arg("y"), py::arg("width"), py::arg("height"), py::arg("buffer"), py::arg("blend_mode_id") = 0, py::arg("opacity") = 1.0)
        // Métodos de Simetria & Guias
        .def("set_symmetry_config", &boundary::PaintEngineFacade::setSymmetryConfig,
             py::arg("mode"), py::arg("cx"), py::arg("cy"), py::arg("angle_rad"),
             py::arg("segments") = 6, py::arg("stop_at_center") = false)
        .def("clear_symmetry", &boundary::PaintEngineFacade::clearSymmetry)
        .def("set_guide_config", &boundary::PaintEngineFacade::setGuideConfig,
             py::arg("type"),
             py::arg("p0x") = 0.0, py::arg("p0y") = 0.0,
             py::arg("p1x") = 100.0, py::arg("p1y") = 100.0,
             py::arg("p2x") = 200.0, py::arg("p2y") = 200.0,
             py::arg("p3x") = 300.0, py::arg("p3y") = 300.0,
             py::arg("vp_ax") = 400.0, py::arg("vp_ay") = 300.0,
             py::arg("vp_bx") = -1000.0, py::arg("vp_by") = 300.0,
             py::arg("vp_cx") = 400.0, py::arg("vp_cy") = -2000.0,
             py::arg("cx") = 0.0, py::arg("cy") = 0.0,
             py::arg("fov") = 130.0, py::arg("pitch") = 0.0, py::arg("yaw") = 0.0,
             py::arg("snap_radius") = 32.0)
        .def("clear_guide", &boundary::PaintEngineFacade::clearGuide)
        .def("snap_point", &boundary::PaintEngineFacade::snapPoint,
             py::arg("raw_x"), py::arg("raw_y"),
             py::arg("last_x") = 0.0, py::arg("last_y") = 0.0,
             py::arg("has_last") = false);
}
