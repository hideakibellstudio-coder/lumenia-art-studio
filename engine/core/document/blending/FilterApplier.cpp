#include "FilterApplier.hpp"
#include "filters/FilterKernels.hpp"

#include <algorithm>

namespace aladyn::engine::document::blending {

void FilterApplier::apply(const FilterLayer& filter, canvas::PixelBuffer& buffer, int minX, int maxX, int minY, int maxY) {
    const double opacity = filter.getEffectiveOpacity();
    if (opacity <= 0.0) return;

    const FilterType type = filter.getFilterType();
    const int w = buffer.getWidth();
    const int h = buffer.getHeight();

    int startX = std::max(0, minX);
    int endX   = (maxX < 0) ? (w - 1) : std::min(w - 1, maxX);
    int startY = std::max(0, minY);
    int endY   = (maxY < 0) ? (h - 1) : std::min(h - 1, maxY);

    if (startX > endX || startY > endY) return;

    const filters::FilterRegion region{
        buffer.getData(), w, h, startX, endX, startY, endY, opacity, (opacity >= 0.999)
    };

    switch (type) {
        case FilterType::BrightnessContrast: filters::applyBrightnessContrast(filter, region); break;
        case FilterType::ColorBalance:       filters::applyColorBalance(filter, region);       break;
        case FilterType::InvertThreshold:    filters::applyInvertThreshold(filter, region);    break;
        case FilterType::HueSat:             filters::applyHueSat(filter, region);             break;
        case FilterType::Pixelate:           filters::applyPixelate(filter, region);           break;
        case FilterType::GaussianBlur:       filters::applyGaussianBlur(filter, region);       break;
        case FilterType::SharpenVignette:    filters::applySharpenVignette(filter, region);    break;
        default: break;
    }
}

} // namespace aladyn::engine::document::blending
