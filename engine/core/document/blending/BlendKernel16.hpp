#ifndef ALADYN_ENGINE_BLEND_KERNEL_16_HPP
#define ALADYN_ENGINE_BLEND_KERNEL_16_HPP

#include "LayerBlendMode.hpp"
#include "../../../utils/ColorRGBA16.hpp"
#include <cstddef>

namespace aladyn::engine::document::blending {

// ─── MESCLAGEM POR LINHA, 16 BITS ────────────────────────────────────────────
//
// O que `BlendKernel` (BlendKernel.hpp) é para 8 bits. `blendPixel16` (BlendEquations16.hpp) é a definição de um
// pixel; o kernel recebe uma LINHA de origem e de destino e faz o mesmo que
//
//     for i: if (src[i].a != 0) dst[i] = blendPixel16(src[i], opacity, dst[i], mode, linearGamma);
//
// mas NÃO é igual bit a bit: o Normal (em gama linear e em sRGB codificado, que é o caminho de quase toda camada)
// tem um laço em float com as tabelas de `LinearColorSpace16.hpp`, e erra no máximo 1 nível de 16 bits contra a
// definição, o que `tests/native/blend16_checks.cpp` mede em milhões de pixels (diferença máxima e fração). Os
// demais casos (modos separáveis, Erase) rodam a própria definição pixel a pixel, com o desvio por modo fora do laço
// da camada: são idênticos à definição. Não há SIMD ainda: entra se a medição pedir.
struct BlendPlan16 {
    using RowFunction = void (*)(const BlendPlan16&, const utils::ColorRGBA16* src, utils::ColorRGBA16* dst, size_t count) noexcept;

    RowFunction run{nullptr};
    double opacity{1.0};
    LayerBlendMode mode{LayerBlendMode::Normal};
    bool linearGamma{true};
};

class BlendKernel16 {
public:
    // O plano de uma camada: montado uma vez, usado em todas as linhas (e threads: só lê).
    [[nodiscard]] static BlendPlan16 plan(double opacity, LayerBlendMode mode, bool linearGamma) noexcept;

    static void blendRow(const BlendPlan16& plan, const utils::ColorRGBA16* src, utils::ColorRGBA16* dst, size_t count) noexcept {
        plan.run(plan, src, dst, count);
    }
};

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_BLEND_KERNEL_16_HPP
