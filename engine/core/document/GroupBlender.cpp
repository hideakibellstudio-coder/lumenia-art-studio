#include "GroupBlender.hpp"
#include "CompositePixel.hpp"
#include "filters/FilterApplier.hpp"
#include <algorithm>
#include <cstring>
#include <stdexcept>

namespace aladyn::engine::document::internal {

template <typename Pixel>
GroupBlender<Pixel>::GroupBlender(canvas::PixelBuffer& outputBuffer, const RegionBounds& bounds, bool linearGamma, bool deepColor)
    : m_outputBuffer(outputBuffer),
      m_bounds(bounds),
      m_linearGamma(linearGamma),
      m_deepColor(deepColor),
      m_outData(outputBuffer.pixels<Pixel>()),
      m_outStride(outputBuffer.getWidth()) {}

template <typename Pixel>
void GroupBlender<Pixel>::beginGroup() {
    const size_t needed = static_cast<size_t>(m_bounds.regW) * m_bounds.regH;
    const Pixel transparent{0, 0, 0, 0};
    if (m_groupPixels.size() != needed) {
        m_groupPixels.assign(needed, transparent);
    } else {
        std::fill(m_groupPixels.begin(), m_groupPixels.end(), transparent);
    }
}

template <typename Pixel>
void GroupBlender<Pixel>::composeTileGrid(
    const canvas::TileGrid& grid,
    double opacity,
    LayerBlendMode mode,
    const Layer* clipBase,
    const canvas::TileGrid* maskGrid,
    bool isToGroup
) {
    using Ops = CompositePixel<Pixel>;
    if (grid.getFormat() != Ops::kFormat ||
        (clipBase && clipBase->getTileGrid().getFormat() != Ops::kFormat) ||
        (maskGrid && maskGrid->getFormat() != Ops::kFormat))
        throw std::logic_error("compositor: layer pixel format differs from the document's");

    Pixel* targetData = isToGroup ? m_groupPixels.data() : m_outData;
    const int targetStride = isToGroup ? m_bounds.regW : m_outStride;
    const int targetOffsetX = isToGroup ? m_bounds.minX : 0;
    const int targetOffsetY = isToGroup ? m_bounds.minY : 0;

    const int maxTilesX = grid.getTilesCountX();
    const int maxTilesY = grid.getTilesCountY();
    const int cSTx = std::clamp(m_bounds.startTileX, 0, maxTilesX - 1);
    const int cETx = std::clamp(m_bounds.endTileX,   0, maxTilesX - 1);
    const int cSTy = std::clamp(m_bounds.startTileY, 0, maxTilesY - 1);
    const int cETy = std::clamp(m_bounds.endTileY,   0, maxTilesY - 1);

    const int numTilesX = cETx - cSTx + 1;
    const int numTilesY = cETy - cSTy + 1;
    const int totalTiles = numTilesX * numTilesY;

    // O desvio por modo, gama e Deep Color é feito aqui, uma vez por camada; as linhas só rodam o laço escolhido.
    const typename Ops::Plan plan = Ops::plan(opacity, mode, m_linearGamma, m_deepColor);

    // Cada thread lê os tiles comprimidos num buffer seu: a composição só lê, e ler não descomprime de vez
    // (antes `getBuffer()` desfazia `compress_inactive_layers` na primeira composição). A base do recorte tem
    // o mesmo índice de tile que a camada, então é buscada uma vez por tile, não uma vez por pixel.
    #pragma omp parallel if(totalTiles >= 16)
    {
        canvas::PixelBuffer scratch(canvas::Tile::TILE_SIZE, canvas::Tile::TILE_SIZE, Ops::kFormat, utils::ColorRGBA{0, 0, 0, 0});
        canvas::PixelBuffer baseScratch(canvas::Tile::TILE_SIZE, canvas::Tile::TILE_SIZE, Ops::kFormat, utils::ColorRGBA{0, 0, 0, 0});
        canvas::PixelBuffer maskScratch(canvas::Tile::TILE_SIZE, canvas::Tile::TILE_SIZE, Ops::kFormat, utils::ColorRGBA{0, 0, 0, 0});
        #pragma omp for schedule(static)
        for (int tIdx = 0; tIdx < totalTiles; ++tIdx) {
            const int ty = cSTy + (tIdx / numTilesX);
            const int tx = cSTx + (tIdx % numTilesX);

            const canvas::Tile* tile = const_cast<canvas::TileGrid&>(grid).getTile(tx, ty);
            if (!tile) continue;

            const canvas::PixelBuffer& tileBuf = tile->view(scratch);
            const Pixel* baseTilePixels = nullptr;
            if (clipBase) {
                const canvas::Tile* baseTile = const_cast<canvas::TileGrid&>(clipBase->getTileGrid()).getTile(tx, ty);
                if (!baseTile) continue;  // sem base neste tile, nada do recorte aparece nele
                baseTilePixels = baseTile->view(baseScratch).template pixels<Pixel>();
            }

            const Pixel* maskTilePixels = nullptr;
            if (maskGrid) {
                const canvas::Tile* maskTile = const_cast<canvas::TileGrid*>(maskGrid)->getTile(tx, ty);
                if (maskTile) {
                    maskTilePixels = maskTile->view(maskScratch).template pixels<Pixel>();
                }
            }

            const double baseOpacity = clipBase ? clipBase->getEffectiveOpacity() : 1.0;
            const int tilePixelX = tile->getPixelX();
            const int tilePixelY = tile->getPixelY();

            const int tileMinX = std::max(m_bounds.minX, tilePixelX);
            const int tileMaxX = std::min(m_bounds.maxX, tilePixelX + canvas::Tile::TILE_SIZE - 1);
            const int tileMinY = std::max(m_bounds.minY, tilePixelY);
            const int tileMaxY = std::min(m_bounds.maxY, tilePixelY + canvas::Tile::TILE_SIZE - 1);

            for (int globalY = tileMinY; globalY <= tileMaxY; ++globalY) {
                const int localY = globalY - tilePixelY;
                const Pixel* srcRow = tileBuf.template pixels<Pixel>() + (localY * canvas::Tile::TILE_SIZE);
                Pixel* dstRow = targetData + static_cast<size_t>(globalY - targetOffsetY) * targetStride;

                if (!baseTilePixels && !maskTilePixels) {
                    if (tileMaxX >= tileMinX) {
                        Ops::blendRow(
                            plan, srcRow + (tileMinX - tilePixelX), dstRow + (tileMinX - targetOffsetX),
                            static_cast<size_t>(tileMaxX - tileMinX + 1));
                    }
                    continue;
                }
                // Camada recortada pela base e/ou com mascara de camada:
                for (int globalX = tileMinX; globalX <= tileMaxX; ++globalX) {
                    const int localX = globalX - tilePixelX;
                    const Pixel src = srcRow[localX];
                    if (src.a == 0) continue;

                    double curOpacity = opacity;
                    if (baseTilePixels) {
                        const double baseA = Ops::alphaUnit(baseTilePixels[localY * canvas::Tile::TILE_SIZE + localX]) * baseOpacity;
                        if (baseA <= 0.0) continue;
                        curOpacity *= baseA;
                    }
                    if (maskTilePixels) {
                        const Pixel mp = maskTilePixels[localY * canvas::Tile::TILE_SIZE + localX];
                        const double aVal = Ops::alphaUnit(mp);
                        if (aVal > 0.0) {
                            const double rVal = (sizeof(decltype(mp.r)) == 1) ? (static_cast<double>(mp.r) / 255.0) : (static_cast<double>(mp.r) / 65535.0);
                            const double maskVal = rVal * aVal + (1.0 - aVal);
                            if (maskVal <= 0.0) continue;
                            curOpacity *= maskVal;
                        }
                    }

                    const int dstX = globalX - targetOffsetX;
                    dstRow[dstX] = Ops::blendPixel(src, curOpacity, dstRow[dstX], mode, m_linearGamma, m_deepColor);
                }
            }
        }
    }
}

template <typename Pixel>
void GroupBlender<Pixel>::applyFilterToGroup(const FilterLayer& filter) {
    const int regW = m_bounds.regW;
    const int regH = m_bounds.regH;
    const size_t bytes = static_cast<size_t>(regW) * regH * sizeof(Pixel);
    canvas::PixelBuffer groupPixelBuf(regW, regH, CompositePixel<Pixel>::kFormat, utils::ColorRGBA{0, 0, 0, 0});
    std::memcpy(groupPixelBuf.getData(), m_groupPixels.data(), bytes);
    filters::FilterApplier::apply(filter.settings(), groupPixelBuf, 0, regW - 1, 0, regH - 1);
    std::memcpy(m_groupPixels.data(), groupPixelBuf.getData(), bytes);
}

template <typename Pixel>
void GroupBlender<Pixel>::blendGroupToDestination(const Layer* group) {
    if (!group || m_groupPixels.empty()) return;
    const double gOpacity = group->getEffectiveOpacity();
    const LayerBlendMode gMode = group->getBlendMode();
    if (gOpacity <= 0.0) return;

    using Ops = CompositePixel<Pixel>;
    const int regW = m_bounds.regW;
    const typename Ops::Plan plan = Ops::plan(gOpacity, gMode, m_linearGamma, m_deepColor);
    const size_t rowPixels = static_cast<size_t>(m_bounds.maxX - m_bounds.minX + 1);
    #pragma omp parallel for schedule(static) if((m_bounds.maxY - m_bounds.minY) > 64)
    for (int y = m_bounds.minY; y <= m_bounds.maxY; ++y) {
        const Pixel* srcRow = m_groupPixels.data() + static_cast<size_t>(y - m_bounds.minY) * regW;
        Pixel* dstRow = m_outData + static_cast<size_t>(y) * m_outStride;
        Ops::blendRow(plan, srcRow, dstRow + m_bounds.minX, rowPixels);
    }
}

template class GroupBlender<utils::ColorRGBA>;
template class GroupBlender<utils::ColorRGBA16>;

} // namespace aladyn::engine::document::internal
