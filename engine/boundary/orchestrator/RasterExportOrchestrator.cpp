#include "RasterExportOrchestrator.hpp"

#include "../../core/color/ColorProfile.hpp"
#include <algorithm>
#include <cstring>
#include <limits>
#include <stdexcept>

namespace aladyn::engine::boundary::orchestrator {

std::vector<uint8_t> RasterExportOrchestrator::getLayerPixelBuffer(
    const document::LayerStack& stack, int layerIndex, int width, int height
) {
    const auto* layer = stack.getDrawingLayer(layerIndex);
    if (!layer || layer->isGroup() || layer->isFilter()) return {};

    std::vector<uint8_t> out(static_cast<size_t>(width) * static_cast<size_t>(height) * 4u, 0u);
    const auto& grid = layer->getTileGrid();
    grid.forEachTile([&](const canvas::TileIndex&, const canvas::Tile& tile) {
        const auto& src = tile.getBuffer();
        const int baseX = tile.getPixelX();
        const int baseY = tile.getPixelY();
        const int minX = std::max(0, baseX);
        const int minY = std::max(0, baseY);
        const int maxX = std::min(width, baseX + canvas::Tile::TILE_SIZE);
        const int maxY = std::min(height, baseY + canvas::Tile::TILE_SIZE);
        if (minX >= maxX || minY >= maxY) return;

        const auto* srcData = reinterpret_cast<const uint8_t*>(src.getData());
        for (int y = minY; y < maxY; ++y) {
            const int localY = y - baseY;
            for (int x = minX; x < maxX; ++x) {
                const int localX = x - baseX;
                const size_t srcOffset = static_cast<size_t>(localY * canvas::Tile::TILE_SIZE + localX) * 4u;
                const size_t dstOffset = static_cast<size_t>(y * width + x) * 4u;
                std::memcpy(out.data() + dstOffset, srcData + srcOffset, 4u);
            }
        }
    });
    return out;
}

std::vector<uint8_t> RasterExportOrchestrator::getLayerThumbnailBuffer(
    const document::LayerStack& stack, int layerIdx, int thumbW, int thumbH
) {
    const auto* layer = stack.getDrawingLayer(layerIdx);
    if (!layer) return {};

    const auto& grid = layer->getTileGrid();
    int srcW = grid.getWidth();
    int srcH = grid.getHeight();
    if (srcW <= 0 || srcH <= 0 || thumbW <= 0 || thumbH <= 0) return {};

    const size_t expectedBytes = static_cast<size_t>(thumbW) * static_cast<size_t>(thumbH) * 4;
    std::vector<uint8_t> out(expectedBytes, 0);

    float scaleX = static_cast<float>(srcW) / thumbW;
    float scaleY = static_cast<float>(srcH) / thumbH;

    for (int dy = 0; dy < thumbH; ++dy) {
        int sy = static_cast<int>(dy * scaleY);
        if (sy >= srcH) sy = srcH - 1;
        for (int dx = 0; dx < thumbW; ++dx) {
            int sx = static_cast<int>(dx * scaleX);
            if (sx >= srcW) sx = srcW - 1;

            int tileX = sx / canvas::Tile::TILE_SIZE;
            int tileY = sy / canvas::Tile::TILE_SIZE;
            int localX = sx % canvas::Tile::TILE_SIZE;
            int localY = sy % canvas::Tile::TILE_SIZE;

            const auto* tile = const_cast<canvas::TileGrid&>(grid).getTile(tileX, tileY);
            utils::ColorRGBA px = tile ? tile->getBuffer().getPixel(localX, localY) : utils::ColorRGBA{0, 0, 0, 0};

            size_t outIdx = static_cast<size_t>((dy * thumbW + dx) * 4);
            out[outIdx + 0] = px.r;
            out[outIdx + 1] = px.g;
            out[outIdx + 2] = px.b;
            out[outIdx + 3] = px.a;
        }
    }
    return out;
}

std::string RasterExportOrchestrator::transformRgbaForProfile(const std::string& buffer, int profileId) {
    if (!color::ColorProfileManager::isProfileValid(profileId)) {
        throw std::invalid_argument("Unknown color profile");
    }
    if (buffer.size() % 4 != 0) {
        throw std::invalid_argument("RGBA input length must be a multiple of four");
    }
    const size_t pixels = buffer.size() / 4;
    if (pixels > static_cast<size_t>(std::numeric_limits<int>::max())) {
        throw std::invalid_argument("RGBA input is too large");
    }
    std::string transformed = buffer;
    color::ColorProfileManager::transformBuffer(
        reinterpret_cast<const uint8_t*>(buffer.data()),
        reinterpret_cast<uint8_t*>(transformed.data()),
        static_cast<int>(pixels),
        static_cast<color::ColorProfileType>(profileId)
    );
    return transformed;
}

void RasterExportOrchestrator::applyColorProfile(uint8_t* targetBuffer, size_t numPixels, int colorProfileId) noexcept {
    if (!targetBuffer || numPixels == 0 || numPixels > static_cast<size_t>(std::numeric_limits<int>::max())) return;
    color::ColorProfileManager::transformBuffer(
        targetBuffer,
        targetBuffer,
        static_cast<int>(numPixels),
        static_cast<color::ColorProfileType>(colorProfileId)
    );
}

uint8_t* RasterExportOrchestrator::resolveDisplayBuffer(
    int colorProfileId, canvas::PixelBuffer& outputBuffer, canvas::PixelBuffer& displayBuffer
) {
    if (colorProfileId == 0) return outputBuffer.getData();
    const size_t totalBytes = outputBuffer.getSizeInBytes();
    std::memcpy(displayBuffer.getData(), outputBuffer.getData(), totalBytes);
    applyColorProfile(displayBuffer.getData(), totalBytes / 4, colorProfileId);
    return displayBuffer.getData();
}

void RasterExportOrchestrator::copyBufferRegion(
    const uint8_t* src, int srcW, int srcH,
    int x, int y, int w, int h, uint8_t* dst, size_t dstSize
) {
    if (w <= 0 || h <= 0 || x < 0 || y < 0 || x > srcW - w || y > srcH - h) {
        throw std::invalid_argument("Display region lies outside the canvas");
    }
    const size_t rowBytes = static_cast<size_t>(w) * 4u;
    if (!src || !dst || dstSize != rowBytes * static_cast<size_t>(h)) {
        throw std::invalid_argument("Display region buffer does not match the region size");
    }
    const size_t srcRowBytes = static_cast<size_t>(srcW) * 4u;
    for (int row = 0; row < h; ++row) {
        std::memcpy(
            dst + static_cast<size_t>(row) * rowBytes,
            src + static_cast<size_t>(y + row) * srcRowBytes + static_cast<size_t>(x) * 4u,
            rowBytes);
    }
}

void RasterExportOrchestrator::copyDisplayRegion(
    int colorProfileId, const canvas::PixelBuffer& outputBuffer,
    int x, int y, int w, int h, uint8_t* dst, size_t dstSize
) {
    copyBufferRegion(outputBuffer.getData(), outputBuffer.getWidth(), outputBuffer.getHeight(), x, y, w, h, dst, dstSize);
    if (colorProfileId != 0) applyColorProfile(dst, static_cast<size_t>(w) * static_cast<size_t>(h), colorProfileId);
}

} // namespace aladyn::engine::boundary::orchestrator
