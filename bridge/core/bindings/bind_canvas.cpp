#include "BindingsCommon.hpp"
#include "../../infrastructure/BufferContract.hpp"

namespace aladyn::bridge {

using namespace aladyn::engine;

void bind_canvas(py::module_& /*m*/, FacadeClass& facade) {
    facade
        .def("resize_canvas", &boundary::PaintEngineFacade::resizeCanvas)
        .def_static("max_canvas_dimension", [](int pixelFormat) {
            return canvas::maxCanvasDimension(static_cast<canvas::PixelFormat>(checkedPixelFormatId(pixelFormat)));
        }, py::arg("pixel_format") = 0)
        .def("get_pixel_format", [](boundary::PaintEngineFacade& self) {
            return static_cast<int>(self.getLayerStack().getPixelFormat());
        })
        .def("clear_canvas",  &boundary::PaintEngineFacade::clearCanvas)
        .def("get_width",     &boundary::PaintEngineFacade::getWidth)
        .def("get_height",    &boundary::PaintEngineFacade::getHeight)
        .def("get_document_generation", &boundary::PaintEngineFacade::getDocumentGeneration)
        .def("get_canvas_height_texture", [](boundary::PaintEngineFacade& self) -> py::object {
            const auto& texture = self.getCanvasTexture().canvasHeightTexture;
            if (!texture) return py::none();
            const int w = texture->getWidth(), h = texture->getHeight();
            return py::make_tuple(w, h, pixelSnapshot(texture->getData(), checkedRasterBytes(w, h, 1)));
        })
        .def("set_color_profile", &boundary::PaintEngineFacade::setColorProfile)
        .def("get_color_profile", &boundary::PaintEngineFacade::getColorProfile)
        .def("get_available_color_profiles", [](boundary::PaintEngineFacade&) {
            py::list result;
            for (const auto& profile : color::ColorProfileManager::getAvailableProfiles()) {
                py::dict item;
                item["id"] = static_cast<int>(profile.type);
                item["name"] = profile.name;
                item["category"] = profile.category;
                item["description"] = profile.description;
                item["gamut"] = profile.gamut;
                item["whitepoint"] = profile.whitepoint;
                item["transfer"] = profile.transfer;
                result.append(std::move(item));
            }
            return result;
        })
        .def("transform_rgba_for_profile", [](boundary::PaintEngineFacade& self, py::bytes buffer, int profileId) {
            // std::invalid_argument do motor vira ValueError (bridge/infrastructure/README.md).
            return py::bytes(self.transformRgbaForProfile(buffer, profileId));
        }, py::arg("buffer"), py::arg("profile_id"))
        .def("set_low_latency", &boundary::PaintEngineFacade::setLowLatency)
        .def("get_low_latency", &boundary::PaintEngineFacade::getLowLatency)
        .def("set_linear_gamma", &boundary::PaintEngineFacade::setLinearGamma)
        .def("get_linear_gamma", &boundary::PaintEngineFacade::getLinearGamma)
        .def("set_deep_color", &boundary::PaintEngineFacade::setDeepColor)
        .def("get_deep_color", &boundary::PaintEngineFacade::getDeepColor)
        .def("set_render_options", &boundary::PaintEngineFacade::setRenderOptions,
             py::arg("low_latency"), py::arg("linear_gamma"), py::arg("deep_color"))
        .def("get_pixel_buffer", [](boundary::PaintEngineFacade& self) {
            return pixelSnapshot(self.getRawPixelData(), self.getPixelDataSize());
        })
        .def("refresh_display", [](boundary::PaintEngineFacade&) {
            // Nada a fazer: o motor só compõe o que alguém lê (get_display_region, a pirâmide, get_pixel_buffer),
            // e cada leitor recompõe os tiles velhos da área que lê. A tela chama isto a cada evento de câmera;
            // até 2026-10-03 isto resolvia o buffer de exibição inteiro (100 a 175 ms em 4096² com perfil de cor
            // que não é sRGB) para a tela depois pedir só a janela.
        })
        .def("get_display_pixel_buffer", [](boundary::PaintEngineFacade& self) {
            return pixelSnapshot(self.getDisplayRawPixelData(), self.getDisplayPixelDataSize());
        })
        .def("get_display_region", [](boundary::PaintEngineFacade& self, int x, int y, int w, int h) {
            // One copy, straight into the Python bytes: the screen asks for the rectangle it paints.
            return filledBytes(checkedRasterBytes(w, h, 4), [&](uint8_t* dst, size_t size) {
                self.copyDisplayRegion(x, y, w, h, dst, size);
            });
        }, py::arg("x"), py::arg("y"), py::arg("width"), py::arg("height"))
        .def("get_display_lod_region", [](boundary::PaintEngineFacade& self, int level, int x, int y, int w, int h) {
            // The same for a level of the zoomed-out pyramid, which is refreshed only where it changed.
            return filledBytes(checkedRasterBytes(w, h, 4), [&](uint8_t* dst, size_t size) {
                self.copyDisplayLodRegion(level, x, y, w, h, dst, size);
            });
        }, py::arg("level"), py::arg("x"), py::arg("y"), py::arg("width"), py::arg("height"))
        .def("get_lod_size", [](boundary::PaintEngineFacade& self, int level) {
            int w = 0, h = 0;
            self.getLodSize(level, w, h);
            return py::make_tuple(w, h);
        }, py::arg("level"))
        .def("get_composite_pixel_buffer16", [](boundary::PaintEngineFacade& self) {
            // The whole composite of a 16-bit document, 8 bytes a pixel (RuntimeError in an 8-bit one).
            const int w = self.getWidth(), h = self.getHeight();
            return filledBytes(checkedRasterBytes(w, h, 8), [&](uint8_t* dst, size_t size) {
                self.copyComposite16(0, 0, w, h, dst, size);
            });
        })
        .def("get_composite_region16", [](boundary::PaintEngineFacade& self, int x, int y, int w, int h) {
            return filledBytes(checkedRasterBytes(w, h, 8), [&](uint8_t* dst, size_t size) {
                self.copyComposite16(x, y, w, h, dst, size);
            });
        }, py::arg("x"), py::arg("y"), py::arg("width"), py::arg("height"))
        .def("get_layer_pixel_buffer16", [](boundary::PaintEngineFacade& self, int layerIdx) {
            // One layer at the size of the canvas, 8 bytes a pixel; ValueError for a layer that holds no 16-bit pixels.
            const int w = self.getWidth(), h = self.getHeight();
            return filledBytes(checkedRasterBytes(w, h, 8), [&](uint8_t* dst, size_t size) {
                self.copyLayer16(layerIdx, dst, size);
            });
        }, py::arg("layer_index"))
        .def("get_layer_pixel_buffer", [](boundary::PaintEngineFacade& self, int layerIdx) -> py::object {
            auto data = self.getLayerPixelBuffer(layerIdx);
            if (data.empty()) return py::none();
            return py::bytes(reinterpret_cast<const char*>(data.data()), data.size());
        })
        .def("get_layer_thumbnail_buffer", [](boundary::PaintEngineFacade& self, int layerIdx, int thumbW, int thumbH) -> py::object {
            // thumbW/thumbH nao eram validados antes de alocar — dimensoes
            // absurdas (ex.: 2**30) causavam uma tentativa de alocacao de
            // dezenas de GB em vez de um ValueError. Mesmo guard usado pelos
            // outros acessores de buffer deste arquivo (checkedRasterBytes).
            checkedRasterBytes(thumbW, thumbH, 4);
            auto out = self.getLayerThumbnailBuffer(layerIdx, thumbW, thumbH);
            if (out.empty()) return py::none();
            return py::bytes(reinterpret_cast<const char*>(out.data()), out.size());
        })
        .def("paste_rgba_buffer_on_active_layer", [](boundary::PaintEngineFacade& self, int x, int y, int w, int h, py::bytes buffer, int blendMode, double opacity) {
            std::string s = buffer;
            validateRasterInput(s, w, h, 4);
            if (x > std::numeric_limits<int>::max() - w || y > std::numeric_limits<int>::max() - h) {
                throw py::value_error("Paste bounds overflow raster coordinates");
            }
            return self.pasteRgbaBufferOnActiveLayer(x, y, w, h, reinterpret_cast<const uint8_t*>(s.data()), blendMode, opacity);
        }, py::arg("x"), py::arg("y"), py::arg("width"), py::arg("height"), py::arg("buffer"), py::arg("blend_mode_id") = 0, py::arg("opacity") = 1.0)
        // ─── FASE 4: MEMÓRIA & SCRATCH DISK ─────────────────────────
        .def("compress_inactive_layers", &boundary::PaintEngineFacade::compressInactiveLayers)
        .def("decompress_all_layers", &boundary::PaintEngineFacade::decompressAllLayers)
        .def("get_total_tile_memory_mb", &boundary::PaintEngineFacade::getTotalTileMemoryMB)
        .def("get_cow_shared_tiles_count", &boundary::PaintEngineFacade::getCowSharedTilesCount)
        .def("set_scratch_disk_enabled", &boundary::PaintEngineFacade::setScratchDiskEnabled)
        .def("is_scratch_disk_enabled", &boundary::PaintEngineFacade::isScratchDiskEnabled)
        .def("get_undo_paged_steps_count", &boundary::PaintEngineFacade::getUndoPagedStepsCount)
        .def("get_scratch_disk_usage_mb", &boundary::PaintEngineFacade::getScratchDiskUsageMB)
        // ─── FASE 5: VIEWPORT & DIRTY TILE STREAMING ─────────────────
        .def("get_dirty_tile_indices", &boundary::PaintEngineFacade::getDirtyTileIndices)
        .def("clear_dirty_tiles", &boundary::PaintEngineFacade::clearDirtyTiles)
        // ─── VIEWPORT MIPMAPPING & LOD ANTI-ALIASING ──────────────────
        .def("get_display_pixel_buffer_lod", [](boundary::PaintEngineFacade& self, int level) -> py::object {
            int outW = 0, outH = 0;
            uint8_t* ptr = self.getDisplayPixelBufferLOD(level, outW, outH);
            if (!ptr || outW <= 0 || outH <= 0) return py::none();
            auto snapshot = pixelSnapshot(ptr, checkedRasterBytes(outW, outH, 4));
            double scale = boundary::PaintEngineFacade::getLODScale(level);
            return py::make_tuple(snapshot, outW, outH, scale);
        })
        .def("get_best_lod_level", [](boundary::PaintEngineFacade&, double zoom) {
            return boundary::PaintEngineFacade::getBestLODLevel(zoom);
        })
        .def_static("calculate_best_lod_level", &boundary::PaintEngineFacade::getBestLODLevel)
        .def("get_lod_scale", [](boundary::PaintEngineFacade&, int level) {
            return boundary::PaintEngineFacade::getLODScale(level);
        })
        .def_static("calculate_lod_scale", &boundary::PaintEngineFacade::getLODScale)
        .def("mark_lod_dirty", &boundary::PaintEngineFacade::markLODDirty);
}

} // namespace aladyn::bridge
