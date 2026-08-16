#ifndef ALADYN_ENGINE_BRUSH_TIP_HPP
#define ALADYN_ENGINE_BRUSH_TIP_HPP

namespace aladyn::engine::brush {

struct BrushTip {
    double angle{0.0};           // Rotação base em graus (0 a 360)
    double aspectRatio{1.0};     // Achatamento elíptico (1.0 = circular, 0.2 = elipse/chato)
    bool followStroke{false};    // Auto-rotação acompanhando a direção do vetor velocidade

    double jitterSize{0.0};      // % de variação aleatória de tamanho por dab (0.0 a 1.0)
    double jitterAngle{0.0};     // % de variação aleatória de ângulo por dab (0.0 a 1.0)
    double jitterPosition{0.0};  // Dispersão/espalhamento da posição por dab (0.0 a 1.0)
};

} // namespace aladyn::engine::brush

#endif // ALADYN_ENGINE_BRUSH_TIP_HPP
