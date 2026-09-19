#include "SnapOrchestrator.hpp"

#include <stdexcept>

namespace aladyn::engine::boundary::internal {

void SnapOrchestrator::setGuideConfig(
    math::GuideConfig& cfg,
    int type, double p0x, double p0y, double p1x, double p1y, double p2x, double p2y, double p3x, double p3y,
    double vpAx, double vpAy, double vpBx, double vpBy, double vpCx, double vpCy, double cx, double cy,
    double fov, double pitch, double yaw, double snapRadius
) {
    cfg = { static_cast<math::GuideType>(type), {p0x, p0y}, {p1x, p1y}, {p2x, p2y}, {p3x, p3y}, {vpAx, vpAy}, {vpBx, vpBy}, {vpCx, vpCy}, cx, cy, fov, pitch, yaw, snapRadius };
}

std::vector<double> SnapOrchestrator::snapPoint(const math::GuideConfig& cfg, double rawX, double rawY, double lastX, double lastY, bool hasLast) {
    const math::Point2D last{ lastX, lastY };
    const math::Point2D snapped = math::GuideSnapEngine::snapPoint(cfg, {rawX, rawY}, hasLast ? &last : nullptr);
    return { snapped.x, snapped.y };
}

namespace {
    // Codifica/decodifica uma CurvilinearCurve em 11 doubles para cruzar a
    // fronteira PyBind11 sem registrar um tipo novo — mesma convenção já usada
    // por outros métodos do facade que trocam buffers planos (ex.: getTransformSourceBufferSize).
    // Layout: [kind, family, p1x,p1y, p2x,p2y, dirx,diry, centerx,centery, radius]
    void encodeCurvilinearCurve(const math::CurvilinearCurve& c, std::vector<double>& out) {
        out.push_back(static_cast<double>(c.kind));
        out.push_back(static_cast<double>(c.family));
        out.push_back(c.p1.x); out.push_back(c.p1.y);
        out.push_back(c.p2.x); out.push_back(c.p2.y);
        out.push_back(c.dir.x); out.push_back(c.dir.y);
        out.push_back(c.center.x); out.push_back(c.center.y);
        out.push_back(c.radius);
    }

    math::CurvilinearCurve decodeCurvilinearCurve(const std::vector<double>& flat, size_t index) {
        math::CurvilinearCurve c;
        const size_t o = index * 11;
        c.kind = static_cast<math::CurveKind>(static_cast<int>(flat[o + 0]));
        c.family = static_cast<math::CurveFamily>(static_cast<int>(flat[o + 1]));
        c.p1 = math::Point2D{ flat[o + 2], flat[o + 3] };
        c.p2 = math::Point2D{ flat[o + 4], flat[o + 5] };
        c.dir = math::Point2D{ flat[o + 6], flat[o + 7] };
        c.center = math::Point2D{ flat[o + 8], flat[o + 9] };
        c.radius = flat[o + 10];
        return c;
    }
}

void SnapOrchestrator::setCurvilinearGuideConfig(
    math::GuideConfig& cfg,
    double baseRadius, double density,
    bool showV, bool showH, bool showD,
    bool showGround, bool showCeiling,
    bool showGroundVerticals, bool showCeilingVerticals,
    bool showStraightVerticals,
    int snapMode, double snapSensitivity
) {
    cfg.baseRadius = baseRadius;
    cfg.density = density;
    cfg.showV = showV;
    cfg.showH = showH;
    cfg.showD = showD;
    cfg.showGround = showGround;
    cfg.showCeiling = showCeiling;
    cfg.showGroundVerticals = showGroundVerticals;
    cfg.showCeilingVerticals = showCeilingVerticals;
    cfg.showStraightVerticals = showStraightVerticals;
    cfg.snapMode = snapMode;
    cfg.snapSensitivity = snapSensitivity;
}

std::vector<double> SnapOrchestrator::getCurvilinearCandidates(const math::GuideConfig& cfg, double clickX, double clickY) {
    const auto curves = math::CurvilinearSnapEngine::candidates(cfg, math::Point2D{ clickX, clickY });
    std::vector<double> out;
    out.reserve(curves.size() * 11);
    for (const auto& c : curves) encodeCurvilinearCurve(c, out);
    return out;
}

std::vector<double> SnapOrchestrator::getNearestPrimaryGridCurve(const math::GuideConfig& cfg, double x, double y, double maxDist) {
    math::CurvilinearCurve found;
    if (!math::CurvilinearSnapEngine::nearestPrimaryGridCurve(cfg, math::Point2D{ x, y }, maxDist, found)) {
        return {};
    }
    std::vector<double> flat;
    encodeCurvilinearCurve(found, flat);
    return flat;
}

std::vector<double> SnapOrchestrator::snapCurvilinear(
    const math::GuideConfig& cfg,
    double rawX, double rawY, double startX, double startY,
    const std::vector<double>& candidates, int lockedIndex, bool isStroking, double zoom
) {
    if (candidates.size() % 11 != 0) {
        throw std::invalid_argument("snapCurvilinear: candidates deve ter um multiplo de 11 doubles por curva");
    }
    const size_t n = candidates.size() / 11;
    std::vector<math::CurvilinearCurve> curves;
    curves.reserve(n);
    for (size_t i = 0; i < n; ++i) curves.push_back(decodeCurvilinearCurve(candidates, i));

    int outLocked = -1;
    const math::Point2D snapped = math::CurvilinearSnapEngine::snap(
        cfg, math::Point2D{ rawX, rawY }, math::Point2D{ startX, startY },
        curves, lockedIndex, isStroking, zoom, outLocked
    );
    return { snapped.x, snapped.y, static_cast<double>(outLocked) };
}

std::vector<double> SnapOrchestrator::snapPerspective(
    const math::GuideConfig& cfg,
    double rawX, double rawY, double startX, double startY,
    bool hasLockedDir, double lockedDirX, double lockedDirY, double zoom
) {
    const math::Point2D lockedDir{ lockedDirX, lockedDirY };
    math::Point2D outLockedDir{ 0.0, 0.0 };
    bool outHasLockedDir = false;
    const math::Point2D snapped = math::GuideSnapEngine::snapPerspective(
        cfg, math::Point2D{ rawX, rawY }, math::Point2D{ startX, startY },
        hasLockedDir ? &lockedDir : nullptr, zoom, outLockedDir, outHasLockedDir
    );
    return { snapped.x, snapped.y, outHasLockedDir ? 1.0 : 0.0, outLockedDir.x, outLockedDir.y };
}

namespace {
    // Decodifica uma SnapCandidate a partir de 9 doubles -- mesma convencao
    // de decodeCurvilinearCurve, so que mais enxuta porque SnapCandidate nao
    // precisa de p2 (reta = ponto + direcao, nunca dois pontos). Layout:
    // [kind, family, p1x,p1y, dirx,diry, centerx,centery, radius]
    // Sem encode correspondente aqui de proposito: nada nesta fase (D0)
    // ainda produz SnapCandidate a partir de nenhum tipo de guia real -- os
    // testes montam candidatas diretamente em Python. O encode volta em
    // D1-D3, quando os adaptadores de guia (Straight/CurveRuler/Curvilinear/
    // Perspectiva) passarem a gerar SnapCandidate de verdade.
    math::SnapCandidate decodeSnapCandidate(const std::vector<double>& flat, size_t index) {
        math::SnapCandidate c;
        const size_t o = index * 9;
        c.kind = static_cast<math::CandidateKind>(static_cast<int>(flat[o + 0]));
        c.family = static_cast<int>(flat[o + 1]);
        c.p1 = math::Point2D{ flat[o + 2], flat[o + 3] };
        c.dir = math::Point2D{ flat[o + 4], flat[o + 5] };
        c.center = math::Point2D{ flat[o + 6], flat[o + 7] };
        c.radius = flat[o + 8];
        return c;
    }
}

// -- Fase D0 (redesign do motor de snap) ------------------------------------
// Ver claude/proposta-redesign-motor-snap-guias.md no projeto para o
// diagnostico e desenho completos. Estaticos (sem `this`): os tres
// componentes (SnapCandidate/TrajectoryEstimator/SnapLockStateMachine) sao
// puros e sem estado -- nao dependem de cfg nem de nenhum outro
// estado do facade, diferente de snapCurvilinear/snapPerspective, que
// consultam cfg. Ainda nao ligados a nenhum tipo de guia real
// (isso e' D1-D3); aqui so o suficiente pra testar os componentes isolados
// via pytest contra o facade.

std::vector<double> SnapOrchestrator::estimateTrajectory(const std::vector<double>& recentPoints, double zoom) {
    if (recentPoints.size() % 2 != 0) {
        throw std::invalid_argument("estimateTrajectory: recentPoints deve ter um multiplo de 2 doubles por ponto");
    }
    std::vector<math::Point2D> points;
    points.reserve(recentPoints.size() / 2);
    for (size_t i = 0; i + 1 < recentPoints.size(); i += 2) {
        points.emplace_back(recentPoints[i], recentPoints[i + 1]);
    }
    const math::TrajectoryEstimate est = math::TrajectoryEstimator::estimate(points, zoom);
    return { est.direction.x, est.direction.y, est.confidence };
}

std::vector<double> SnapOrchestrator::stepSnapLock(
    double rawX, double rawY,
    double trajDirX, double trajDirY, double trajConfidence,
    const std::vector<double>& candidates,
    int prevState, int prevCandidateIndex, int prevStreak,
    double attractionRadius, double breakawayRadius, int commitFrames, double scoreSharpness
) {
    if (candidates.size() % 9 != 0) {
        throw std::invalid_argument("stepSnapLock: candidates deve ter um multiplo de 9 doubles por candidata");
    }
    const size_t n = candidates.size() / 9;
    std::vector<math::SnapCandidate> decoded;
    decoded.reserve(n);
    for (size_t i = 0; i < n; ++i) decoded.push_back(decodeSnapCandidate(candidates, i));

    const math::TrajectoryEstimate trajectory{ math::Point2D{ trajDirX, trajDirY }, trajConfidence };
    const math::SnapLockConfig config{ attractionRadius, breakawayRadius, commitFrames, scoreSharpness };

    const math::SnapLockResult result = math::SnapLockStateMachine::step(
        math::Point2D{ rawX, rawY }, trajectory, decoded,
        static_cast<math::SnapLockState>(prevState), prevCandidateIndex, prevStreak, config
    );

    return {
        result.point.x, result.point.y,
        static_cast<double>(static_cast<int>(result.state)),
        static_cast<double>(result.candidateIndex),
        static_cast<double>(result.streak)
    };
}

} // namespace aladyn::engine::boundary::internal
