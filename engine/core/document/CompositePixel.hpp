#ifndef ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_PIXEL_HPP
#define ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_PIXEL_HPP

#include "../canvas/PixelFormat.hpp"
#include "../../utils/ColorRGBA.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include "blending/BlendEquations.hpp"
#include "blending/BlendEquations16.hpp"
#include "blending/BlendKernel.hpp"
#include "blending/BlendKernel16.hpp"

#include <cstddef>

namespace aladyn::engine::document::internal {

// O que a composição precisa saber do pixel que compõe. `GroupBlender` e `LayerCompositePass` são escritos uma vez
// para `Pixel` e instanciados para os dois formatos; cada formato entra aqui com o seu plano de mesclagem de linha,
// a sua definição de um pixel e o alfa em [0, 1].
template <typename Pixel>
struct CompositePixel;

template <>
struct CompositePixel<utils::ColorRGBA> {
    using Plan = blending::BlendPlan;
    static constexpr canvas::PixelFormat kFormat = canvas::PixelFormat::RGBA8;

    static Plan plan(double opacity, LayerBlendMode mode, bool linearGamma, bool deepColor) noexcept {
        return blending::BlendKernel::plan(opacity, mode, linearGamma, deepColor);
    }
    static void blendRow(const Plan& plan, const utils::ColorRGBA* src, utils::ColorRGBA* dst, size_t count) noexcept {
        blending::BlendKernel::blendRow(plan, src, dst, count);
    }
    static utils::ColorRGBA blendPixel(
        utils::ColorRGBA src, double opacity, utils::ColorRGBA dst, LayerBlendMode mode, bool linearGamma, bool deepColor
    ) noexcept {
        return blending::blendPixel(src, opacity, dst, mode, linearGamma, deepColor);
    }
    static double alphaUnit(utils::ColorRGBA pixel) noexcept { return static_cast<double>(pixel.a) / 255.0; }
};

// Nos 16 bits não há Deep Color: a conta é sempre em precisão alta e arredondada (`BlendEquations16.hpp`).
template <>
struct CompositePixel<utils::ColorRGBA16> {
    using Plan = blending::BlendPlan16;
    static constexpr canvas::PixelFormat kFormat = canvas::PixelFormat::RGBA16;

    static Plan plan(double opacity, LayerBlendMode mode, bool linearGamma, bool /*deepColor*/) noexcept {
        return blending::BlendKernel16::plan(opacity, mode, linearGamma);
    }
    static void blendRow(const Plan& plan, const utils::ColorRGBA16* src, utils::ColorRGBA16* dst, size_t count) noexcept {
        blending::BlendKernel16::blendRow(plan, src, dst, count);
    }
    static utils::ColorRGBA16 blendPixel(
        utils::ColorRGBA16 src, double opacity, utils::ColorRGBA16 dst, LayerBlendMode mode, bool linearGamma, bool /*deepColor*/
    ) noexcept {
        return blending::blendPixel16(src, opacity, dst, mode, linearGamma);
    }
    static double alphaUnit(utils::ColorRGBA16 pixel) noexcept { return blending::detail16::unit(pixel.a); }
};

} // namespace aladyn::engine::document::internal

#endif // ALADYN_ENGINE_DOCUMENT_INTERNAL_COMPOSITE_PIXEL_HPP
