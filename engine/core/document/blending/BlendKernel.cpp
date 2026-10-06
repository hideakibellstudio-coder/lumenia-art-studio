#include "BlendKernel.hpp"
#include "BlendEquations.hpp"
#include "BlendKernelInternal.hpp"

#include <atomic>
#include <cstring>

namespace aladyn::engine::document::blending {

namespace {

// ─── NÍVEL DE SIMD ───────────────────────────────────────────────────────────

constexpr int kNotDetected = -1;
std::atomic<int> g_level{kNotDetected};

BlendSimdLevel detectBest() noexcept {
    return cpuHasAvx2() ? BlendSimdLevel::Avx2 : BlendSimdLevel::Scalar;
}

// ─── LINHAS ──────────────────────────────────────────────────────────────────

// Qualquer caso sem laço próprio: a definição, um pixel por vez, com o desvio por modo já fora do laço
// da camada.
void rowGeneric(const BlendPlan& plan, const utils::ColorRGBA* src, utils::ColorRGBA* dst, size_t count) noexcept {
    for (size_t i = 0; i < count; ++i) {
        if (src[i].a == 0) continue;
        dst[i] = blendPixel(src[i], plan.opacity, dst[i], plan.mode, plan.linearGamma, plan.deepColor);
    }
}

// Normal, gama linear, 8 bits. Cada ramo repete o de `blendPixel` e `blendLinearNormalOpaque`
// (LinearColorSpace.hpp), com as tabelas e o alfa por valor já à mão; destino com alfa vai à definição.
void rowNormalLinear8Scalar(const BlendPlan& plan, const utils::ColorRGBA* src, utils::ColorRGBA* dst, size_t count) noexcept {
    const KernelTables& tables = *plan.tables;
    for (size_t i = 0; i < count; ++i) {
        const utils::ColorRGBA s = src[i];
        if (s.a == 0) continue;
        const utils::ColorRGBA d = dst[i];
        if (d.a != 255) {
            dst[i] = blendPixel(s, plan.opacity, d, plan.mode, true, false);
            continue;
        }
        const float alpha = plan.alphaF[s.a];
        if (alpha <= 0.0f) continue;
        if (alpha >= 1.0f) {
            dst[i] = utils::ColorRGBA{s.r, s.g, s.b, 255};
            continue;
        }
        const float inverse = 1.0f - alpha;
        const auto channel = [&](uint8_t sourceChannel, uint8_t destinationChannel) noexcept {
            const float linear = tables.srgbToLinear[sourceChannel] * alpha + tables.srgbToLinear[destinationChannel] * inverse;
            int index = static_cast<int>(linear * 4095.0f + 0.5f);
            index = index < 0 ? 0 : (index > 4095 ? 4095 : index);
            return tables.linearToSrgb[index];
        };
        dst[i] = utils::ColorRGBA{channel(s.r, d.r), channel(s.g, d.g), channel(s.b, d.b), 255};
    }
}

} // namespace

const KernelTables& kernelTables() noexcept {
    static const KernelTables tables = [] {
        KernelTables copy{};
        const color::LinearLutTables& source = color::getLinearLutTables();
        std::memcpy(copy.srgbToLinear, source.sRGB_to_Linear, sizeof copy.srgbToLinear);
        std::memcpy(copy.linearToSrgb, source.Linear_to_sRGB, 4096);
        return copy;  // as 8 posições finais ficam em 0
    }();
    return tables;
}

BlendSimdLevel BlendKernel::bestAvailableLevel() noexcept {
    return detectBest();
}

BlendSimdLevel BlendKernel::activeLevel() noexcept {
    int level = g_level.load(std::memory_order_relaxed);
    if (level == kNotDetected) {
        level = static_cast<int>(detectBest());
        g_level.store(level, std::memory_order_relaxed);
    }
    return static_cast<BlendSimdLevel>(level);
}

bool BlendKernel::forceLevel(BlendSimdLevel level) noexcept {
    if (level == BlendSimdLevel::Avx2 && !cpuHasAvx2()) return false;
    g_level.store(static_cast<int>(level), std::memory_order_relaxed);
    return true;
}

BlendPlan BlendKernel::plan(double opacity, LayerBlendMode mode, bool linearGamma, bool deepColor) noexcept {
    BlendPlan result;
    result.opacity = opacity;
    result.mode = mode;
    result.linearGamma = linearGamma;
    result.deepColor = deepColor;
    result.run = rowGeneric;
    if (mode == LayerBlendMode::Normal && linearGamma && !deepColor) {
        result.tables = &kernelTables();
        for (int a = 0; a < 256; ++a) {
            result.alphaF[a] = static_cast<float>((static_cast<double>(a) / 255.0) * opacity);
        }
        result.run = (activeLevel() == BlendSimdLevel::Avx2) ? rowNormalLinear8Avx2 : rowNormalLinear8Scalar;
    }
    return result;
}

} // namespace aladyn::engine::document::blending
