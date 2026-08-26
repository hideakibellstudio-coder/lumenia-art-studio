#ifndef ALADYN_ENGINE_FILTER_APPLIER_HPP
#define ALADYN_ENGINE_FILTER_APPLIER_HPP

#include "../FilterLayer.hpp"
#include "../../canvas/PixelBuffer.hpp"

namespace aladyn::engine::document::blending {

class FilterApplier {
public:
    static void apply(const FilterLayer& filter, canvas::PixelBuffer& buffer, int minX = 0, int maxX = -1, int minY = 0, int maxY = -1);
};

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_FILTER_APPLIER_HPP
