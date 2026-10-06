#ifndef ALADYN_ENGINE_BLEND_EQUATIONS_HPP
#define ALADYN_ENGINE_BLEND_EQUATIONS_HPP

#include "ChannelBlend.hpp"
#include "LayerBlendMode.hpp"
#include "../../../utils/ColorRGBA.hpp"
#include "../../color/DeepColorLut.hpp"
#include "../../color/LinearColorSpace.hpp"
#include <algorithm>
#include <array>
#include <cmath>

namespace aladyn::engine::document::blending {

// ─── MATEMÁTICA PURA DE MESCLAGEM DE PIXEL (ALPHA OVER + BLEND MODES) ───────
//
// `blendPixel` decide o caminho; cada caminho é uma função com nome:
//   - atalhos exatos do Normal com opacidade total;
//   - Erase (só o alfa de destino);
//   - Normal em linear (LinearColorSpace.hpp) ou em sRGB codificado;
//   - os demais modos: a equação de um canal por caso (`separableBlend`) e o alpha over.
// A separação não muda nenhum pixel: tests/golden/compositing_golden.json.

namespace detail {

inline uint8_t quantize(double value, bool deepColor) noexcept {
    const double scaled = std::clamp(value * 255.0, 0.0, 255.0);
    return static_cast<uint8_t>(deepColor ? std::lround(scaled) : scaled);
}

// c / 255.0 para cada valor de canal, calculado na compilação: a divisão IEEE é a mesma em tempo de
// compilação e de execução, então a tabela dá o mesmo double que a conta, sem a divisão (o Overlay gastava
// seis por pixel).
inline constexpr std::array<double, 256> kUnitOfChannel = [] {
    std::array<double, 256> table{};
    for (int channel = 0; channel < 256; ++channel) table[static_cast<size_t>(channel)] = static_cast<double>(channel) / 255.0;
    return table;
}();

inline double toUnit(uint8_t channel) noexcept {
    return kUnitOfChannel[channel];
}

// Resultado exato do Normal com opacidade total, sem Deep Color. `false` quando o caso
// precisa da conta completa.
inline bool normalAtFullOpacity(
    utils::ColorRGBA src, utils::ColorRGBA dst, bool linearGamma, utils::ColorRGBA& out
) noexcept {
    if (src.a == 255) {
        out = src;
        return true;
    }
    if (dst.a != 255 || linearGamma) return false;
    const uint32_t sA = src.a;
    const uint32_t invA = 255 - sA;
    out = utils::ColorRGBA{
        static_cast<uint8_t>((src.r * sA + dst.r * invA) / 255),
        static_cast<uint8_t>((src.g * sA + dst.g * invA) / 255),
        static_cast<uint8_t>((src.b * sA + dst.b * invA) / 255),
        255
    };
    return true;
}

inline utils::ColorRGBA eraseAlpha(utils::ColorRGBA dst, double srcA) noexcept {
    const double dstA = toUnit(dst.a);
    const double newA = std::max(0.0, dstA * (1.0 - srcA));
    return utils::ColorRGBA{dst.r, dst.g, dst.b, static_cast<uint8_t>(std::clamp(newA * 255.0, 0.0, 255.0))};
}

// Mistura sRGB direta (compatível com pipelines que mantêm a gama codificada). Em modo Deep
// Color o cálculo continua em double e a quantização final usa arredondamento, evitando a
// perda sistemática causada por truncar cada composição intermediária.
inline utils::ColorRGBA normalEncoded(
    utils::ColorRGBA src, double srcA, utils::ColorRGBA dst, bool deepColor
) noexcept {
    const double dstA = toUnit(dst.a);
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return utils::ColorRGBA{0, 0, 0, 0};
    const double factorSrc = srcA / outA;
    const double factorDst = dstA * (1.0 - srcA) / outA;
    return utils::ColorRGBA{
        quantize(toUnit(src.r) * factorSrc + toUnit(dst.r) * factorDst, deepColor),
        quantize(toUnit(src.g) * factorSrc + toUnit(dst.g) * factorDst, deepColor),
        quantize(toUnit(src.b) * factorSrc + toUnit(dst.b) * factorDst, deepColor),
        quantize(outA, deepColor)
    };
}

inline utils::ColorRGBA normalBlend(
    utils::ColorRGBA src, double srcA, utils::ColorRGBA dst, bool linearGamma, bool deepColor
) noexcept {
    if (!linearGamma) return normalEncoded(src, srcA, dst, deepColor);
    if (deepColor) return color::blendLinearNormalDeep(color::deepColorLut(), src, srcA, dst);
    if (dst.a == 255) return color::blendLinearNormalOpaque(src, static_cast<float>(srcA), dst);
    return color::blendLinearNormal(src, static_cast<float>(srcA), dst);
}

// Alpha over de um modo separável: `blend(s, d)` é a cor que a camada (s) e o destino (d)
// formam num canal, antes de interpolar com o alfa. O modo é escolhido uma vez por pixel
// (`separableBlend`) e a função entra inline nos três canais.
template <typename ChannelBlend>
inline utils::ColorRGBA overWith(
    ChannelBlend blend, utils::ColorRGBA src, double srcA, utils::ColorRGBA dst, bool deepColor
) noexcept {
    const double dstA = toUnit(dst.a);
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return utils::ColorRGBA{0, 0, 0, 0};

    const auto channel = [&](uint8_t srcChannel, uint8_t dstChannel) noexcept {
        const double s = toUnit(srcChannel);
        const double d = toUnit(dstChannel);
        return (blend(s, d) * srcA + d * dstA * (1.0 - srcA)) / outA;
    };
    return utils::ColorRGBA{
        quantize(channel(src.r, dst.r), deepColor),
        quantize(channel(src.g, dst.g), deepColor),
        quantize(channel(src.b, dst.b), deepColor),
        quantize(outA, deepColor)
    };
}

// Um caso por modo separável (a equação de canal mora em `ChannelBlend.hpp`, a mesma que a mesclagem de 16 bits usa).
inline utils::ColorRGBA separableBlend(
    LayerBlendMode mode, utils::ColorRGBA src, double srcA, utils::ColorRGBA dst, bool deepColor
) noexcept {
    return dispatchChannelBlend(mode, [&](auto blend) noexcept {
        return overWith(blend, src, srcA, dst, deepColor);
    });
}

} // namespace detail

inline utils::ColorRGBA blendPixel(
    utils::ColorRGBA src,
    double layerOpacity,
    utils::ColorRGBA dst,
    LayerBlendMode mode,
    bool linearGamma = true,
    bool deepColor = false
) noexcept {
    if (src.a == 0) return dst;

    utils::ColorRGBA exact{};
    if (mode == LayerBlendMode::Normal && layerOpacity == 1.0 && !deepColor &&
        detail::normalAtFullOpacity(src, dst, linearGamma, exact)) {
        return exact;
    }

    const double srcA = (static_cast<double>(src.a) / 255.0) * layerOpacity;
    if (srcA <= 0.0) return dst;

    if (mode == LayerBlendMode::Erase) return detail::eraseAlpha(dst, srcA);
    if (mode == LayerBlendMode::Normal) return detail::normalBlend(src, srcA, dst, linearGamma, deepColor);
    return detail::separableBlend(mode, src, srcA, dst, deepColor);
}

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_BLEND_EQUATIONS_HPP
