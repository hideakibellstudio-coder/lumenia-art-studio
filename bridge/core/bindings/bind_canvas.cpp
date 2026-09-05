#include "BindingsCommon.hpp"

namespace aladyn::bridge {

using namespace aladyn::engine;

void bind_canvas(py::module_& /*m*/, FacadeClass& facade) {
    facade
        .def("resize_canvas", &boundary::PaintEngineFacade::resizeCanvas)
        .def("clear_canvas",  &boundary::PaintEngineFacade::clearCanvas)
        .def("get_width",     &boundary::PaintEngineFacade::getWidth)
        .def("get_height",    &boundary::PaintEngineFacade::getHeight)
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
        .def("clear_dirty_tiles", &boundary::PaintEngineFacade::clearDirtyTiles);
}

} // namespace aladyn::bridge
