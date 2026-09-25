#include "BrushPreviews.hpp"
#include "../orchestrator/StrokePreviewRenderer.hpp"

namespace aladyn::engine::boundary {

static_assert(kRoundTipPreviewSize == orchestrator::kRoundTipPreviewSize);

std::vector<uint8_t> renderStrokePreview(const brush::BrushProfile& profile, int width, int height) {
    return orchestrator::renderStrokePreview(profile, width, height);
}

std::vector<uint8_t> renderRoundTipMask(double hardness) {
    return orchestrator::renderRoundTipMask(hardness);
}

} // namespace aladyn::engine::boundary
