#include "BindingsCommon.hpp"
#include "BufferContract.hpp"
#include "../../../engine/core/color/ColorProfile.hpp"

namespace aladyn::bridge {

using namespace aladyn::engine;

void bind_canvas(py::module_& /*m*/, FacadeClass& facade) {
    facade
        .def("resize_canvas", &boundary::PaintEngineFacade::resizeCanvas)
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
        .def("transform_rgba_for_profile", [](boundary::PaintEngineFacade&, py::bytes buffer, int profileId) {
            if (!color::ColorProfileManager::isProfileValid(profileId)) {
                throw py::value_error("Unknown color profile");
            }
            std::string source = buffer;
            if (source.size() % 4 != 0) {
                throw py::value_error("RGBA input length must be a multiple of four");
            }
            const size_t pixels = source.size() / 4;
            if (pixels > static_cast<size_t>(std::numeric_limits<int>::max())) {
                throw py::value_error("RGBA input is too large");
            }
            std::string transformed = source;
            color::ColorProfileManager::transformBuffer(
                reinterpret_cast<const uint8_t*>(source.data()),
                reinterpret_cast<uint8_t*>(transformed.data()),
                static_cast<int>(pixels),
                static_cast<color::ColorProfileType>(profileId)
            );
            return py::bytes(transformed);
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
        .def("refresh_display", [](boundary::PaintEngineFacade& self) {
            // Refresh composition without allocating a discarded Python snapshot.
            [[maybe_unused]] const auto* display = self.getDisplayRawPixelData();
        })
        .def("get_display_pixel_buffer", [](boundary::PaintEngineFacade& self) {
            return pixelSnapshot(self.getDisplayRawPixelData(), self.getDisplayPixelDataSize());
        })
        .def("get_layer_pixel_buffer", [](boundary::PaintEngineFacade& self, int layerIdx) -> py::object {
            auto data = self.getLayerPixelBuffer(layerIdx);
            if (data.empty()) return py::none();
            return py::bytes(reinterpret_cast<const char*>(data.data()), data.size());
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
            std::vector<uint8_t> out(checkedRasterBytes(thumbW, thumbH, 4), 0);

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
