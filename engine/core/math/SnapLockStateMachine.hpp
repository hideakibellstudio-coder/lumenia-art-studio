#ifndef ALADYN_ENGINE_SNAP_LOCK_STATE_MACHINE_HPP
#define ALADYN_ENGINE_SNAP_LOCK_STATE_MACHINE_HPP

#include "Point2D.hpp"
#include "SnapCandidate.hpp"
#include "TrajectoryEstimator.hpp"
#include <vector>

namespace aladyn::engine::math {

enum class SnapLockState { Searching = 0, Tentative = 1, Committed = 2 };

struct SnapLockConfig {
    double attractionRadius{32.0};  // raio espacial de atracao (gate de proximidade) -- substitui o uso duplo de snapRadius
    double breakawayRadius{32.0};   // raio de afastamento para soltar um Committed -- parametro proprio, independente do de atracao
    int    commitFrames{3};         // frames consecutivos como melhor candidata antes de virar Committed
    double scoreSharpness{2.0};     // expoente k no alinhamento direcional (score = proximidade * alinhamento^k)
};

struct SnapLockResult {
    Point2D point{ 0.0, 0.0 };
    SnapLockState state{ SnapLockState::Searching };
    int candidateIndex{ -1 }; // -1 = nenhuma candidata tentativa/comprometida
    int streak{ 0 };
};

// Fase D0 (redesign do motor de snap, ver
// claude/proposta-redesign-motor-snap-guias.md no projeto) — substitui o
// lock binário de frame único (decidia tudo a partir de uma única amostra
// de direção, sem histerese, e só soltava quando o afastamento already
// comprovado ultrapassava um raio) por três estados com debounce — o padrão
// usual para um classificador sensível a ruído que hoje oscila entre
// decisões erradas mesmo depois de soltar uma trava obsoleta (C3.5 v1/v2):
//
//   Searching — sem compromisso; reporta a melhor candidata do frame atual,
//               mas nada persiste entre frames.
//   Tentative — uma candidata vem pontuando melhor há `streak` frames
//               seguidos; troca de candidata tentativa (streak volta a 1)
//               se outra assumir a liderança antes de completar
//               `commitFrames`.
//   Committed — projeta sempre na candidata travada; só solta quando o
//               afastamento (stray) ultrapassa `breakawayRadius`, e ao
//               soltar reavalia do zero (não herda streak da trava antiga).
//
// Sem estado próprio: quem chama (GeometryToolController) possui
// state/candidateIndex/streak e os repassa a cada chamada — mesmo contrato
// já usado em CurvilinearSnapEngine::snap()/GuideSnapEngine::snapPerspective().
class SnapLockStateMachine {
public:
    static SnapLockResult step(
        const Point2D& rawPoint,
        const TrajectoryEstimate& trajectory,
        const std::vector<SnapCandidate>& candidates,
        SnapLockState prevState,
        int prevCandidateIndex,
        int prevStreak,
        const SnapLockConfig& config
    ) noexcept;

private:
    // Retorna a pontuação da candidata (0 = fora do raio de atração) e
    // escreve em outClosest o ponto projetado, para reaproveitar sem
    // recalcular no chamador.
    static double scoreCandidate(
        const SnapCandidate& candidate,
        const Point2D& rawPoint,
        const TrajectoryEstimate& trajectory,
        const SnapLockConfig& config,
        Point2D& outClosest
    ) noexcept;
};

} // namespace aladyn::engine::math

#endif // ALADYN_ENGINE_SNAP_LOCK_STATE_MACHINE_HPP
