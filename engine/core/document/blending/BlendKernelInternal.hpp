#ifndef ALADYN_ENGINE_BLEND_KERNEL_INTERNAL_HPP
#define ALADYN_ENGINE_BLEND_KERNEL_INTERNAL_HPP

// Parte privada do kernel de mesclagem (BlendKernel.cpp e BlendKernelAvx2.cpp). Não é incluída fora da pasta.

#include "BlendKernel.hpp"
#include <cstdint>

namespace aladyn::engine::document::blending {

// As duas tabelas do Normal em gama linear de 8 bits, as de LinearColorSpace.hpp copiadas para um bloco
// alinhado e com folga no fim: o `gather` de bytes do AVX2 lê 4 bytes a partir de cada posição.
struct KernelTables {
    alignas(32) float srgbToLinear[256];
    alignas(32) uint8_t linearToSrgb[4096 + 8];
};

[[nodiscard]] const KernelTables& kernelTables() noexcept;

// BlendKernelAvx2.cpp. Em outra arquitetura ou compilador sem AVX2, `cpuHasAvx2` é falso e a linha nunca é usada.
[[nodiscard]] bool cpuHasAvx2() noexcept;
void rowNormalLinear8Avx2(const BlendPlan& plan, const utils::ColorRGBA* src, utils::ColorRGBA* dst, size_t count) noexcept;

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_BLEND_KERNEL_INTERNAL_HPP
