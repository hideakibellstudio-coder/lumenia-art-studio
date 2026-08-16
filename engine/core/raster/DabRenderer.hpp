#ifndef ALADYN_ENGINE_DAB_RENDERER_HPP
#define ALADYN_ENGINE_DAB_RENDERER_HPP

#include "Dab.hpp"
#include "PixelContext.hpp"
#include "../canvas/TileGrid.hpp"
#include "../canvas/CanvasTexture.hpp"
#include "../brush/BrushProfile.hpp"

namespace aladyn::engine::raster {

class DabRenderer {
public:
    static void renderDab(
        const Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const PixelContext& ctx = {}
    );
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_DAB_RENDERER_HPP
