#ifndef ALADYN_ENGINE_BRUSH_GRAIN_HPP
#define ALADYN_ENGINE_BRUSH_GRAIN_HPP

#include "DabFootprint.hpp"
#include "../brush/BrushProfile.hpp"
#include "../../utils/MathUtils.hpp"

namespace aladyn::engine::raster {

// ─── O GRÃO DO PINCEL ───────────────────────────────────────────────────────
//
// A textura de altura do pincel (o dente do grafite, a cerda seca) lida num pixel de um dab. Antes era a mesma
// conta escrita duas vezes, no Pincel (DabRenderer) e no Lápis (PencilEngine); agora está aqui, com dois modos:
//
//   Móvel  a textura acompanha o carimbo (gira com ele e escala com o tamanho do pincel). Cada carimbo traz um
//          grão diferente, e com os carimbos se sobrepondo o grão se borra. É o que sempre foi.
//   Fixo   a textura fica presa ao canvas, como o grão do papel (0,002 de textura por px, vezes a escala): o mesmo
//          pixel tem sempre o mesmo grão, de qualquer carimbo e de qualquer traço, e o dente aparece de verdade.
//
// Em ambos, inverter, contraste e a curva da textura valem igual.
class BrushGrain {
public:
    explicit BrushGrain(const brush::BrushProfile& profile)
        : m_profile(profile),
          m_texture(profile.brushHeightTexture.get()),
          m_enabled(profile.brushGrainEnabled && profile.brushHeightTexture),
          m_fixed(profile.brushGrainMode == brush::GrainMode::Fixed),
          m_halfSpan((profile.brushGrainContrast != 1.0 && profile.brushGrainContrast > 0.0)
                         ? 0.5 / profile.brushGrainContrast : 0.0) {}

    [[nodiscard]] bool enabled() const noexcept { return m_enabled; }

    // `u`, `v`: onde o pixel cai no carimbo, de 0 a 1 (só o modo móvel os usa). 1 quando o grão está desligado.
    [[nodiscard]] double height(const DabPixel& pixel, double u, double v) const {
        if (!m_enabled) return 1.0;
        const double scale = m_profile.brushGrainScale;
        double height = m_fixed
            ? m_texture->sampleNormalized((static_cast<double>(pixel.gx) + 0.5) * kFixedPerPixel * scale,
                                          (static_cast<double>(pixel.gy) + 0.5) * kFixedPerPixel * scale,
                                          texture::TextureWrapMode::Repeat)
            : m_texture->sampleNormalized(u * scale, v * scale, texture::TextureWrapMode::Repeat);
        if (m_profile.brushGrainInvert) height = 1.0 - height;
        if (m_halfSpan > 0.0) height = utils::MathUtils::smoothstep(0.5 - m_halfSpan, 0.5 + m_halfSpan, height);
        return m_profile.brushTextureCurve.sample(height);
    }

private:
    static constexpr double kFixedPerPixel = 0.002;  // a mesma do grão do papel

    const brush::BrushProfile& m_profile;
    const texture::Texture2D* m_texture;
    bool m_enabled;
    bool m_fixed;
    double m_halfSpan;
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_BRUSH_GRAIN_HPP
