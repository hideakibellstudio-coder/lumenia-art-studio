#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "../../../engine/boundary/public-api/PaintEngineFacade.hpp"
#include "../../../engine/core/canvas/Tile.hpp"
#include "../../../engine/core/color/ColorProfile.hpp"

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
        .value("Linear",    math::CurvePreset::Linear)
        .value("Soft",      math::CurvePreset::Soft)
        .value("Hard",      math::CurvePreset::Hard)
        .value("S",         math::CurvePreset::S)
        .value("Threshold", math::CurvePreset::Threshold)
        .export_values();

    py::class_<math::BezierCurve>(m, "BezierCurve")
        .def(py::init<>())
        .def(py::init<math::CurvePreset>())
        .def("set_control_points", &math::BezierCurve::setControlPoints)
        .def("set_preset", &math::BezierCurve::setPreset)
        .def("invert",     &math::BezierCurve::invert)
        .def("sample",     &math::BezierCurve::sample);

    // ─── ENGINE TYPE (CATEGORIAS DE MOTOR) ───────────────────────────────────
    py::enum_<brush::EngineType>(m, "EngineType")
        .value("Brush",      brush::EngineType::Brush)
        .value("Pencil",     brush::EngineType::Pencil)
        .value("Inker",      brush::EngineType::Inker)
        .value("Eraser",     brush::EngineType::Eraser)
        .value("Marker",     brush::EngineType::Marker)
        .value("Blur",       brush::EngineType::Blur)
        .value("Smudge",     brush::EngineType::Smudge)
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

    // ─── COLOR PROFILE TYPE (PERFIS DE COR & PROVA DE CORES) ─────────────────
    py::enum_<color::ColorProfileType>(m, "ColorProfileType")
        .value("Default_sRGB",             color::ColorProfileType::Default_sRGB)
        .value("Display_P3",               color::ColorProfileType::Display_P3)
        .value("Generic_CMYK",             color::ColorProfileType::Generic_CMYK)
        .value("US_SWOP_Web_Coated_v2",    color::ColorProfileType::US_SWOP_Web_Coated_v2)
        .value("US_SWOP_Web_Coated_G3",    color::ColorProfileType::US_SWOP_Web_Coated_G3)
        .value("US_SWOP_Web_Coated_G5",    color::ColorProfileType::US_SWOP_Web_Coated_G5)
        .value("US_GRACOL_Coated_2006",    color::ColorProfileType::US_GRACOL_Coated_2006)
        .value("US_SWOP_Web_Uncoated_v2",  color::ColorProfileType::US_SWOP_Web_Uncoated_v2)
        .value("Europe_FOGRA39_Coated",    color::ColorProfileType::Europe_FOGRA39_Coated)
        .value("Euroscale_Coated_v2",      color::ColorProfileType::Euroscale_Coated_v2)
        .value("Euroscale_Uncoated_v2",    color::ColorProfileType::Euroscale_Uncoated_v2)
        .value("Japan_Coated_2011",        color::ColorProfileType::Japan_Coated_2011)
        .value("Generic_Grayscale",        color::ColorProfileType::Generic_Grayscale)
        .value("Line_Art_HighContrast",    color::ColorProfileType::Line_Art_HighContrast)
        .value("ColorBlindness_Protanopia",   color::ColorProfileType::ColorBlindness_Protanopia)
        .value("ColorBlindness_Deuteranopia", color::ColorProfileType::ColorBlindness_Deuteranopia)
        .value("ColorBlindness_Tritanopia",   color::ColorProfileType::ColorBlindness_Tritanopia)
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
        .def("get_stabilization_percentage", &stroke::DynamicStabilizer::getStabilizationPercentage);

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
            const auto* layer = self.getLayerStack().getDrawingLayer(index);
            if (layer) {
                d["name"] = layer->getName();
                d["opacity"] = layer->getOpacity();
                d["visible"] = layer->isVisible();
                d["locked"] = layer->isLocked();
                d["alpha_locked"] = layer->isAlphaLocked();
                d["clipping_mask"] = layer->isClippingMask();
                d["blend_mode"] = static_cast<int>(layer->getBlendMode());
                d["is_group"] = layer->isGroup();
                d["is_filter"] = layer->isFilter();
            }
            return d;
        })
        // Traço
        .def("begin_stroke",  &boundary::PaintEngineFacade::beginStroke)
        .def("update_stroke", &boundary::PaintEngineFacade::updateStroke)
        .def("end_stroke",    &boundary::PaintEngineFacade::endStroke)
        // Desfazer / Refazer
        .def("undo",          &boundary::PaintEngineFacade::undo)
        .def("redo",          &boundary::PaintEngineFacade::redo)
        // Texturas e presets
        .def("set_shape_preset",         &boundary::PaintEngineFacade::setShapePreset)
        .def("set_brush_height_preset",  &boundary::PaintEngineFacade::setBrushHeightPreset)
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
        .def("get_pixel_buffer", [](boundary::PaintEngineFacade& self) {
            return py::memoryview::from_memory(
                self.getRawPixelData(), self.getPixelDataSize(), true);
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
        .def("get_undo_memory_bytes", &boundary::PaintEngineFacade::getUndoMemoryBytes)
        .def("set_max_undo_memory_mb", &boundary::PaintEngineFacade::setMaxUndoMemoryMB)
        // Amostragem de Cores (Eyedropper)
        .def("pick_color_merged", [](const boundary::PaintEngineFacade& self, int x, int y, int sampleRadius) {
            auto arr = self.pickColorMerged(x, y, sampleRadius);
            return py::make_tuple(arr[0], arr[1], arr[2], arr[3]);
        }, py::arg("x"), py::arg("y"), py::arg("sample_radius") = 0)
        .def("pick_color_layer", [](const boundary::PaintEngineFacade& self, int layerIndex, int x, int y, int sampleRadius) {
            auto arr = self.pickColorLayer(layerIndex, x, y, sampleRadius);
            return py::make_tuple(arr[0], arr[1], arr[2], arr[3]);
        }, py::arg("layer_index"), py::arg("x"), py::arg("y"), py::arg("sample_radius") = 0)
        // Gerenciamento de Perfis de Cor (Color Profiles & Soft-Proofing)
        .def("set_color_profile", [](boundary::PaintEngineFacade& self, int profileId) {
            self.setColorProfile(profileId);
        })
        .def("get_color_profile", &boundary::PaintEngineFacade::getColorProfile)
        .def("get_color_profile_name", &boundary::PaintEngineFacade::getColorProfileName);

    // ─── CATÁLOGO DE PERFIS DE COR DISPONÍVEIS ──────────────────────────────
    m.def("get_available_color_profiles", []() {
        py::list result;
        for (const auto& p : color::ColorProfileManager::getAvailableProfiles()) {
            py::dict item;
            item["id"]          = static_cast<int>(p.type);
            item["name"]        = p.name;
            item["category"]    = p.category;
            item["description"] = p.description;
            result.append(item);
        }
        return result;
    });

    // ─── RENDERIZADOR DE PREVIEW DO TRAÇO EM ALTA FIDELIDADE ─────────────────
    m.def("render_stroke_preview", [](const brush::BrushProfile& profile, int width, int height) -> py::bytes {
        auto vec = boundary::PaintEngineFacade::renderStrokePreview(profile, width, height);
        return py::bytes(reinterpret_cast<const char*>(vec.data()), vec.size());
    }, py::arg("profile"), py::arg("width") = 260, py::arg("height") = 52);
}
