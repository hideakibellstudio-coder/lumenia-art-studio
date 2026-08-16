#ifndef ALADYN_ENGINE_COMPOSITOR_HPP
#define ALADYN_ENGINE_COMPOSITOR_HPP

#include "Layer.hpp"
#include "../canvas/PixelBuffer.hpp"
#include <vector>
#include <memory>

namespace aladyn::engine::document {

class Compositor {
public:
    Compositor(int width, int height);

    static raster::ColorRGBA blendPixel(raster::ColorRGBA src, double layerOpacity, raster::ColorRGBA dst, LayerBlendMode mode);

    void composite(const std::vector<const Layer*>& layers, canvas::PixelBuffer& outputBuffer, const raster::ColorRGBA& bgColor = {255, 255, 255, 255});
    void composite(const std::vector<std::unique_ptr<Layer>>& layers, canvas::PixelBuffer& outputBuffer, const raster::ColorRGBA& bgColor = {255, 255, 255, 255});

    void compositeRegion(const std::vector<const Layer*>& layers, const math::Rect2D& region, canvas::PixelBuffer& outputBuffer, const raster::ColorRGBA& bgColor = {255, 255, 255, 255});
    void compositeRegion(const std::vector<std::unique_ptr<Layer>>& layers, const math::Rect2D& region, canvas::PixelBuffer& outputBuffer, const raster::ColorRGBA& bgColor = {255, 255, 255, 255});

private:
    int m_width{0};
    int m_height{0};
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_COMPOSITOR_HPP
