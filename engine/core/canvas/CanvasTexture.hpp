#ifndef ALADYN_ENGINE_CANVAS_TEXTURE_HPP
#define ALADYN_ENGINE_CANVAS_TEXTURE_HPP

#include "../texture/Texture2D.hpp"
#include "../texture/ProceduralTextures.hpp"
#include "../math/BezierCurve.hpp"
#include "../math/MathUtils.hpp"
#include "../raster/Dab.hpp"
#include <memory>

namespace aladyn::engine::canvas {

class CanvasTexture {
public:
    raster::ColorRGBA backgroundColor{255, 255, 255, 255};

    bool canvasGrainEnabled{false};
    double canvasGrainScale{1.0};
    double canvasGrainContrast{1.0};
    bool canvasGrainInvert{false};

    math::BezierCurve canvasTextureCurve{math::CurvePreset::Linear};
    std::shared_ptr<texture::Texture2D> canvasHeightTexture{texture::ProceduralTextures::createPaperGrain(512, 512)};

    mutable double heightLUT[256];
    mutable bool lutValid{false};

    void updateLUT() const noexcept {
        for (int i = 0; i < 256; ++i) {
            double h = static_cast<double>(i) / 255.0;
            if (canvasGrainInvert) {
                h = 1.0 - h;
            }
            if (canvasGrainContrast != 1.0 && canvasGrainContrast > 0.0) {
                const double halfSpan = 0.5 / canvasGrainContrast;
                h = math::MathUtils::smoothstep(0.5 - halfSpan, 0.5 + halfSpan, h);
            }
            heightLUT[i] = canvasTextureCurve.sample(h);
        }
        lutValid = true;
    }

    [[nodiscard]] inline double sampleLUT(uint8_t rawVal) const noexcept {
        if (!lutValid) updateLUT();
        return heightLUT[rawVal];
    }

    void invalidateLUT() noexcept {
        lutValid = false;
    }
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_CANVAS_TEXTURE_HPP
