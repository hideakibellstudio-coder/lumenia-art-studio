#include "SnapLockStateMachine.hpp"
#include "MathUtils.hpp"
#include <cmath>

namespace aladyn::engine::math {

double SnapLockStateMachine::scoreCandidate(
    const SnapCandidate& candidate,
    const Point2D& rawPoint,
    const TrajectoryEstimate& trajectory,
    const SnapLockConfig& config,
    Point2D& outClosest
) noexcept {
    outClosest = SnapCandidateMath::closestPoint(candidate, rawPoint);
    const double dist = rawPoint.distanceTo(outClosest);

    const double t = MathUtils::clamp(1.0 - dist / std::max(1e-6, config.attractionRadius), 0.0, 1.0);
    const double proximity = t * t * (3.0 - 2.0 * t); // smoothstep(0,1,t) -- candidata fora do raio pontua 0
    if (proximity <= 0.0) {
        return 0.0;
    }

    const Point2D tangent = SnapCandidateMath::tangentAt(candidate, rawPoint);
    const double alignment = std::abs(trajectory.direction.x * tangent.x + trajectory.direction.y * tangent.y);
    const double sharpened = std::pow(alignment, config.scoreSharpness);

    // Sem confianca de trajetoria (poucos pontos, ou segmentos que se
    // cancelam), ignora a direcao por completo (directionFactor=1: so
    // proximidade decide, igual ao "Buscando" quando ainda nao ha gesto
    // confiavel). Com confianca plena, pesa o alinhamento inteiro. Rampa
    // continua em vez de um corte binario -- nao reintroduz o mesmo tipo de
    // limiar rigido que causou o bug original.
    const double directionFactor = MathUtils::lerp(1.0, sharpened, trajectory.confidence);
    return proximity * directionFactor;
}

SnapLockResult SnapLockStateMachine::step(
    const Point2D& rawPoint,
    const TrajectoryEstimate& trajectory,
    const std::vector<SnapCandidate>& candidates,
    SnapLockState prevState,
    int prevCandidateIndex,
    int prevStreak,
    const SnapLockConfig& config
) noexcept {
    SnapLockResult result;

    // 1) Committed: só reavalia permanência (stray vs breakawayRadius); não
    //    repontua candidatas concorrentes enquanto a trava aguenta -- evita
    //    flicagem por ruído de um único frame enquanto o gesto claramente
    //    continua sobre a candidata travada.
    if (prevState == SnapLockState::Committed
        && prevCandidateIndex >= 0
        && prevCandidateIndex < static_cast<int>(candidates.size())) {
        const Point2D closest = SnapCandidateMath::closestPoint(candidates[static_cast<size_t>(prevCandidateIndex)], rawPoint);
        const double stray = rawPoint.distanceTo(closest);
        if (config.breakawayRadius <= 0.0 || stray <= config.breakawayRadius) {
            result.point = closest;
            result.state = SnapLockState::Committed;
            result.candidateIndex = prevCandidateIndex;
            result.streak = prevStreak;
            return result;
        }
        // stray > breakawayRadius: solta e cai para a repontuação abaixo,
        // recomeçando do zero (não herda o streak da trava antiga).
    }

    // 2) Buscando/Tentativa: pontua todas as candidatas neste frame.
    if (candidates.empty()) {
        result.point = rawPoint;
        return result; // Searching, candidateIndex=-1, streak=0 (defaults)
    }

    int bestIndex = -1;
    double bestScore = 0.0;
    Point2D bestClosest = rawPoint;
    for (int i = 0; i < static_cast<int>(candidates.size()); ++i) {
        Point2D closest;
        const double score = scoreCandidate(candidates[static_cast<size_t>(i)], rawPoint, trajectory, config, closest);
        if (score > bestScore) {
            bestScore = score;
            bestIndex = i;
            bestClosest = closest;
        }
    }

    if (bestIndex < 0) {
        // Nenhuma candidata dentro do raio de atracao.
        result.point = rawPoint;
        return result; // Searching, candidateIndex=-1, streak=0
    }

    const bool continuesTentative = (prevState != SnapLockState::Searching) && (prevCandidateIndex == bestIndex);
    const int newStreak = continuesTentative ? (prevStreak + 1) : 1;

    result.point = bestClosest;
    result.candidateIndex = bestIndex;
    result.streak = newStreak;
    result.state = (newStreak >= config.commitFrames) ? SnapLockState::Committed : SnapLockState::Tentative;
    return result;
}

} // namespace aladyn::engine::math
