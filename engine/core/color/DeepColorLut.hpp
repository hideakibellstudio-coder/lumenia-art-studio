#ifndef ALADYN_ENGINE_DEEP_COLOR_LUT_HPP
#define ALADYN_ENGINE_DEEP_COLOR_LUT_HPP

#include "LinearColorSpace.hpp"
#include "../../utils/ColorRGBA.hpp"
#include <cstdint>

namespace aladyn::engine::color {

// ─── DEEP COLOR SEM `pow` POR PIXEL ──────────────────────────────────────────
//
// `blendLinearNormalHighPrecision` (LinearColorSpace.hpp) é a definição do Deep Color: três `pow` para
// levar origem e destino de cada canal ao espaço linear (seis por pixel) e mais três para voltar ao
// sRGB. Medido em 2026-10-02 custava 246 ns por pixel, 16 vezes o caminho padrão (recompor 4096² com 10
// camadas: 7,6 s). Esta tabela dá o MESMO resultado, bit a bit, sem nenhum `pow` no laço:
//
//   toLinear   o `toLinear` da definição para cada um dos 256 valores de canal (a mesma expressão,
//              calculada uma vez);
//   threshold  `linearToSRGBPrecise` só devolve inteiros de 0 a 255 e nunca decresce: então ela é
//              uma escada. threshold[k] é o MENOR double cuja imagem é >= k, achado por bisecção
//              sobre os próprios doubles com a função de referência (nada é aproximado);
//   lowest/highest  o valor da escada nas duas bordas de cada um de 4096 baldes de [0, 1]: a busca
//              começa em `lowest` e sobe no máximo até `highest` (um ou dois degraus).
//
// Quem garante a igualdade é tests/native/blend_kernel_checks.cpp (milhões de doubles, os vizinhos de
// cada degrau e a mesclagem inteira contra a definição).
struct DeepColorLut {
    static constexpr int kBuckets = 4096;

    double toLinear[256];
    double threshold[257];
    uint8_t lowest[kBuckets + 1];
    uint8_t highest[kBuckets + 1];

    DeepColorLut() noexcept;
};

[[nodiscard]] const DeepColorLut& deepColorLut() noexcept;

[[nodiscard]] inline uint8_t linearToSRGBPreciseFast(const DeepColorLut& lut, double linear) noexcept {
    // Mesma saturação da definição; um NaN (que a definição deixa indefinido) cai em 0.
    const double x = linear > 1.0 ? 1.0 : (linear >= 0.0 ? linear : 0.0);
    const int bucket = static_cast<int>(x * DeepColorLut::kBuckets);
    unsigned step = lut.lowest[bucket];
    const unsigned top = lut.highest[bucket];
    while (step < top && x >= lut.threshold[step + 1]) ++step;
    return static_cast<uint8_t>(step);
}

// `blendLinearNormalHighPrecision` com as tabelas: mesma ordem de contas, mesmos desvios.
[[nodiscard]] inline utils::ColorRGBA blendLinearNormalDeep(
    const DeepColorLut& lut, utils::ColorRGBA src, double srcA, utils::ColorRGBA dst
) noexcept {
    if (srcA <= 0.0) return dst;
    if (dst.a == 0) {
        return utils::ColorRGBA{
            src.r, src.g, src.b,
            static_cast<uint8_t>(std::clamp(std::lround(srcA * 255.0), 0l, 255l))
        };
    }
    const double dstA = static_cast<double>(dst.a) / 255.0;
    const double outA = srcA + dstA * (1.0 - srcA);
    if (outA <= 0.0) return utils::ColorRGBA{0, 0, 0, 0};
    const double srcFactor = srcA / outA;
    const double dstFactor = dstA * (1.0 - srcA) / outA;
    return utils::ColorRGBA{
        linearToSRGBPreciseFast(lut, lut.toLinear[src.r] * srcFactor + lut.toLinear[dst.r] * dstFactor),
        linearToSRGBPreciseFast(lut, lut.toLinear[src.g] * srcFactor + lut.toLinear[dst.g] * dstFactor),
        linearToSRGBPreciseFast(lut, lut.toLinear[src.b] * srcFactor + lut.toLinear[dst.b] * dstFactor),
        static_cast<uint8_t>(std::clamp(std::lround(outA * 255.0), 0l, 255l))
    };
}

} // namespace aladyn::engine::color

#endif // ALADYN_ENGINE_DEEP_COLOR_LUT_HPP
