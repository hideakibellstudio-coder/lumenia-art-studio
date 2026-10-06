#ifndef ALADYN_ENGINE_PRESSURE_CALIBRATION_HPP
#define ALADYN_ENGINE_PRESSURE_CALIBRATION_HPP

#include <algorithm>
#include <cmath>

namespace aladyn::engine::stroke {

// Curva global de entrada da pressão: o que a MESA entrega vira o que o motor lê, antes do
// estabilizador e de qualquer curva de pincel. Existe porque cada caneta/driver cobre uma faixa
// diferente: a mesa gravada em 2026-10-02 (Windows Ink) mal passa de 0,35 no desenho livre, e com
// as curvas de pincel pensadas para 0..1 o Lápis HB deixava 74% do trajeto sem tinta.
//
//   lido = ((bruto - floor) / (ceiling - floor)) ^ gamma, preso em 0..1
//
// floor    pressão bruta abaixo da qual a caneta lê 0 (zona morta do driver).
// ceiling  pressão bruta que conta como pressão total (a que o dono aperta de verdade).
// gamma    < 1 levanta as pressões leves, > 1 as achata; 1 é linear.
// O padrão (0, 1, 1) é a identidade: nada muda enquanto o artista não calibra.
struct PressureCalibration {
    double floor{0.0};
    double ceiling{1.0};
    double gamma{1.0};

    [[nodiscard]] bool isIdentity() const noexcept { return floor == 0.0 && ceiling == 1.0 && gamma == 1.0; }

    // Valores fora de faixa são corrigidos aqui, no uso, para que um slider ou um arquivo de
    // configuração malformado nunca produza NaN: ceiling > floor + 0,01 e gamma em 0,1..5.
    [[nodiscard]] double apply(double raw) const noexcept {
        if (isIdentity()) return raw;
        const double lo = std::clamp(floor, 0.0, 0.98);
        const double hi = std::clamp(ceiling, lo + 0.01, 1.0);
        const double unit = std::clamp((raw - lo) / (hi - lo), 0.0, 1.0);
        const double g = std::clamp(gamma, 0.1, 5.0);
        return g == 1.0 ? unit : std::pow(unit, g);
    }
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_PRESSURE_CALIBRATION_HPP
