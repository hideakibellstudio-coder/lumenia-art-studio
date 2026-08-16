#ifndef ALADYN_ENGINE_OIL_IMPASTO_ENGINE_HPP
#define ALADYN_ENGINE_OIL_IMPASTO_ENGINE_HPP

#include "IBrushEngine.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE ÓLEO 3D & IMPASTO (OilImpastoEngine) ───────────────────
//
// Física: Tinta viscosa com massa física, ranhuras de cerda paralelas ao traço,
//         acúmulo de relevo (Impasto Ridge) e brilho especular úmido.
//
// Parâmetros exclusivos usados:
//   profile.oilParams.impastoDepth       (espessura do acúmulo 3D de tinta 0-1)
//   profile.oilParams.bristleGrooves     (profundidade das ranhuras de cerda 0-1)
//   profile.oilParams.viscosity          (viscosidade/resistência à fusão 0-1)
//   profile.oilParams.specularBrilliance (brilho especular das cristas 0-1)
// ───────────────────────────────────────────────────────────────────────────
class OilImpastoEngine final : public IBrushEngine {
public:
    OilImpastoEngine() = default;

    void renderDab(
        const raster::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const canvas::PixelBuffer* compositeBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::OilImpasto;
    }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_OIL_IMPASTO_ENGINE_HPP
