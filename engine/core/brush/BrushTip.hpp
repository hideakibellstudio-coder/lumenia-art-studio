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

    // ─── DINÂMICAS CROMÁTICAS (COLOR JITTER) ─────────────────────────────────
    double jitterHue{0.0};        // Variação estocástica de matiz (0.0 a 1.0, onde 1.0 = ±180°)
    double jitterSaturation{0.0}; // Variação estocástica de saturação (0.0 a 1.0)
    double jitterBrightness{0.0}; // Variação estocástica de brilho/valor (0.0 a 1.0)

    // ─── DINÂMICAS DE CANETA AVANÇADAS ───────────────────────────────────────
    bool   useTwistForAngle{false}; // Ângulo sincronizado com Barrel Roll / Twist da caneta
    double tiltToAngle{0.0};        // Modulação de rotação por azimute de inclinação (0.0 a 1.0)
    double tiltToAspect{0.0};       // Achatamento da ponta conforme caneta se deita (0.0 a 1.0)
    double tiltToSize{0.0};         // Crescimento do tamanho conforme a caneta se deita: 1.0 dobra o diâmetro (0.0 a 1.0)
    double tiltToFlow{0.0};         // Perda de fluxo conforme a caneta se deita: 1.0 apaga com a caneta deitada (0.0 a 1.0)
};

} // namespace aladyn::engine::brush

#endif // ALADYN_ENGINE_BRUSH_TIP_HPP
