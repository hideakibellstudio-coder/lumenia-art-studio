#ifndef ALADYN_ENGINE_LAYER_MERGER_HPP
#define ALADYN_ENGINE_LAYER_MERGER_HPP

#include "Layer.hpp"
#include <vector>
#include <memory>

namespace aladyn::engine::document {

class LayerMerger {
public:
    static bool flattenGroup(
        std::vector<std::unique_ptr<Layer>>& drawingLayers,
        int& activeIndex,
        int width,
        int height,
        int index
    );

    static bool mergeLayerDown(
        std::vector<std::unique_ptr<Layer>>& drawingLayers,
        int& activeIndex,
        int width,
        int height,
        int index
    );
};

} // namespace aladyn::engine::document

#endif // ALADYN_ENGINE_LAYER_MERGER_HPP
