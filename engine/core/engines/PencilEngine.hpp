#ifndef ALADYN_ENGINE_PENCIL_ENGINE_HPP
#define ALADYN_ENGINE_PENCIL_ENGINE_HPP

#include "IBrushEngine.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE LÁPIS / GRAFITE / GIZ (PencilEngine) ───────────────────
//
// Física: Contato do grafite/carvão com os dentes do micro-relevo do papel.
// O Canvas Heightmap é o elemento central — a tinta só penetra nos vales
// do papel. A dureza do grafite (graphiteHardness) modula o limiar de
// contato na equação 3D: grafite mole (0.0) deposita muito com pouca pressão;
// grafite duro (1.0) exige pressão alta para depositar.
//
// Parâmetros exclusivos usados:
//   profile.pencilParams.graphiteHardness  (0.0 = 6B mole, 1.0 = 2H duro)
//   profile.pencilParams.tiltShadingEnabled (expansão lateral por inclinação)
//
// Parâmetros comuns usados:
//   brushSize, minSizePercent, opacity, hardness, spacingFactor,
//   pressureSizeCurve, tip (angle, aspectRatio, followStroke, jitters),
//   shapeTexture, brushHeightTexture, canvasHeightTexture, brushTextureCurve.
// ───────────────────────────────────────────────────────────────────────────
class PencilEngine final : public IBrushEngine {
public:
    PencilEngine() = default;

    void renderDab(
        const raster::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const canvas::PixelBuffer* compositeBuffer = nullptr,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::Pencil;
    }
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_PENCIL_ENGINE_HPP
