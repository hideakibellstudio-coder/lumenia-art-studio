#include "LayerMerger.hpp"
#include "FilterLayer.hpp"
#include "Compositor.hpp"
#include "CompositePixel.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document {

namespace {

// Compõe `source` sobre `target` pixel a pixel, tile a tile, no pixel `Pixel` do formato das duas grades. Com
// `clipToBase`, só mexe onde o destino já tem tile e pixel (máscara de recorte); sem ele, cria os tiles que faltarem.
template <typename Pixel>
void blendGridAs(
    canvas::TileGrid& source,
    canvas::TileGrid& target,
    double opacity,
    LayerBlendMode mode,
    bool clipToBase,
    bool linearGamma,
    bool deepColor
) {
    using Ops = internal::CompositePixel<Pixel>;
    for (int ty = 0; ty < source.getTilesCountY(); ++ty) {
        for (int tx = 0; tx < source.getTilesCountX(); ++tx) {
            canvas::Tile* sourceTile = source.getTile(tx, ty);
            if (!sourceTile) continue;

            canvas::Tile* targetTile = clipToBase ? target.getTile(tx, ty) : target.getOrCreateTile(tx, ty);
            if (!targetTile) continue;

            const Pixel* sourcePixels = sourceTile->getBuffer().template pixels<Pixel>();
            Pixel* targetPixels = targetTile->getBuffer().template pixels<Pixel>();
            for (int i = 0; i < canvas::Tile::TILE_SIZE * canvas::Tile::TILE_SIZE; ++i) {
                const Pixel src = sourcePixels[i];
                if (src.a == 0) continue;

                const Pixel dst = targetPixels[i];
                // Não mescla fora da silhueta da camada base
                if (clipToBase && dst.a == 0) continue;

                targetPixels[i] = Ops::blendPixel(src, opacity, dst, mode, linearGamma, deepColor);
            }
        }
    }
}

void blendGridInto(
    canvas::TileGrid& source,
    canvas::TileGrid& target,
    double opacity,
    LayerBlendMode mode,
    bool clipToBase,
    bool linearGamma,
    bool deepColor
) {
    if (source.getFormat() == canvas::PixelFormat::RGBA16) {
        blendGridAs<utils::ColorRGBA16>(source, target, opacity, mode, clipToBase, linearGamma, deepColor);
    } else {
        blendGridAs<utils::ColorRGBA>(source, target, opacity, mode, clipToBase, linearGamma, deepColor);
    }
}

bool isDescendantOf(const LayerNode* node, const LayerNode* ancestor) {
    for (const LayerNode* current = node->getParent(); current; current = current->getParent()) {
        if (current == ancestor) return true;
    }
    return false;
}

std::vector<int> descendantIndices(const std::vector<std::unique_ptr<Layer>>& layers, int groupIndex) {
    const LayerNode* group = layers[groupIndex].get();
    std::vector<int> indices;
    for (int i = 0; i < static_cast<int>(layers.size()); ++i) {
        if (i != groupIndex && layers[i] && isDescendantOf(layers[i].get(), group)) indices.push_back(i);
    }
    return indices;
}

// A opacidade de `layer` dentro do grupo que está sendo achatado: o produto das opacidades dela e
// dos grupos entre ela e `group`; um grupo invisível no caminho zera a camada.
double opacityWithinGroup(const Layer& layer, const LayerNode* group) {
    double opacity = layer.getOpacity();
    for (const LayerNode* current = layer.getParent(); current && current != group; current = current->getParent()) {
        if (!current->isVisible()) return 0.0;
        opacity *= current->getOpacity();
    }
    return opacity;
}

// A camada raster que ocupa o lugar do grupo: mesmo nome, opacidade, visibilidade e pai; o modo
// Atravessar (padrão dos grupos) vira Normal porque agora há uma imagem só.
std::unique_ptr<Layer> emptyLayerLike(const Layer& group, int width, int height) {
    auto flattened = std::make_unique<Layer>(group.getName(), width, height, false, group.getTileGrid().getFormat());
    flattened->setOpacity(group.getOpacity());
    flattened->setVisible(group.isVisible());
    flattened->setParent(const_cast<LayerNode*>(group.getParent()));
    const LayerBlendMode blend = group.getBlendMode();
    flattened->setBlendMode(blend == LayerBlendMode::PassThrough ? LayerBlendMode::Normal : blend);
    return flattened;
}

void paintDescendants(
    const std::vector<std::unique_ptr<Layer>>& layers,
    const std::vector<int>& descendants,
    const Layer& group,
    Layer& flattened,
    bool linearGamma,
    bool deepColor
) {
    for (const int index : descendants) {
        Layer* layer = layers[index].get();
        if (!layer || layer->isGroup() || !layer->isVisible()) continue;

        const double opacity = opacityWithinGroup(*layer, &group);
        if (opacity <= 0.0) continue;

        blendGridInto(layer->getTileGrid(), flattened.getTileGrid(), opacity, LayerBlendMode::Normal,
                      /*clipToBase=*/false, linearGamma, deepColor);
    }
}

// Rasteriza o filtro sobre os tiles da camada que ele afeta.
void rasterizeFilterInto(const FilterLayer& filter, Layer& target) {
    target.getTileGrid().forEachTile([&](const auto& /*idx*/, canvas::Tile& tile) {
        Compositor::applyFilterToBuffer(filter, tile.getBuffer());
        tile.setDirty(true);
    });
}

// A pilha tem um formato de pixel só; uma camada de outro formato seria misturada como lixo, então a mesclagem
// recusa (devolve false, sem tocar em nada) a pilha em que as camadas não concordam.
bool sameFormat(const std::vector<std::unique_ptr<Layer>>& layers) {
    const Layer* first = nullptr;
    for (const auto& layer : layers) {
        if (!layer) continue;
        if (!first) first = layer.get();
        if (layer->getTileGrid().getFormat() != first->getTileGrid().getFormat()) return false;
    }
    return true;
}

}  // namespace

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
    if (!sameFormat(drawingLayers)) return false;

    const Layer* groupNode = drawingLayers[index].get();
    const LayerNode* groupParent = groupNode->getParent();
    const std::vector<int> descendants = descendantIndices(drawingLayers, index);

    auto flattened = emptyLayerLike(*groupNode, width, height);
    paintDescendants(drawingLayers, descendants, *groupNode, *flattened, linearGamma, deepColor);

    std::vector<bool> removed(count, false);
    for (const int descendant : descendants) removed[descendant] = true;

    std::vector<std::unique_ptr<Layer>> newLayers;
    newLayers.reserve(drawingLayers.size());
    for (int i = 0; i < count; ++i) {
        if (i == index) {
            newLayers.push_back(std::move(flattened));
        } else if (!removed[i]) {
            newLayers.push_back(std::move(drawingLayers[i]));
        }
    }

    drawingLayers = std::move(newLayers);
    activeIndex = std::min(index, static_cast<int>(drawingLayers.size()) - 1);

    // Reassocia ponteiros de pais
    for (auto& layer : drawingLayers) {
        if (layer && layer->getParent() == groupNode) {
            layer->setParent(const_cast<LayerNode*>(groupParent));
        }
    }
    return true;
}

bool LayerMerger::mergeLayerDown(
    std::vector<std::unique_ptr<Layer>>& drawingLayers,
    int& activeIndex,
    int index,
    bool linearGamma,
    bool deepColor
) {
    const int count = static_cast<int>(drawingLayers.size());
    if (index <= 0 || index >= count) return false;
    if (!sameFormat(drawingLayers)) return false;

    // Group flattening can remove the upper index as a descendant. Require
    // callers to flatten explicitly before resolving the next merge indices.
    if (drawingLayers[index]->isGroup() || drawingLayers[index - 1]->isGroup()) return false;

    Layer* upperLayer = drawingLayers[index].get();
    Layer* lowerLayer = drawingLayers[index - 1].get();
    if (!upperLayer || !lowerLayer) return false;

    if (upperLayer->isFilter()) {
        if (const auto* filterLayer = dynamic_cast<const FilterLayer*>(upperLayer)) {
            rasterizeFilterInto(*filterLayer, *lowerLayer);
        }
    } else {
        blendGridInto(upperLayer->getTileGrid(), lowerLayer->getTileGrid(), upperLayer->getOpacity(),
                      upperLayer->getBlendMode(), upperLayer->isClippingMask(), linearGamma, deepColor);
    }

    drawingLayers.erase(drawingLayers.begin() + index);
    activeIndex = index - 1;
    return true;
}

} // namespace aladyn::engine::document
