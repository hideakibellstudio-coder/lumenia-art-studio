#ifndef ALADYN_ENGINE_LARGE_BRUSH_OPTIMIZER_HPP
#define ALADYN_ENGINE_LARGE_BRUSH_OPTIMIZER_HPP

#include <cstddef>
#include <algorithm>
#include <cmath>

namespace aladyn::engine::raster {

/**
 * @brief Componente isolado e dedicado de governança de throughput e fluidez para pincéis médios e gigantes (R > 32px até 2000px).
 *
 * Garante que a fluidez de 120 FPS em pincéis gigantes (≥ 500px de diâmetro) fique
 * 100% blindada e isolada de quaisquer ajustes ou manutenções nos parâmetros de traço fino.
 */
class LargeBrushOptimizer {
public:
    /// Raio mínimo (em pixels do canvas) para ativação das políticas de pincel grande (diâmetro 64px)
    static constexpr double LARGE_BRUSH_RADIUS_THRESHOLD = 32.0;

    /// Verifica se um dado raio entra na categoria de pincel grande / gigante
    [[nodiscard]] static constexpr bool isLargeBrush(double radius) noexcept {
        return radius > LARGE_BRUSH_RADIUS_THRESHOLD;
    }

    /**
     * @brief Calcula o passo analítico adaptativo entre carimbos.
     *
     * - Para traços finos (R <= 32px): mantém espaçamento puramente uniforme e nominal.
     * - Para traços gigantes (R > 32px): o espaçamento sobe suavemente (Hermite) até
     *   18% do diâmetro em R = 250px, com teto de 35% do diâmetro (sobreposição >= 65%).
     *   Só o raio decide o passo: até 2026-09-25 a assinatura recebia a distância do
     *   segmento e este texto prometia "modulação por velocidade", que nunca existiu.
     */
    [[nodiscard]] static double computeAdaptiveStep(
        double radius,
        double spacingFactor
    ) noexcept;

    /**
     * @brief Retorna o teto seguro de carimbos por micro-segmento baseado no raio.
     *
     * Previne explosão quadrática de pixels em eventos com latência pontual.
     */
    [[nodiscard]] static size_t getMaxDabsPerSegment(double radius) noexcept;

    /**
     * @brief Curva Hermite cúbica suave C^1 para atenuação radial contínua.
     * S(t) = t^2 * (3 - 2t), com derivada zero em t=0 e t=1.
     */
    [[nodiscard]] static constexpr double smoothHermite(double t) noexcept {
        const double tc = (t < 0.0) ? 0.0 : ((t > 1.0) ? 1.0 : t);
        return tc * tc * (3.0 - 2.0 * tc);
    }
};

} // namespace aladyn::engine::raster

#endif // ALADYN_ENGINE_LARGE_BRUSH_OPTIMIZER_HPP
