#ifndef ALADYN_ENGINE_LINEAR_COLOR_SPACE_16_HPP
#define ALADYN_ENGINE_LINEAR_COLOR_SPACE_16_HPP

#include "../../utils/ColorRGBA16.hpp"
#include <algorithm>
#include <cstdint>

namespace aladyn::engine::color {

// ─── sRGB ↔ LINEAR PARA CANAIS DE 16 BITS ────────────────────────────────────
//
// A mesclagem em gama linear de um documento de 16 bits leva cada canal codificado (0..65535) ao espaço linear,
// mistura e volta. As duas contas têm uma DEFINIÇÃO em double (`srgbToLinearReference`, `linearToSrgb16Reference`,
// a mesma curva de `LinearColorSpace.hpp`) e uma tabela que a reproduz sem `pow` por pixel:
//
//   toLinear  o `srgbToLinearReference` dos 65536 valores, em float;
//   encode    o sRGB codificado de 16385 pontos de [0, 1] (passo de 1/16384), já em unidades de 16 bits, em float;
//             entre dois pontos a tabela interpola em linha reta. A curva é uma reta até 0,0031308 (exata) e depois
//             tem a curvatura de x^(1/2,4). O erro de interpolar é de 0,22 passo de 16 bits no pior ponto, o balde da
//             junção (onde a inclinação passa de 12,92 a cerca de 12,7 e a corda corta a quina), 0,05 entre 0,004 e
//             0,01, 0,012 entre 0,01 e 0,05 e 0,003 acima de 0,05. Medido por tests/native/blend16_checks.cpp.
//
// Os dois lados erram menos de um passo de 16 bits contra a definição: o resultado arredondado difere dela em no
// máximo 1 nível, e só onde a definição cai a menos de 0,25 de um meio.
struct Srgb16Tables {
    static constexpr int kEncodeBuckets = 16384;

    float toLinear[65536];
    float encode[kEncodeBuckets + 2];  // o último repete o penúltimo: a interpolação em 1.0 lê dois pontos

    Srgb16Tables() noexcept;
};

// Montadas uma vez, na primeira mesclagem de 16 bits (65536 + 16385 `pow`).
[[nodiscard]] const Srgb16Tables& srgb16Tables() noexcept;

// Definições em double, para as tabelas e para os testes. `encoded` e `linear` em [0, 1].
[[nodiscard]] double srgbToLinearReference(double encoded) noexcept;
[[nodiscard]] double linearToSrgbReference(double linear) noexcept;
// O canal de 16 bits mais próximo da codificação de `linear` (saturado em [0, 1]).
[[nodiscard]] uint16_t linearToSrgb16Reference(double linear) noexcept;

[[nodiscard]] inline uint16_t linearToSrgb16(const Srgb16Tables& tables, float linear) noexcept {
    // Mesma saturação da definição; um NaN cai em 0.
    const float clamped = linear > 1.0f ? 1.0f : (linear >= 0.0f ? linear : 0.0f);
    const float position = clamped * static_cast<float>(Srgb16Tables::kEncodeBuckets);
    const int bucket = static_cast<int>(position);
    const float fraction = position - static_cast<float>(bucket);
    const float low = tables.encode[bucket];
    return static_cast<uint16_t>(low + (tables.encode[bucket + 1] - low) * fraction + 0.5f);
}

inline utils::ColorRGBA16 blendLinearNormal16(
    utils::ColorRGBA16 src,
    float srcA,
    utils::ColorRGBA16 dst
) noexcept {
    if (srcA <= 0.0f) return dst;
    if (dst.a == 0) {
        return utils::ColorRGBA16{
            src.r, src.g, src.b,
            static_cast<uint16_t>(std::clamp(srcA * 65535.0f + 0.5f, 0.0f, 65535.0f))
        };
    }

    const float dstA = static_cast<float>(dst.a) / 65535.0f;
    const float outA = srcA + dstA * (1.0f - srcA);
    if (outA <= 0.0f) return utils::ColorRGBA16{0, 0, 0, 0};

    const auto& tables = srgb16Tables();
    const float sR = tables.toLinear[src.r];
    const float sG = tables.toLinear[src.g];
    const float sB = tables.toLinear[src.b];

    const float dR = tables.toLinear[dst.r];
    const float dG = tables.toLinear[dst.g];
    const float dB = tables.toLinear[dst.b];

    const float invOutA = 1.0f / outA;
    const float factorSrc = srcA * invOutA;
    const float factorDst = dstA * (1.0f - srcA) * invOutA;

    const float outLinR = sR * factorSrc + dR * factorDst;
    const float outLinG = sG * factorSrc + dG * factorDst;
    const float outLinB = sB * factorSrc + dB * factorDst;

    return utils::ColorRGBA16{
        linearToSrgb16(tables, outLinR),
        linearToSrgb16(tables, outLinG),
        linearToSrgb16(tables, outLinB),
        static_cast<uint16_t>(std::clamp(outA * 65535.0f + 0.5f, 0.0f, 65535.0f))
    };
}

inline utils::ColorRGBA16 blendLinearNormalOpaque16(
    utils::ColorRGBA16 src,
    float srcA,
    utils::ColorRGBA16 dst
) noexcept {
    if (srcA <= 0.0f) return dst;
    if (srcA >= 1.0f) return utils::ColorRGBA16{src.r, src.g, src.b, 65535};

    const auto& tables = srgb16Tables();
    const float sR = tables.toLinear[src.r];
    const float sG = tables.toLinear[src.g];
    const float sB = tables.toLinear[src.b];

    const float dR = tables.toLinear[dst.r];
    const float dG = tables.toLinear[dst.g];
    const float dB = tables.toLinear[dst.b];

    const float invSrcA = 1.0f - srcA;
    const float outLinR = sR * srcA + dR * invSrcA;
    const float outLinG = sG * srcA + dG * invSrcA;
    const float outLinB = sB * srcA + dB * invSrcA;

    return utils::ColorRGBA16{
        linearToSrgb16(tables, outLinR),
        linearToSrgb16(tables, outLinG),
        linearToSrgb16(tables, outLinB),
        65535
    };
}

} // namespace aladyn::engine::color

#endif // ALADYN_ENGINE_LINEAR_COLOR_SPACE_16_HPP
