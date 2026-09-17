#ifndef ALADYN_ENGINE_TRAJECTORY_ESTIMATOR_HPP
#define ALADYN_ENGINE_TRAJECTORY_ESTIMATOR_HPP

#include "Point2D.hpp"
#include <vector>

namespace aladyn::engine::math {

struct TrajectoryEstimate {
    Point2D direction{1.0, 0.0}; // unitário (mesmo quando confidence == 0)
    double confidence{0.0};      // 0..1
};

// Fase D0 (redesign do motor de snap, ver
// claude/proposta-redesign-motor-snap-guias.md no projeto) — substitui o
// `chord = (rawPoint - referencia) / dist` usado por toda a família antiga
// de snap*() (e pelas duas rodadas de fix do C3.5, que só trocaram QUAL
// ponto usar como referência — o ponto de pressão, depois o último ponto
// travado) por uma estimativa robusta a amostragem esparsa/ruidosa (mouse
// gera eventos grandes e espaçados; stylus gera eventos pequenos e densos
// para o mesmo gesto percebido).
//
// A diferença não é qual ponto vira a referência — é NÃO reduzir a direção
// a um único vetor entre dois pontos. Cada segmento consecutivo da janela
// recente é normalizado individualmente antes de entrar na média (ponderada
// por recência): um salto grande contribui com a mesma força de DIREÇÃO que
// qualquer outro segmento, não domina a média só por ser fisicamente maior
// — que é exatamente o que fazia o "chord" antigo (e continuaria fazendo
// não importa qual ponto fosse escolhido como referência única).
//
// Sem estado: o chamador possui a janela (ring buffer simples, cap de N
// pontos — ver GeometryToolController) e a passa inteira a cada chamada,
// mesmo padrão já usado para `candidates` no Curvilinear.
class TrajectoryEstimator {
public:
    // recentPoints: pontos brutos do traço em ordem cronológica (mais antigo
    // primeiro), tipicamente uma janela pequena e limitada (5-8 pontos) — não
    // o traço inteiro. zoom afeta só o piso de deslocamento mínimo (mesmo
    // papel que já tinha em lock_thresh).
    static TrajectoryEstimate estimate(
        const std::vector<Point2D>& recentPoints,
        double zoom
    ) noexcept;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_TRAJECTORY_ESTIMATOR_HPP
