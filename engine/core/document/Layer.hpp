#ifndef ALADYN_ENGINE_LAYER_HPP
#define ALADYN_ENGINE_LAYER_HPP

#include "LayerNode.hpp"
#include "../canvas/TileGrid.hpp"
#include <string>

namespace aladyn::engine::document {

class Layer : public LayerNode {
public:
    Layer(const std::string& name, int width, int height, bool isBackground = false)
        : LayerNode(name, LayerNodeType::DrawingLayer), m_tileGrid(width, height), m_isBackground(isBackground) {}

    // Constructor alternativo para criação de grupos com LayerNodeType::Group
    Layer(const std::string& name, LayerNodeType type, int width, int height, bool isBackground = false)
        : LayerNode(name, type), m_tileGrid(width, height), m_isBackground(isBackground) {}

    [[nodiscard]] bool isAlphaLocked() const noexcept { return m_alphaLocked; }
    void setAlphaLocked(bool locked) noexcept { m_alphaLocked = locked; }

    [[nodiscard]] bool isClippingMask() const noexcept { return m_clippingMask; }
    void setClippingMask(bool clipped) noexcept { m_clippingMask = clipped; }

    [[nodiscard]] bool isBackground() const noexcept { return m_isBackground; }
    void setBackground(bool isBg) noexcept { m_isBackground = isBg; }

    [[nodiscard]] double getEffectiveOpacity() const noexcept { return m_effectiveOpacity; }
    void setEffectiveOpacity(double opacity) noexcept { m_effectiveOpacity = opacity; }

    [[nodiscard]] canvas::TileGrid& getTileGrid() noexcept { return m_tileGrid; }
    [[nodiscard]] const canvas::TileGrid& getTileGrid() const noexcept { return m_tileGrid; }

private:
    bool m_alphaLocked{false};
    bool m_clippingMask{false};
    bool m_isBackground{false};
    double m_effectiveOpacity{1.0};
    canvas::TileGrid m_tileGrid;
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_LAYER_HPP
