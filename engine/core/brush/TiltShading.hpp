#ifndef ALADYN_ENGINE_TILT_SHADING_HPP
#define ALADYN_ENGINE_TILT_SHADING_HPP

#include <algorithm>
#include <cmath>

namespace aladyn::engine::brush {

// ─── A INCLINAÇÃO DA CANETA ─────────────────────────────────────────────────
//
// O quanto a caneta está deitada, de 0 (em pé, ou mouse) a 1 (deitada), com transição suave. É a medida que o lado
// do grafite do Lápis e os controles "inclinação → tamanho" e "inclinação → fluxo" do mapeador usam; mouse e caneta
// em pé (altitude de 70° para cima) dão 0 e não mudam nada.
namespace pen_tilt {

constexpr double kStandingAltitude = 70.0;  // acima disto a ponta risca fino
constexpr double kLyingAltitude = 25.0;     // abaixo disto o lado inteiro da ponta toca o papel

[[nodiscard]] inline double lean(double altitude) noexcept {
    const double t = std::clamp((kStandingAltitude - altitude) / (kStandingAltitude - kLyingAltitude), 0.0, 1.0);
    return t * t * (3.0 - 2.0 * t);
}

} // namespace pen_tilt

// ─── O LADO DO GRAFITE ──────────────────────────────────────────────────────
//
// Um lápis em pé risca fino com a ponta; deitado, risca largo com o lado do grafite: a marca se alonga no sentido
// em que a caneta pende (o azimute) e a mesma carga se espalha numa área maior, então fica mais clara. O
// interruptor "sombreamento por inclinação" do Lápis (`pencilParams.tiltShadingEnabled`) liga isso; até
// 2026-10-02 estava na interface e em cinco presets sem que nenhuma linha do motor o lesse.
//
// A largura da marca é a do grafite (o raio escolhido); só o eixo ao longo do azimute cresce.
namespace graphite_side {

constexpr double kMaxStretch = 3.0;         // quantas vezes a marca se alonga com a caneta deitada
constexpr double kMaxFlowLoss = 0.4;        // quanto do fluxo se perde, com a caneta deitada, ao espalhar

// Gira `angle` para alinhar o eixo maior da elipse ao azimute, pelo menor caminho (a elipse tem simetria de 180°),
// na proporção de `amount`.
[[nodiscard]] inline double turnToward(double angle, double azimuth, double amount) noexcept {
    const double shortest = std::fmod(azimuth - angle + 270.0, 180.0) - 90.0;
    double turned = std::fmod(angle + shortest * amount, 360.0);
    if (turned < 0.0) turned += 360.0;
    return turned;
}

// Aplica o lado do grafite ao carimbo já mapeado. `radius` é o eixo maior; `aspect`, menor / maior.
inline void apply(double altitude, double azimuth, double& radius, double& flow, double& angle, double& aspect) noexcept {
    const double amount = pen_tilt::lean(altitude);
    if (amount <= 0.0) return;
    const double stretch = 1.0 + (kMaxStretch - 1.0) * amount;
    radius *= stretch;
    aspect = std::clamp(aspect / stretch, 0.05, 1.0);
    angle = turnToward(angle, azimuth, amount);
    flow *= 1.0 - kMaxFlowLoss * amount;
}

} // namespace graphite_side

} // namespace aladyn::engine::brush

#endif // ALADYN_ENGINE_TILT_SHADING_HPP
