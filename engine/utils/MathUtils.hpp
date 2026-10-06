#ifndef ALADYN_ENGINE_MATH_UTILS_HPP
#define ALADYN_ENGINE_MATH_UTILS_HPP

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace aladyn::engine::utils {

class MathUtils {
public:
    static inline double clamp(double val, double minVal, double maxVal) noexcept {
        return std::clamp(val, minVal, maxVal);
    }

    static inline double lerp(double a, double b, double t) noexcept {
        return a + (b - a) * t;
    }

    static inline double smoothstep(double edge0, double edge1, double x) noexcept {
        if (edge0 >= edge1) {
            return x >= edge0 ? 1.0 : 0.0;
        }
        const double t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0);
        return t * t * (3.0 - 2.0 * t);
    }

    // Valor em 0..255 para o byte MAIS PRÓXIMO (fora da faixa e NaN são presos). Até 2026-10-02 os
    // motores de traço convertiam com `static_cast<uint8_t>(...)`, que trunca: cada depósito perdia
    // em média meio nível, o Lápis e o Nanquim não passavam de alfa 254 e a cor derivava 1 nível
    // para baixo a cada camada de tinta. Converter para byte no caminho de traço passa por aqui.
    static inline std::uint8_t roundToByte(double value) noexcept {
        if (!(value > 0.0)) return 0;
        if (value >= 255.0) return 255;
        return static_cast<std::uint8_t>(std::lround(value));
    }

    // O mesmo para um valor em 0..1.
    static inline std::uint8_t unitToByte(double unit) noexcept {
        return roundToByte(unit * 255.0);
    }
};

} // namespace aladyn::engine::utils

#endif // ALADYN_ENGINE_MATH_UTILS_HPP
