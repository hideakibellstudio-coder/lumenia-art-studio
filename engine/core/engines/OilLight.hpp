#ifndef ALADYN_ENGINE_OIL_LIGHT_HPP
#define ALADYN_ENGINE_OIL_LIGHT_HPP

#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

// ─── A LUZ DO RELEVO DO ÓLEO ────────────────────────────────────────────────
//
// O relevo de uma pincelada (as cristas entre as cerdas e a pilha de tinta nas bordas) é mostrado por uma luz
// fixa no canto superior esquerdo. A conta é feita a partir do DECLIVE da superfície no pixel, e não somada em
// cada carimbo como o brilho especular era: o resultado de um pixel é o mesmo com 4 ou com 40 carimbos por cima.
//
// `lambda` é a luz de um pixel, de -1 (sombra total) a +1 (branco). Ela é aplicada de um jeito que se desfaz
// exatamente: a luz positiva leva o canal para o branco (c + λ(1 - c)), a negativa para o preto (c(1 + λ)).
// Por isso o motor tira a luz que o pixel já tinha antes de compor a tinta nova e põe a luz nova depois, sem
// que o brilho se acumule nem estoure o canal.
namespace oil_light {

// Direção da luz (para onde ela está, em relação à superfície) e o vetor intermediário entre ela e o olho.
constexpr float kLightX = -0.45223f, kLightY = -0.45223f, kLightZ = 0.76878f;
constexpr float kHalfX = -0.24045f, kHalfY = -0.24045f, kHalfZ = 0.94037f;
constexpr float kDiffuseGain = 0.4f;
constexpr float kSpecularGain = 1.1f;
constexpr float kMaxShadow = -0.5f;
constexpr float kMaxLight = 0.85f;

[[nodiscard]] inline float lit(float channel, float lambda) noexcept {
    return lambda >= 0.0f ? channel + lambda * (1.0f - channel) : channel * (1.0f + lambda);
}

[[nodiscard]] inline float unlit(float channel, float lambda) noexcept {
    return lambda >= 0.0f ? (channel - lambda) / (1.0f - lambda) : channel / (1.0f + lambda);
}

// x^16 só com multiplicações: o mesmo resultado em qualquer compilador (pow() difere no último bit).
[[nodiscard]] inline float pow16(float value) noexcept {
    value *= value;
    value *= value;
    value *= value;
    return value * value;
}

// A luz de um pixel cuja superfície sobe `slopeX` por px em x e `slopeY` em y (unidades de altura de cerda).
// `impasto` escala o sombreado (volume), `specular` o brilho úmido. Superfície plana: 0.
[[nodiscard]] inline float shade(float slopeX, float slopeY, float impasto, float specular) noexcept {
    const float inverse = 1.0f / std::sqrt(1.0f + slopeX * slopeX + slopeY * slopeY);
    const float nx = -slopeX * inverse, ny = -slopeY * inverse, nz = inverse;
    const float diffuse = nx * kLightX + ny * kLightY + nz * kLightZ - kLightZ;
    const float facing = std::max(0.0f, nx * kHalfX + ny * kHalfY + nz * kHalfZ);
    const float gloss = std::max(0.0f, pow16(facing) - pow16(kHalfZ));
    return std::clamp(kDiffuseGain * impasto * diffuse + kSpecularGain * specular * gloss, kMaxShadow, kMaxLight);
}

} // namespace oil_light

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_OIL_LIGHT_HPP
