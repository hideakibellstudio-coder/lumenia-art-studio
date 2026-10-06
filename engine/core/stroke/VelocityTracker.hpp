#ifndef ALADYN_ENGINE_VELOCITY_TRACKER_HPP
#define ALADYN_ENGINE_VELOCITY_TRACKER_HPP

#include "../../utils/Point2D.hpp"

namespace aladyn::engine::stroke {

// Velocidade do ponteiro em px/s, medida sobre o caminho percorrido numa janela de tempo e
// suavizada por uma constante de TEMPO (não por evento): a leitura não depende de a mesa
// entregar 1 evento por milissegundo ou uma rajada de 6 por quadro de 16,7 ms.
class VelocityTracker {
public:
    // Constante de tempo da suavização exponencial, em segundos.
    static constexpr double kDefaultSmoothingSeconds = 0.020;
    // Janela mínima de medição: abaixo dela os eventos só acumulam caminho (rajadas da fila do
    // sistema, vários eventos no mesmo milissegundo) e a velocidade não é recalculada.
    static constexpr double kMinWindowSeconds = 0.0008;
    // Teto de velocidade física humana, para um salto isolado não contaminar a leitura.
    static constexpr double kMaxVelocity = 3500.0;

    explicit VelocityTracker(double smoothingSeconds = kDefaultSmoothingSeconds) noexcept;

    void reset(utils::Point2D initialPosition, double timestamp) noexcept;
    double update(utils::Point2D currentPosition, double timestamp) noexcept;

    [[nodiscard]] double getSmoothedVelocity() const noexcept { return m_smoothedVelocity; }
    [[nodiscard]] double getNormalizedVelocity(double maxVelocity = 1500.0) const noexcept;

private:
    double m_smoothingSeconds{kDefaultSmoothingSeconds};
    utils::Point2D m_lastPosition{0.0, 0.0};
    double m_windowStart{0.0};     // instante da última leitura de velocidade
    double m_windowDistance{0.0};  // caminho percorrido desde m_windowStart
    double m_smoothedVelocity{0.0};
    bool m_hasReading{false};
};

} // namespace aladyn::engine::stroke

#endif // ALADYN_ENGINE_VELOCITY_TRACKER_HPP
