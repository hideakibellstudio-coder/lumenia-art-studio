#include "LayerMerger.hpp"
#include "FilterLayer.hpp"
#include "Compositor.hpp"
#include "blending/BlendEquations.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document {

bool LayerMerger::flattenGroup(
    std::vector<std::unique_ptr<Layer>>& drawingLayers,
    int& activeIndex,
    int width,
    int height,
    int index,
    bool linearGamma,
    bool deepColor
) {
    const int count = static_cast<int>(drawingLayers.size());
    if (index < 0 || index >= count) return false;
    if (!drawingLayers[index] || !drawingLayers[index]->isGroup()) return false;

    const Layer* groupNode = drawingLayers[index].get();
    std::string groupName = groupNode->getName();
    double groupOpacity = groupNode->getOpacity();
    bool groupVis = groupNode->isVisible();
    LayerBlendMode groupBlend = groupNode->getBlendMode();
    const LayerNode* groupParent = groupNode->getParent();

    std::vector<int> descendantIndices;
    for (int i = 0; i < count; ++i) {
        if (i == index || !drawingLayers[i]) continue;
        const LayerNode* curr = drawingLayers[i]->getParent();
        while (curr) {
            if (curr == groupNode) {
                descendantIndices.push_back(i);
                break;
            }
            curr = curr->getParent();
        }
    }

    auto flattened = std::make_unique<Layer>(groupName, width, height, false);
    flattened->setOpacity(groupOpacity);
    flattened->setVisible(groupVis);
    flattened->setParent(const_cast<LayerNode*>(groupParent));
    flattened->setBlendMode(groupBlend == LayerBlendMode::PassThrough ? LayerBlendMode::Normal : groupBlend);

    for (int dIdx : descendantIndices) {
        Layer* dLayer = drawingLayers[dIdx].get();
        if (!dLayer || dLayer->isGroup() || !dLayer->isVisible()) continue;

        double relOpacity = dLayer->getOpacity();
        const LayerNode* curr = dLayer->getParent();
        while (curr && curr != groupNode) {
            if (!curr->isVisible()) { relOpacity = 0.0; break; }
            relOpacity *= curr->getOpacity();
            curr = curr->getParent();
        }
        if (relOpacity <= 0.0) continue;

        auto& srcGrid = dLayer->getTileGrid();
        auto& dstGrid = flattened->getTileGrid();
        const int tilesY = srcGrid.getTilesCountY();
        const int tilesX = srcGrid.getTilesCountX();

        for (int ty = 0; ty < tilesY; ++ty) {
            for (int tx = 0; tx < tilesX; ++tx) {
                canvas::Tile* sTile = srcGrid.getTile(tx, ty);
                if (!sTile) continue;
                canvas::Tile* dTile = dstGrid.getOrCreateTile(tx, ty);
                if (!dTile) continue;

                canvas::PixelBuffer& sBuf = sTile->getBuffer();
                canvas::PixelBuffer& dBuf = dTile->getBuffer();

                for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                    for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                        raster::ColorRGBA src = sBuf.getPixel(px, py);
                        if (src.a == 0) continue;

                        raster::ColorRGBA dst = dBuf.getPixel(px, py);
                        dBuf.setPixel(px, py, blending::blendPixel(
                            src, relOpacity, dst, LayerBlendMode::Normal, linearGamma, deepColor));
                    }
                }
            }
        }
    }

    std::vector<std::unique_ptr<Layer>> newLayers;
    newLayers.reserve(drawingLayers.size());

    for (int i = 0; i < count; ++i) {
        if (i == index) {
            newLayers.push_back(std::move(flattened));
        } else if (std::find(descendantIndices.begin(), descendantIndices.end(), i) != descendantIndices.end()) {
            continue;
        } else {
            newLayers.push_back(std::move(drawingLayers[i]));
        }
    }

    drawingLayers = std::move(newLayers);
    activeIndex = std::min(index, static_cast<int>(drawingLayers.size()) - 1);

    // Reassocia ponteiros de pais
    for (auto& l : drawingLayers) {
        if (l && l->getParent() == groupNode) {
            l->setParent(const_cast<LayerNode*>(groupParent));
        }
    }
    return true;
}

bool LayerMerger::mergeLayerDown(
    std::vector<std::unique_ptr<Layer>>& drawingLayers,
    int& activeIndex,
    int width,
    int height,
    int index,
    bool linearGamma,
    bool deepColor
) {
    const int count = static_cast<int>(drawingLayers.size());
    if (index <= 0 || index >= count) return false;

    // Group flattening can remove the upper index as a descendant. Require
    // callers to flatten explicitly before resolving the next merge indices.
    if (drawingLayers[index]->isGroup() || drawingLayers[index - 1]->isGroup()) return false;

    Layer* upperLayer = drawingLayers[index].get();
    Layer* lowerLayer = drawingLayers[index - 1].get();
    if (!upperLayer || !lowerLayer) return false;

    // Se a camada superior for uma FilterLayer, rasteriza o filtro sobre os tiles da camada inferior
    if (upperLayer->isFilter()) {
        const auto* filterLayer = dynamic_cast<const FilterLayer*>(upperLayer);
        if (filterLayer) {
            auto& lowerGrid = lowerLayer->getTileGrid();
            lowerGrid.forEachTile([&](const auto& /*idx*/, canvas::Tile& tile) {
                Compositor::applyFilterToBuffer(*filterLayer, tile.getBuffer());
                tile.setDirty(true);
            });
        }
        drawingLayers.erase(drawingLayers.begin() + index);
        activeIndex = index - 1;
        return true;
    }

    const double upperOpacity = upperLayer->getOpacity();

    auto& upperGrid = upperLayer->getTileGrid();
    auto& lowerGrid = lowerLayer->getTileGrid();

    const int tilesY = upperGrid.getTilesCountY();
    const int tilesX = upperGrid.getTilesCountX();

    const LayerBlendMode upperBlend = upperLayer->getBlendMode();
    const bool upperIsClipping = upperLayer->isClippingMask();

    for (int ty = 0; ty < tilesY; ++ty) {
        for (int tx = 0; tx < tilesX; ++tx) {
            canvas::Tile* uTile = upperGrid.getTile(tx, ty);
            if (!uTile) continue;

            // Se for clipping mask, só opera onde a camada base já tem tile
            canvas::Tile* lTile = upperIsClipping ? lowerGrid.getTile(tx, ty) : lowerGrid.getOrCreateTile(tx, ty);
            if (!lTile) continue;

            canvas::PixelBuffer& uBuf = uTile->getBuffer();
            canvas::PixelBuffer& lBuf = lTile->getBuffer();

            for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                    raster::ColorRGBA src = uBuf.getPixel(px, py);
                    if (src.a == 0) continue;

                    raster::ColorRGBA dst = lBuf.getPixel(px, py);
                    // Não mescla fora da silhueta da camada base
                    if (upperIsClipping && dst.a == 0) continue;

                    raster::ColorRGBA blended = blending::blendPixel(src, upperOpacity, dst, upperBlend, linearGamma, deepColor);
                    lBuf.setPixel(px, py, blended);
                }
            }
        }
    }

    drawingLayers.erase(drawingLayers.begin() + index);
    activeIndex = index - 1;
    return true;
}

} // namespace aladyn::engine::document
