#pragma once

#include "../../../core/math/GuideSnapEngine.hpp"
#include "../../../core/math/CurvilinearSnapEngine.hpp"
#include "../../../core/math/SnapCandidate.hpp"
#include "../../../core/math/TrajectoryEstimator.hpp"
#include "../../../core/math/SnapLockStateMachine.hpp"
#include <vector>

namespace aladyn::engine::boundary::internal {

// Orquestrador de guias, simetria de perspectiva e snap.
//
// Extraido de PaintEngineFacade.cpp (Achado #6). Todo este bloco ja era
// funcionalmente isolado: o unico estado que ele le e' o math::GuideConfig do
// documento, que agora entra por parametro. Nada aqui toca camadas, buffers,
// historico ou telemetria -- por isso sai inteiro do facade sem contexto
// nenhum alem da propria configuracao de guia.
//
// Os metodos de codificacao plana (11 doubles por curva, 9 por candidata)
// continuam sendo a convencao de travessia da fronteira PyBind11 sem registrar
// tipos novos; o facade apenas repassa os vetores.
class SnapOrchestrator {
public:
    static void setGuideConfig(
        math::GuideConfig& cfg,
        int type, double p0x, double p0y, double p1x, double p1y, double p2x, double p2y, double p3x, double p3y,
        double vpAx, double vpAy, double vpBx, double vpBy, double vpCx, double vpCy, double cx, double cy,
        double fov, double pitch, double yaw, double snapRadius
    );

    static void setCurvilinearGuideConfig(
        math::GuideConfig& cfg,
        double baseRadius, double density,
        bool showV, bool showH, bool showD,
        bool showGround, bool showCeiling,
        bool showGroundVerticals, bool showCeilingVerticals,
        bool showStraightVerticals,
        int snapMode, double snapSensitivity
    );

    static std::vector<double> snapPoint(
        const math::GuideConfig& cfg,
        double rawX, double rawY, double lastX, double lastY, bool hasLast
    );

    static std::vector<double> getCurvilinearCandidates(
        const math::GuideConfig& cfg, double clickX, double clickY
    );

    static std::vector<double> getNearestPrimaryGridCurve(
        const math::GuideConfig& cfg, double x, double y, double maxDist
    );

    static std::vector<double> snapCurvilinear(
        const math::GuideConfig& cfg,
        double rawX, double rawY, double startX, double startY,
        const std::vector<double>& candidates, int lockedIndex, bool isStroking, double zoom
    );

    static std::vector<double> snapPerspective(
        const math::GuideConfig& cfg,
        double rawX, double rawY, double startX, double startY,
        bool hasLockedDir, double lockedDirX, double lockedDirY, double zoom
    );

    // Fase D0: puros e sem estado -- nao leem GuideConfig (ver comentario no .cpp).
    static std::vector<double> estimateTrajectory(
        const std::vector<double>& recentPoints, double zoom
    );

    static std::vector<double> stepSnapLock(
        double rawX, double rawY,
        double trajDirX, double trajDirY, double trajConfidence,
        const std::vector<double>& candidates,
        int prevState, int prevCandidateIndex, int prevStreak,
        double attractionRadius, double breakawayRadius, int commitFrames, double scoreSharpness
    );
};

} // namespace aladyn::engine::boundary::internal
