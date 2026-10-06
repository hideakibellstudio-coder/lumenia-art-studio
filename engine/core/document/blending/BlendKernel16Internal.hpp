#ifndef ALADYN_ENGINE_BLEND_KERNEL_16_INTERNAL_HPP
#define ALADYN_ENGINE_BLEND_KERNEL_16_INTERNAL_HPP

// Parte privada do kernel de 16 bits (BlendKernel16.cpp e BlendKernel16Avx2.cpp). Não é incluída fora da pasta.

#include "BlendKernel16.hpp"

namespace aladyn::engine::document::blending {

// O Normal em gama linear, o caso de quase toda camada. A linha escalar define o resultado; a de AVX2 (oito pixels
// por vez, `gather` nas tabelas) dá os MESMOS bytes, e entrega à escalar o que não é destino opaco nos oito pixels.
void rowNormal16Linear(const BlendPlan16& plan, const utils::ColorRGBA16* src, utils::ColorRGBA16* dst, size_t count) noexcept;
void rowNormal16LinearAvx2(const BlendPlan16& plan, const utils::ColorRGBA16* src, utils::ColorRGBA16* dst, size_t count) noexcept;

} // namespace aladyn::engine::document::blending

#endif // ALADYN_ENGINE_BLEND_KERNEL_16_INTERNAL_HPP
