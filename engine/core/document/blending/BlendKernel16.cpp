#include "BlendKernel16Internal.hpp"
#include "BlendEquations16.hpp"
#include "BlendKernel.hpp"
#include "../../color/LinearColorSpace16.hpp"

namespace aladyn::engine::document::blending {

namespace {

using utils::ColorRGBA16;

// O alfa efetivo e os fatores da origem e do destino de um pixel que não é nem transparente nem opaco por cima.
// O alfa é calculado em double, igual à definição (`detail16::effectiveAlpha`): é ele que decide o atalho do alfa
// cheio (`>= 1.0`), e esse atalho tem de cair nos mesmos pixels nos dois lados.
struct Mix {
    float source;
    float destination;
    uint16_t alpha;
};

inline Mix mixOf(double srcA, uint16_t dstAlpha) noexcept {
    if (dstAlpha == 65535) {
        // Destino opaco: o alfa de saída é 1 e os fatores são o próprio alfa e o seu complemento.
        return Mix{static_cast<float>(srcA), static_cast<float>(1.0 - srcA), 65535};
    }
    const double dstA = detail16::unit(dstAlpha);
    const double outA = srcA + dstA * (1.0 - srcA);
    return Mix{static_cast<float>(srcA / outA), static_cast<float>(dstA * (1.0 - srcA) / outA), detail16::quantize(outA)};
}

// Normal, sRGB codificado: a mistura é direta nos valores de 16 bits.
void rowNormal16Encoded(const BlendPlan16& plan, const ColorRGBA16* src, ColorRGBA16* dst, size_t count) noexcept {
    for (size_t i = 0; i < count; ++i) {
        const ColorRGBA16 s = src[i];
        if (s.a == 0) continue;
        const double srcA = detail16::effectiveAlpha(s.a, plan.opacity);
        if (srcA <= 0.0) continue;
        if (srcA >= 1.0) {
            dst[i] = ColorRGBA16{s.r, s.g, s.b, 65535};
            continue;
        }
        const ColorRGBA16 d = dst[i];
        if (d.a == 0) {
            dst[i] = ColorRGBA16{s.r, s.g, s.b, detail16::quantize(srcA)};
            continue;
        }
        const Mix mix = mixOf(srcA, d.a);
        const auto channel = [&](uint16_t sourceChannel, uint16_t destinationChannel) noexcept {
            // fs + fd = 1 só até o arredondamento do float: o teto impede que 65535,0001 + 0,5 vire 65536.
            const float value = static_cast<float>(sourceChannel) * mix.source + static_cast<float>(destinationChannel) * mix.destination + 0.5f;
            return static_cast<uint16_t>(value < 65535.0f ? value : 65535.0f);
        };
        dst[i] = ColorRGBA16{channel(s.r, d.r), channel(s.g, d.g), channel(s.b, d.b), mix.alpha};
    }
}

// Qualquer outro caso (modos separáveis, Erase): a definição, um pixel por vez, com o desvio por modo já fora do
// laço da camada.
void rowGeneric16(const BlendPlan16& plan, const ColorRGBA16* src, ColorRGBA16* dst, size_t count) noexcept {
    for (size_t i = 0; i < count; ++i) {
        if (src[i].a == 0) continue;
        dst[i] = blendPixel16(src[i], plan.opacity, dst[i], plan.mode, plan.linearGamma);
    }
}

} // namespace

// Normal, gama linear. Cada ramo repete o de `detail16::normalBlend`, com as tabelas à mão.
void rowNormal16Linear(const BlendPlan16& plan, const ColorRGBA16* src, ColorRGBA16* dst, size_t count) noexcept {
    const color::Srgb16Tables& tables = color::srgb16Tables();
    for (size_t i = 0; i < count; ++i) {
        const ColorRGBA16 s = src[i];
        if (s.a == 0) continue;
        const double srcA = detail16::effectiveAlpha(s.a, plan.opacity);
        if (srcA <= 0.0) continue;
        if (srcA >= 1.0) {
            dst[i] = ColorRGBA16{s.r, s.g, s.b, 65535};
            continue;
        }
        const ColorRGBA16 d = dst[i];
        if (d.a == 0) {
            dst[i] = ColorRGBA16{s.r, s.g, s.b, detail16::quantize(srcA)};
            continue;
        }
        const Mix mix = mixOf(srcA, d.a);
        const auto channel = [&](uint16_t sourceChannel, uint16_t destinationChannel) noexcept {
            return color::linearToSrgb16(tables, tables.toLinear[sourceChannel] * mix.source +
                                                     tables.toLinear[destinationChannel] * mix.destination);
        };
        dst[i] = ColorRGBA16{channel(s.r, d.r), channel(s.g, d.g), channel(s.b, d.b), mix.alpha};
    }
}

BlendPlan16 BlendKernel16::plan(double opacity, LayerBlendMode mode, bool linearGamma) noexcept {
    BlendPlan16 result;
    result.opacity = opacity;
    result.mode = mode;
    result.linearGamma = linearGamma;
    result.run = rowGeneric16;
    if (mode == LayerBlendMode::Normal) {
        if (linearGamma) {
            (void)color::srgb16Tables();  // monta as tabelas aqui, uma vez, e não dentro de um laço paralelo
            // O nível de SIMD é um só para os dois kernels (`BlendKernel::activeLevel`, `forceLevel`). Opacidade
            // ínfima fica na escalar: o fator em float de um alfa efetivo tão pequeno não é o do double.
            result.run = (BlendKernel::activeLevel() == BlendSimdLevel::Avx2 && opacity >= 1e-12) ? rowNormal16LinearAvx2 : rowNormal16Linear;
        } else {
            result.run = rowNormal16Encoded;
        }
    }
    return result;
}

} // namespace aladyn::engine::document::blending
