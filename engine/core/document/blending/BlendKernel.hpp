#ifndef ALADYN_ENGINE_BLEND_KERNEL_HPP
#define ALADYN_ENGINE_BLEND_KERNEL_HPP

#include "LayerBlendMode.hpp"
#include "../../../utils/ColorRGBA.hpp"
#include <cstddef>

namespace aladyn::engine::document::blending {

// ─── MESCLAGEM POR LINHA ─────────────────────────────────────────────────────
//
// `blendPixel` (BlendEquations.hpp) é a definição de um pixel. Chamá-la pixel a pixel custava, medido em
// 2026-10-02, 12 ns no Normal em gama linear (o caminho de quase toda camada), 39 ns no Overlay e 246 ns no
// Deep Color; recompor 4096² com 10 camadas levava 476 ms no padrão e 7,6 s no Deep Color. O kernel recebe
// uma LINHA de origem e de destino e faz o mesmo que
//
//     for i: if (src[i].a != 0) dst[i] = blendPixel(src[i], opacity, dst[i], mode, linearGamma, deepColor);
//
// pixel por pixel IGUAL, bit a bit (não é aproximação: tests/native/blend_kernel_checks.cpp compara as duas
// contas em milhões de pixels e em cada nível de SIMD). O que muda é o custo:
//
//   - o desvio por modo, gama e Deep Color é feito uma vez por camada, no plano, não por pixel;
//   - o Normal em gama linear de 8 bits tem um laço próprio com tabelas fixas (escalar) e outro em
//     AVX2 (oito pixels por vez, `gather` nas tabelas), escolhido na hora de rodar pela CPU: um só
//     binário serve ao processador que tem AVX2 e ao que não tem (o build distribuído continua escalar);
//   - o Deep Color usa tabelas exatas (core/color/DeepColorLut.hpp) no lugar de nove `pow` por pixel.
//
// Os demais casos (modos separáveis, sRGB codificado) usam `blendPixel` por pixel dentro do laço da linha.
enum class BlendSimdLevel { Scalar, Avx2 };

struct KernelTables;

struct BlendPlan {
    using RowFunction = void (*)(const BlendPlan&, const utils::ColorRGBA* src, utils::ColorRGBA* dst, size_t count) noexcept;

    RowFunction run{nullptr};
    double opacity{1.0};
    LayerBlendMode mode{LayerBlendMode::Normal};
    bool linearGamma{true};
    bool deepColor{false};
    const KernelTables* tables{nullptr};
    // Normal em gama linear de 8 bits: o alfa efetivo de cada alfa de origem, como float, pela mesma
    // conta de `blendPixel` ((a / 255.0) * opacidade, depois float).
    float alphaF[256]{};
};

class BlendKernel {
public:
    // O plano de uma camada: montado uma vez, usado em todas as linhas (e threads: só lê).
    [[nodiscard]] static BlendPlan plan(double opacity, LayerBlendMode mode, bool linearGamma, bool deepColor) noexcept;

    static void blendRow(const BlendPlan& plan, const utils::ColorRGBA* src, utils::ColorRGBA* dst, size_t count) noexcept {
        plan.run(plan, src, dst, count);
    }

    // O nível em uso (o melhor que a CPU tem, salvo `forceLevel`) e o melhor disponível.
    [[nodiscard]] static BlendSimdLevel activeLevel() noexcept;
    [[nodiscard]] static BlendSimdLevel bestAvailableLevel() noexcept;
    // Para os testes: `false` se a CPU não tem o nível pedido. Vale para os planos montados depois.
    static bool forceLevel(BlendSimdLevel level) noexcept;
};

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_BLEND_KERNEL_HPP
