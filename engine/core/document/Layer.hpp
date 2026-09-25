#ifndef ALADYN_ENGINE_LAYER_HPP
#define ALADYN_ENGINE_LAYER_HPP

#include "LayerNode.hpp"
#include "../canvas/TileGrid.hpp"
#include <string>
#include <cstddef>

namespace aladyn::engine::document {

class Layer : public LayerNode {
public:
    Layer(const std::string& name, int width, int height, bool isBackground = false)
        : LayerNode(name, LayerNodeType::DrawingLayer), m_isBackground(isBackground), m_tileGrid(width, height) {}

    // Constructor alternativo para criação de grupos com LayerNodeType::Group
    Layer(const std::string& name, LayerNodeType type, int width, int height, bool isBackground = false)
        : LayerNode(name, type), m_isBackground(isBackground), m_tileGrid(width, height) {}

    [[nodiscard]] bool isAlphaLocked() const noexcept { return m_alphaLocked; }
    void setAlphaLocked(bool locked) noexcept { m_alphaLocked = locked; }

    [[nodiscard]] bool isClippingMask() const noexcept { return m_clippingMask; }
    void setClippingMask(bool clipped) noexcept { m_clippingMask = clipped; }

    [[nodiscard]] bool isBackground() const noexcept { return m_isBackground; }
    void setBackground(bool isBg) noexcept { m_isBackground = isBg; }

    [[nodiscard]] double getEffectiveOpacity() const noexcept {
        if (!isVisible()) return 0.0;
        double eff = getOpacity();
        const LayerNode* curr = getParent();
        while (curr) {
            if (!curr->isVisible()) return 0.0;
            eff *= curr->getOpacity();
            curr = curr->getParent();
        }
        return eff;
    }
    void setEffectiveOpacity(double opacity) noexcept { m_effectiveOpacity = opacity; }

    [[nodiscard]] const Layer* getClipBase() const noexcept { return m_clipBase; }
    void setClipBase(const Layer* base) const noexcept { m_clipBase = base; }

    [[nodiscard]] canvas::TileGrid& getTileGrid() noexcept { return m_tileGrid; }
    [[nodiscard]] const canvas::TileGrid& getTileGrid() const noexcept { return m_tileGrid; }

    // ─── FASE 4: COMPRESSÃO & MEMÓRIA ────────────────────────────────────────
    size_t compressInactiveTiles() { return m_tileGrid.compressInactiveTiles(); }
    size_t decompressAllTiles() { return m_tileGrid.decompressAllTiles(); }
    [[nodiscard]] size_t getMemoryFootprintBytes() const noexcept { return m_tileGrid.getMemoryFootprintBytes(); }

private:
    bool m_alphaLocked{false};
    bool m_clippingMask{false};
    bool m_isBackground{false};
    double m_effectiveOpacity{1.0};
    mutable const Layer* m_clipBase{nullptr};
    canvas::TileGrid m_tileGrid;
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_LAYER_HPP
