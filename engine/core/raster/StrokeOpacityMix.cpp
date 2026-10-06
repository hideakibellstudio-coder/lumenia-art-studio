#include "StrokeOpacityMix.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include <algorithm>
#include <cmath>
#include <cstring>

namespace aladyn::engine::raster {

namespace {

constexpr double kInv255 = 1.0 / 255.0;
constexpr double kInv65535 = 1.0 / 65535.0;

uint8_t roundToByte(double value) noexcept {
    return static_cast<uint8_t>(std::clamp(std::lround(value), 0L, 255L));
}

uint16_t roundToWord(double value) noexcept {
    return static_cast<uint16_t>(std::clamp(std::lround(value), 0L, 65535L));
}

// base + (trabalho - base) * opacidade, em alfa pré-multiplicado, com cor reta na saída.
utils::ColorRGBA mixPixel(utils::ColorRGBA base, utils::ColorRGBA work, double opacity) noexcept {
    const double baseAlpha = static_cast<double>(base.a);
    const double workAlpha = static_cast<double>(work.a);
    const double alpha = baseAlpha + (workAlpha - baseAlpha) * opacity;
    if (alpha <= 0.0) return base.a == 0 ? base : utils::ColorRGBA{0, 0, 0, 0};

    const auto channel = [&](uint8_t b, uint8_t w) {
        const double premultBase = static_cast<double>(b) * baseAlpha * kInv255;
        const double premultWork = static_cast<double>(w) * workAlpha * kInv255;
        const double premult = premultBase + (premultWork - premultBase) * opacity;
        return roundToByte(premult * 255.0 / alpha);
    };
    return utils::ColorRGBA{channel(base.r, work.r), channel(base.g, work.g), channel(base.b, work.b), roundToByte(alpha)};
}

utils::ColorRGBA16 mixPixel16(utils::ColorRGBA16 base, utils::ColorRGBA16 work, double opacity) noexcept {
    const double baseAlpha = static_cast<double>(base.a);
    const double workAlpha = static_cast<double>(work.a);
    const double alpha = baseAlpha + (workAlpha - baseAlpha) * opacity;
    if (alpha <= 0.0) return base.a == 0 ? base : utils::ColorRGBA16{0, 0, 0, 0};

    const auto channel = [&](uint16_t b, uint16_t w) {
        const double premultBase = static_cast<double>(b) * baseAlpha * kInv65535;
        const double premultWork = static_cast<double>(w) * workAlpha * kInv65535;
        const double premult = premultBase + (premultWork - premultBase) * opacity;
        return roundToWord(premult * 65535.0 / alpha);
    };
    return utils::ColorRGBA16{channel(base.r, work.r), channel(base.g, work.g), channel(base.b, work.b), roundToWord(alpha)};
}

} // namespace

void StrokeOpacityMix::begin(const canvas::TileGrid& layerGrid, double opacity, int layerIndex) {
    m_base = std::make_unique<canvas::TileGrid>(layerGrid.getWidth(), layerGrid.getHeight(), layerGrid.getFormat());
    m_base->copyFrom(layerGrid);
    m_work = std::make_unique<canvas::TileGrid>(layerGrid.getWidth(), layerGrid.getHeight(), layerGrid.getFormat());
    m_work->copyFrom(layerGrid);
    m_opacity = std::clamp(opacity, 0.0, 1.0);
    m_layerIndex = layerIndex;
}

void StrokeOpacityMix::end() noexcept {
    m_work.reset();
    m_base.reset();
    m_layerIndex = -1;
}

void StrokeOpacityMix::mergeInto(canvas::TileGrid& layerGrid, int firstTileX, int firstTileY, int lastTileX, int lastTileY) {
    if (!active()) return;
    const bool is16 = layerGrid.getFormat() == canvas::PixelFormat::RGBA16;
    constexpr size_t kPixels = static_cast<size_t>(canvas::Tile::TILE_SIZE) * canvas::Tile::TILE_SIZE;
    for (int ty = std::max(0, firstTileY); ty <= std::min(lastTileY, m_work->getTilesCountY() - 1); ++ty) {
        for (int tx = std::max(0, firstTileX); tx <= std::min(lastTileX, m_work->getTilesCountX() - 1); ++tx) {
            canvas::Tile* workTile = m_work->getTile(tx, ty);
            if (!workTile) continue;
            const canvas::Tile* baseTile = m_base->getTile(tx, ty);
            if (baseTile && baseTile->getSharedBuffer() == workTile->getSharedBuffer()) continue;  // intocado

            canvas::Tile* layerTile = layerGrid.getOrCreateTile(tx, ty);
            layerTile->setDirty(true);

            if (is16) {
                const auto* workData = reinterpret_cast<const utils::ColorRGBA16*>(static_cast<const canvas::Tile*>(workTile)->getBuffer().getData());
                const auto* baseData = baseTile ? reinterpret_cast<const utils::ColorRGBA16*>(baseTile->getBuffer().getData()) : nullptr;
                auto* out = reinterpret_cast<utils::ColorRGBA16*>(layerTile->getBuffer().getData());
                for (size_t i = 0; i < kPixels; ++i) {
                    const utils::ColorRGBA16 work = workData[i];
                    const utils::ColorRGBA16 base = baseData ? baseData[i] : utils::ColorRGBA16{0, 0, 0, 0};
                    const bool unchanged = work.r == base.r && work.g == base.g && work.b == base.b && work.a == base.a;
                    out[i] = unchanged ? base : mixPixel16(base, work, m_opacity);
                }
            } else {
                const uint8_t* workData = static_cast<const canvas::Tile*>(workTile)->getBuffer().getData();
                const uint8_t* baseData = baseTile ? baseTile->getBuffer().getData() : nullptr;
                uint8_t* out = layerTile->getBuffer().getData();
                for (size_t i = 0; i < kPixels; ++i) {
                    const size_t at = i * 4;
                    const utils::ColorRGBA work{workData[at], workData[at + 1], workData[at + 2], workData[at + 3]};
                    const utils::ColorRGBA base = baseData
                        ? utils::ColorRGBA{baseData[at], baseData[at + 1], baseData[at + 2], baseData[at + 3]}
                        : utils::ColorRGBA{0, 0, 0, 0};
                    const bool unchanged = work.r == base.r && work.g == base.g && work.b == base.b && work.a == base.a;
                    const utils::ColorRGBA mixed = unchanged ? base : mixPixel(base, work, m_opacity);
                    out[at] = mixed.r;
                    out[at + 1] = mixed.g;
                    out[at + 2] = mixed.b;
                    out[at + 3] = mixed.a;
                }
            }
        }
    }
}

} // namespace aladyn::engine::raster
