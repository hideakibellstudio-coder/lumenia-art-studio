#ifndef ALADYN_ENGINE_LAYER_HPP
#define ALADYN_ENGINE_LAYER_HPP

#include "LayerNode.hpp"
#include "../canvas/TileGrid.hpp"
#include <string>
#include <cstddef>

namespace aladyn::engine::document {

class Layer : public LayerNode {
public:
    Layer(const std::string& name, int width, int height, bool isBackground = false,
          canvas::PixelFormat format = canvas::PixelFormat::RGBA8)
        : LayerNode(name, LayerNodeType::DrawingLayer), m_isBackground(isBackground), m_tileGrid(width, height, format) {}

    // Constructor alternativo para criação de grupos com LayerNodeType::Group
    Layer(const std::string& name, LayerNodeType type, int width, int height, bool isBackground = false,
          canvas::PixelFormat format = canvas::PixelFormat::RGBA8)
        : LayerNode(name, type), m_isBackground(isBackground), m_tileGrid(width, height, format) {}

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

    // ─── MÁSCARA DE CAMADA (S9) ──────────────────────────────────────────────
    [[nodiscard]] bool hasMask() const noexcept { return m_maskGrid != nullptr; }
    [[nodiscard]] bool isMaskEnabled() const noexcept { return m_maskEnabled; }
    void setMaskEnabled(bool enabled) noexcept { m_maskEnabled = enabled; }
    [[nodiscard]] bool isMaskEditTarget() const noexcept { return m_maskEditTarget; }
    void setMaskEditTarget(bool target) noexcept { m_maskEditTarget = target; }

    canvas::TileGrid* getMaskGrid() noexcept { return m_maskGrid.get(); }
    const canvas::TileGrid* getMaskGrid() const noexcept { return m_maskGrid.get(); }

    void createMask() {
        if (!m_maskGrid) {
            m_maskGrid = std::make_unique<canvas::TileGrid>(m_tileGrid.getWidth(), m_tileGrid.getHeight(), m_tileGrid.getFormat());
            m_maskEnabled = true;
            m_maskEditTarget = false;
        }
    }

    void removeMask() noexcept {
        m_maskGrid.reset();
        m_maskEnabled = false;
        m_maskEditTarget = false;
    }

    [[nodiscard]] canvas::TileGrid& getTargetGrid() noexcept {
        return (m_maskEditTarget && m_maskGrid) ? *m_maskGrid : m_tileGrid;
    }
    [[nodiscard]] const canvas::TileGrid& getTargetGrid() const noexcept {
        return (m_maskEditTarget && m_maskGrid) ? *m_maskGrid : m_tileGrid;
    }

    // ─── FASE 4: COMPRESSÃO & MEMÓRIA ────────────────────────────────────────
    size_t compressInactiveTiles() {
        size_t c = m_tileGrid.compressInactiveTiles();
        if (m_maskGrid) c += m_maskGrid->compressInactiveTiles();
        return c;
    }
    size_t decompressAllTiles() {
        size_t d = m_tileGrid.decompressAllTiles();
        if (m_maskGrid) d += m_maskGrid->decompressAllTiles();
        return d;
    }
    [[nodiscard]] size_t getMemoryFootprintBytes() const noexcept {
        size_t m = m_tileGrid.getMemoryFootprintBytes();
        if (m_maskGrid) m += m_maskGrid->getMemoryFootprintBytes();
        return m;
    }

private:
    bool m_alphaLocked{false};
    bool m_clippingMask{false};
    bool m_isBackground{false};
    bool m_maskEnabled{false};
    bool m_maskEditTarget{false};
    double m_effectiveOpacity{1.0};
    mutable const Layer* m_clipBase{nullptr};
    canvas::TileGrid m_tileGrid;
    std::unique_ptr<canvas::TileGrid> m_maskGrid{nullptr};
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_LAYER_HPP
