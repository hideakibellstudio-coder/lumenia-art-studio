#ifndef ALADYN_ENGINE_BLEND_EQUATIONS_16_HPP
#define ALADYN_ENGINE_BLEND_EQUATIONS_16_HPP

#include "ChannelBlend.hpp"
#include "LayerBlendMode.hpp"
#include "../../../utils/ColorRGBA16.hpp"
#include "../../color/LinearColorSpace16.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::document::blending {

// ─── MESCLAGEM DE UM PIXEL DE 16 BITS: A DEFINIÇÃO ───────────────────────────
//
// O que `blendPixel` (BlendEquations.hpp) é para 8 bits, esta é para 16: a DEFINIÇÃO em double, lenta e clara.
// O kernel de linha (`BlendKernel16.hpp`) é o que roda; os testes (`tests/native/blend16_checks.cpp`) medem o quanto
// ele se afasta daqui.
//
// Diferenças deliberadas em relação aos 8 bits, todas porque o buffer é de 16 bits e não há o que economizar:
//   - não existe Deep Color: toda conta é em double e o resultado é arredondado ao inteiro mais próximo
//     (os 8 bits truncam, a menos que o Deep Color esteja ligado);
//   - o atalho exato é o do alfa cheio: Normal com alfa efetivo 1 devolve a cor da camada e alfa 65535 sem passar
//     pela gama (nos 8 bits o atalho só vale com destino opaco), e destino transparente devolve a cor da camada
//     com o alfa dela;
//   - o Normal em gama linear usa a curva sRGB exata (`LinearColorSpace16.hpp`), não a tabela de 12 bits.
// O que não muda: a equação de cada modo (`ChannelBlend.hpp`), o alpha over e o Erase (só o alfa de destino).

namespace detail16 {

inline constexpr double kInv65535 = 1.0 / 65535.0;

// O canal em [0, 1]. O fundo de escala é 1 exato (65535 * (1/65535) pode dar 0,9999999999999999).
inline double unit(uint16_t channel) noexcept {
    return channel == 65535 ? 1.0 : static_cast<double>(channel) * kInv65535;
}

// O alfa efetivo de uma camada: o alfa do pixel vezes a opacidade. O kernel de linha calcula igual.
inline double effectiveAlpha(uint16_t alpha, double layerOpacity) noexcept {
    return unit(alpha) * layerOpacity;
}

inline uint16_t quantize(double value) noexcept {
    return static_cast<uint16_t>(std::clamp(std::lround(value * 65535.0), 0l, 65535l));
}

inline utils::ColorRGBA16 eraseAlpha(utils::ColorRGBA16 dst, double srcA) noexcept {
    return utils::ColorRGBA16{dst.r, dst.g, dst.b, quantize(std::max(0.0, unit(dst.a) * (1.0 - srcA)))};
}

inline utils::ColorRGBA16 normalEncoded(utils::ColorRGBA16 src, double srcA, utils::ColorRGBA16 dst) noexcept {
    const double dstA = unit(dst.a);
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return utils::ColorRGBA16{0, 0, 0, 0};
    const double factorSrc = srcA / outA;
    const double factorDst = dstA * (1.0 - srcA) / outA;
    return utils::ColorRGBA16{
        quantize(unit(src.r) * factorSrc + unit(dst.r) * factorDst),
        quantize(unit(src.g) * factorSrc + unit(dst.g) * factorDst),
        quantize(unit(src.b) * factorSrc + unit(dst.b) * factorDst),
        quantize(outA)
    };
}

inline utils::ColorRGBA16 normalLinear(utils::ColorRGBA16 src, double srcA, utils::ColorRGBA16 dst) noexcept {
    const double dstA = unit(dst.a);
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return utils::ColorRGBA16{0, 0, 0, 0};
    const double factorSrc = srcA / outA;
    const double factorDst = dstA * (1.0 - srcA) / outA;
    const auto channel = [&](uint16_t s, uint16_t d) noexcept {
        return color::linearToSrgb16Reference(color::srgbToLinearReference(unit(s)) * factorSrc +
                                              color::srgbToLinearReference(unit(d)) * factorDst);
    };
    return utils::ColorRGBA16{channel(src.r, dst.r), channel(src.g, dst.g), channel(src.b, dst.b), quantize(outA)};
}

inline utils::ColorRGBA16 normalBlend(
    utils::ColorRGBA16 src, double srcA, utils::ColorRGBA16 dst, bool linearGamma
) noexcept {
    if (srcA >= 1.0) return utils::ColorRGBA16{src.r, src.g, src.b, 65535};
    if (dst.a == 0) return utils::ColorRGBA16{src.r, src.g, src.b, quantize(srcA)};
    return linearGamma ? normalLinear(src, srcA, dst) : normalEncoded(src, srcA, dst);
}

// Alpha over de um modo separável, na codificação sRGB (como nos 8 bits).
template <typename ChannelBlend>
inline utils::ColorRGBA16 overWith(
    ChannelBlend blend, utils::ColorRGBA16 src, double srcA, utils::ColorRGBA16 dst
) noexcept {
    const double dstA = unit(dst.a);
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return utils::ColorRGBA16{0, 0, 0, 0};
    const auto channel = [&](uint16_t srcChannel, uint16_t dstChannel) noexcept {
        const double s = unit(srcChannel);
        const double d = unit(dstChannel);
        return (blend(s, d) * srcA + d * dstA * (1.0 - srcA)) / outA;
    };
    return utils::ColorRGBA16{quantize(channel(src.r, dst.r)), quantize(channel(src.g, dst.g)),
                              quantize(channel(src.b, dst.b)), quantize(outA)};
}

} // namespace detail16

inline utils::ColorRGBA16 blendPixel16(
    utils::ColorRGBA16 src,
    double layerOpacity,
    utils::ColorRGBA16 dst,
    LayerBlendMode mode,
    bool linearGamma = true
) noexcept {
    if (src.a == 0) return dst;
    const double srcA = detail16::effectiveAlpha(src.a, layerOpacity);
    if (srcA <= 0.0) return dst;

    if (mode == LayerBlendMode::Erase) return detail16::eraseAlpha(dst, srcA);
    if (mode == LayerBlendMode::Normal) return detail16::normalBlend(src, srcA, dst, linearGamma);
    return dispatchChannelBlend(mode, [&](auto blend) noexcept { return detail16::overWith(blend, src, srcA, dst); });
}

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_BLEND_EQUATIONS_16_HPP
