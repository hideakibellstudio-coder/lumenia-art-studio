#include "FilterApplier.hpp"
#include "FilterKernels.hpp"
#include "FilterKernels16.hpp"

#include <algorithm>

namespace aladyn::engine::document::filters {

namespace {

// Os mesmos sete filtros, para um buffer de 16 bits.
void applyKernel16(FilterType type, const FilterSettings& filter, const FilterRegion& region) {
    switch (type) {
        case FilterType::BrightnessContrast: applyBrightnessContrast16(filter, region); break;
        case FilterType::ColorBalance:       applyColorBalance16(filter, region);       break;
        case FilterType::InvertThreshold:    applyInvertThreshold16(filter, region);    break;
        case FilterType::HueSat:             applyHueSat16(filter, region);             break;
        case FilterType::Pixelate:           applyPixelate16(filter, region);           break;
        case FilterType::GaussianBlur:       applyGaussianBlur16(filter, region);       break;
        case FilterType::SharpenVignette:    applySharpenVignette16(filter, region);    break;
        default: break;
    }
}

} // namespace

void FilterApplier::apply(const FilterSettings& filter, canvas::PixelBuffer& buffer, int minX, int maxX, int minY, int maxY) {
    const double opacity = filter.opacity;
    if (opacity <= 0.0) return;

    const FilterType type = filter.type;
    const int w = buffer.getWidth();
    const int h = buffer.getHeight();

    int startX = std::max(0, minX);
    int endX   = (maxX < 0) ? (w - 1) : std::min(w - 1, maxX);
    int startY = std::max(0, minY);
    int endY   = (maxY < 0) ? (h - 1) : std::min(h - 1, maxY);

    if (startX > endX || startY > endY) return;

    const FilterRegion region{
        buffer.getData(), w, h, startX, endX, startY, endY, opacity, (opacity >= 0.999)
    };

    if (buffer.getFormat() == canvas::PixelFormat::RGBA16) {
        applyKernel16(type, filter, region);
        return;
    }

    switch (type) {
        case FilterType::BrightnessContrast: applyBrightnessContrast(filter, region); break;
        case FilterType::ColorBalance:       applyColorBalance(filter, region);       break;
        case FilterType::InvertThreshold:    applyInvertThreshold(filter, region);    break;
        case FilterType::HueSat:             applyHueSat(filter, region);             break;
        case FilterType::Pixelate:           applyPixelate(filter, region);           break;
        case FilterType::GaussianBlur:       applyGaussianBlur(filter, region);       break;
        case FilterType::SharpenVignette:    applySharpenVignette(filter, region);    break;
        default: break;
    }
}

} // namespace aladyn::engine::document::filters
