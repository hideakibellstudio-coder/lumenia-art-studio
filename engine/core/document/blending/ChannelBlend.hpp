#ifndef ALADYN_ENGINE_CHANNEL_BLEND_HPP
#define ALADYN_ENGINE_CHANNEL_BLEND_HPP

#include "LayerBlendMode.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document::blending {

// ─── A EQUAÇÃO DE CANAL DE CADA MODO ─────────────────────────────────────────
//
// `s` é a camada e `d` o destino, os dois em [0, 1] e codificados em sRGB; o resultado é a cor que os dois
// formam num canal, antes de interpolar com o alfa. Esta é a ÚNICA tabela de equações: a mesclagem de 8 bits
// (`BlendEquations.hpp`) e a de 16 bits (`BlendEquations16.hpp`) chamam o mesmo caso, então um modo novo entra
// aqui uma vez e vale nas duas.
//
// O modo é escolhido uma vez por pixel (não por canal: escolher por canal custou 30% no Darken): `visit` recebe
// a equação como um lambda e entra inline nos três canais. Um modo sem equação própria (PassThrough) usa a cor
// da camada, como o Normal. O Erase não passa aqui: só mexe no alfa de destino.
template <typename Visitor>
inline auto dispatchChannelBlend(LayerBlendMode mode, Visitor&& visit) {
    switch (mode) {
        case LayerBlendMode::Multiply:
            return visit([](double s, double d) noexcept { return s * d; });
        case LayerBlendMode::Screen:
            return visit([](double s, double d) noexcept { return 1.0 - (1.0 - s) * (1.0 - d); });
        case LayerBlendMode::Overlay:
            return visit([](double s, double d) noexcept {
                return (d < 0.5) ? (2.0 * d * s) : (1.0 - 2.0 * (1.0 - d) * (1.0 - s));
            });
        case LayerBlendMode::Darken:
            return visit([](double s, double d) noexcept { return std::min(s, d); });
        case LayerBlendMode::Lighten:
            return visit([](double s, double d) noexcept { return std::max(s, d); });
        case LayerBlendMode::ColorDodge:
            return visit([](double s, double d) noexcept { return std::min(1.0, d / (1.0 - s + 1e-5)); });
        case LayerBlendMode::ColorBurn:
            return visit([](double s, double d) noexcept { return 1.0 - std::min(1.0, (1.0 - d) / (s + 1e-5)); });
        case LayerBlendMode::Difference:
            return visit([](double s, double d) noexcept { return std::abs(d - s); });
        case LayerBlendMode::Exclusion:
            return visit([](double s, double d) noexcept { return d + s - 2.0 * d * s; });
        case LayerBlendMode::Add:
            return visit([](double s, double d) noexcept { return std::min(1.0, d + s); });
        case LayerBlendMode::SoftLight:
            return visit([](double s, double d) noexcept {
                if (s <= 0.5) {
                    return d - (1.0 - 2.0 * s) * d * (1.0 - d);
                } else {
                    const double dVal = (d <= 0.25) ? (((16.0 * d - 12.0) * d + 4.0) * d) : std::sqrt(d);
                    return d + (2.0 * s - 1.0) * (dVal - d);
                }
            });
        case LayerBlendMode::HardLight:
            return visit([](double s, double d) noexcept {
                return (s <= 0.5) ? (2.0 * s * d) : (1.0 - 2.0 * (1.0 - s) * (1.0 - d));
            });
        case LayerBlendMode::VividLight:
            return visit([](double s, double d) noexcept {
                if (s <= 0.5) {
                    const double twoS = 2.0 * s;
                    return 1.0 - std::min(1.0, (1.0 - d) / (twoS + 1e-5));
                } else {
                    const double twoSMinus1 = 2.0 * (s - 0.5);
                    return std::min(1.0, d / (1.0 - twoSMinus1 + 1e-5));
                }
            });
        case LayerBlendMode::LinearLight:
            return visit([](double s, double d) noexcept {
                return std::clamp(d + 2.0 * s - 1.0, 0.0, 1.0);
            });
        case LayerBlendMode::PinLight:
            return visit([](double s, double d) noexcept {
                return (s < 0.5) ? std::min(d, 2.0 * s) : std::max(d, 2.0 * (s - 0.5));
            });
        case LayerBlendMode::HardMix:
            return visit([](double s, double d) noexcept {
                double vivid = 0.0;
                if (s <= 0.5) {
                    const double twoS = 2.0 * s;
                    vivid = 1.0 - std::min(1.0, (1.0 - d) / (twoS + 1e-5));
                } else {
                    const double twoSMinus1 = 2.0 * (s - 0.5);
                    vivid = std::min(1.0, d / (1.0 - twoSMinus1 + 1e-5));
                }
                return (vivid >= 1.0 - 1e-5) ? 1.0 : 0.0;
            });
        case LayerBlendMode::Subtract:
            return visit([](double s, double d) noexcept {
                return std::max(0.0, d - s);
            });
        case LayerBlendMode::Normal:
        default:
            return visit([](double s, double) noexcept { return s; });
    }
}

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_CHANNEL_BLEND_HPP
