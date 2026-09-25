#ifndef ALADYN_ENGINE_BRUSH_PREVIEWS_HPP
#define ALADYN_ENGINE_BRUSH_PREVIEWS_HPP

// Prévias do painel de pincel, fora de qualquer documento. Contrato público;
// a implementação mora em orchestrator/StrokePreviewRenderer.

#include "../../core/brush/BrushProfile.hpp"
#include <cstdint>
#include <vector>

namespace aladyn::engine::boundary {

/// Lado da máscara devolvida por renderRoundTipMask.
inline constexpr int kRoundTipPreviewSize = 64;

/// Pincelada senoidal com o motor real do perfil; RGBA8, width*height*4.
[[nodiscard]] std::vector<uint8_t> renderStrokePreview(const brush::BrushProfile& profile, int width, int height);

/// Ponta redonda com a dureza dada (perfil sem textura de forma); A8, lado kRoundTipPreviewSize.
[[nodiscard]] std::vector<uint8_t> renderRoundTipMask(double hardness);

} // namespace aladyn::engine::boundary

#endif // ALADYN_ENGINE_BRUSH_PREVIEWS_HPP
