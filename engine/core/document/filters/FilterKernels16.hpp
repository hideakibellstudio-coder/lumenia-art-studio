#ifndef ALADYN_ENGINE_FILTER_KERNELS_16_HPP
#define ALADYN_ENGINE_FILTER_KERNELS_16_HPP

// Os sete núcleos de filtro para um buffer de 16 bits por canal (`FilterKernels.hpp` é o de 8 bits). Cabeçalho INTERNO
// como aquele: o ponto de entrada continua sendo `FilterApplier::apply`, que escolhe o conjunto pelo formato do buffer.
//
// Os de 16 bits fazem a mesma conta dos de 8 (mesmas fórmulas, mesmos parâmetros em unidades de 8 bits, mesma regra de
// pular o pixel de alfa 0 e de deixar o alfa como está), com duas diferenças que vêm do buffer ter 16 bits e não
// haver o que economizar: arredondam em vez de truncar e misturam com a opacidade da camada em 16 bits (os de 8 bits
// usam peso de 8 bits). `tests/native/filter16_checks.cpp` mede a distância de cada um ao de 8 bits.

#include "FilterKernels.hpp"
#include "../../../utils/ColorRGBA16.hpp"

#include <cstddef>
#include <cstdint>

namespace aladyn::engine::document::filters {

void applyBrightnessContrast16(const FilterSettings& filter, const FilterRegion& region);
void applyColorBalance16(const FilterSettings& filter, const FilterRegion& region);
void applyInvertThreshold16(const FilterSettings& filter, const FilterRegion& region);
void applyHueSat16(const FilterSettings& filter, const FilterRegion& region);

void applyPixelate16(const FilterSettings& filter, const FilterRegion& region);
void applyGaussianBlur16(const FilterSettings& filter, const FilterRegion& region);
void applySharpenVignette16(const FilterSettings& filter, const FilterRegion& region);

// O peso da opacidade da camada de filtro em 16 bits fixos (0..65536) e a mistura de um canal com ele.
[[nodiscard]] inline uint32_t opacityWeight16(double opacity) noexcept {
    return static_cast<uint32_t>(opacity * 65536.0 + 0.5);
}

[[nodiscard]] inline uint16_t mixChannel16(uint16_t original, uint16_t filtered, uint32_t weight) noexcept {
    const uint64_t mixed = static_cast<uint64_t>(original) * (65536u - weight) + static_cast<uint64_t>(filtered) * weight + 32768u;
    return static_cast<uint16_t>(mixed >> 16);
}

[[nodiscard]] inline uint16_t roundChannel16(float value) noexcept {
    return static_cast<uint16_t>(value < 0.0f ? 0.0f : (value > 65535.0f ? 65535.0f : value + 0.5f));
}

// Aplica `transform` (pixel -> pixel; só r, g e b importam) a cada pixel de alfa != 0 da região e mistura o resultado
// com o original pela opacidade da camada. Os filtros ponto a ponto são só a função `transform`.
template <typename Transform>
void transformPixels16(const FilterRegion& region, Transform&& transform) {
    utils::ColorRGBA16* base = reinterpret_cast<utils::ColorRGBA16*>(region.ptr);
    const bool full = region.isFullOpacity;
    const uint32_t weight = opacityWeight16(region.opacity);
    #pragma omp parallel for schedule(static) if((region.endY - region.startY) > 32)
    for (int y = region.startY; y <= region.endY; ++y) {
        utils::ColorRGBA16* row = base + static_cast<size_t>(y) * region.w;
        for (int x = region.startX; x <= region.endX; ++x) {
            const utils::ColorRGBA16 p = row[x];
            if (p.a == 0) continue;
            const utils::ColorRGBA16 q = transform(p);
            row[x] = full ? utils::ColorRGBA16{q.r, q.g, q.b, p.a}
                          : utils::ColorRGBA16{mixChannel16(p.r, q.r, weight), mixChannel16(p.g, q.g, weight), mixChannel16(p.b, q.b, weight), p.a};
        }
    }
}

} // namespace aladyn::engine::document::filters

#endif // ALADYN_ENGINE_FILTER_KERNELS_16_HPP
