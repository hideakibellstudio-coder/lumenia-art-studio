#include "GuideSnapEngine.hpp"
#include <cmath>
#include <algorithm>
#include <limits>

namespace aladyn::engine::math {

static constexpr double PI = 3.14159265358979323846;

utils::Point2D GuideSnapEngine::projectToLine(const utils::Point2D& p0, const utils::Point2D& p1, const utils::Point2D& q) noexcept {
    const double dx = p1.x - p0.x;
    const double dy = p1.y - p0.y;
    const double len2 = dx * dx + dy * dy;
    if (len2 < 1e-8) return p0;
    const double t = ((q.x - p0.x) * dx + (q.y - p0.y) * dy) / len2;
    return utils::Point2D{ p0.x + t * dx, p0.y + t * dy };
}

static inline utils::Point2D evalBezier(const utils::Point2D& p0, const utils::Point2D& p1, const utils::Point2D& p2, const utils::Point2D& p3, double t) noexcept {
    const double u = 1.0 - t;
    const double u2 = u * u;
    const double u3 = u2 * u;
    const double t2 = t * t;
    const double t3 = t2 * t;
    return utils::Point2D{
        p0.x * u3 + p1.x * (3.0 * u2 * t) + p2.x * (3.0 * u * t2) + p3.x * t3,
        p0.y * u3 + p1.y * (3.0 * u2 * t) + p2.y * (3.0 * u * t2) + p3.y * t3
    };
}

static inline utils::Point2D derivBezier(const utils::Point2D& p0, const utils::Point2D& p1, const utils::Point2D& p2, const utils::Point2D& p3, double t) noexcept {
    const double u = 1.0 - t;
    const double d0x = p1.x - p0.x, d0y = p1.y - p0.y;
    const double d1x = p2.x - p1.x, d1y = p2.y - p1.y;
    const double d2x = p3.x - p2.x, d2y = p3.y - p2.y;
    return utils::Point2D{
        d0x * (3.0 * u * u) + d1x * (6.0 * u * t) + d2x * (3.0 * t * t),
        d0y * (3.0 * u * u) + d1y * (6.0 * u * t) + d2y * (3.0 * t * t)
    };
}

utils::Point2D GuideSnapEngine::projectToBezier(const utils::Point2D& p0, const utils::Point2D& p1, const utils::Point2D& p2, const utils::Point2D& p3, const utils::Point2D& q) noexcept {
    const int N = 32;
    double bestT = 0.0;
    double bestD2 = std::numeric_limits<double>::max();

    for (int i = 0; i <= N; ++i) {
        const double t = static_cast<double>(i) / N;
        const utils::Point2D b = evalBezier(p0, p1, p2, p3, t);
        const double dx = b.x - q.x;
        const double dy = b.y - q.y;
        const double d2 = dx * dx + dy * dy;
        if (d2 < bestD2) {
            bestD2 = d2;
            bestT = t;
        }
    }

    double t = bestT;
    for (int iter = 0; iter < 6; ++iter) {
        const utils::Point2D b = evalBezier(p0, p1, p2, p3, t);
        const utils::Point2D bp = derivBezier(p0, p1, p2, p3, t);
        const double diffX = b.x - q.x;
        const double diffY = b.y - q.y;
        const double fPrime = 2.0 * (diffX * bp.x + diffY * bp.y);
        const double fPrime2 = 2.0 * (bp.x * bp.x + bp.y * bp.y);
        if (std::abs(fPrime2) < 1e-8) break;
        const double dt = fPrime / fPrime2;
        t = std::clamp(t - dt, 0.0, 1.0);
        if (std::abs(dt) < 1e-4) break;
    }

    return evalBezier(p0, p1, p2, p3, t);
}

utils::Point2D GuideSnapEngine::snapPoint(const GuideConfig& config, const utils::Point2D& rawPoint, const utils::Point2D* lastPoint) noexcept {
    // lastPoint nao e usado por Straight/CurveRuler (unicos tipos ainda
    // tratados aqui apos a Fase C3.1) -- mantido no contrato publico por
    // compatibilidade com o binding snap_point() ja exposto.
    (void)lastPoint;

    if (config.type == GuideType::None) {
        return rawPoint;
    }

    const double maxRadius2 = config.snapRadius * config.snapRadius;

    if (config.type == GuideType::Straight) {
        const utils::Point2D proj = projectToLine(config.p0, config.p1, rawPoint);
        const double dx = proj.x - rawPoint.x, dy = proj.y - rawPoint.y;
        return (dx * dx + dy * dy <= maxRadius2) ? proj : rawPoint;
    }

    if (config.type == GuideType::CurveRuler) {
        const utils::Point2D proj = projectToBezier(config.p0, config.p1, config.p2, config.p3, rawPoint);
        const double dx = proj.x - rawPoint.x, dy = proj.y - rawPoint.y;
        return (dx * dx + dy * dy <= maxRadius2) ? proj : rawPoint;
    }

    // OnePoint/TwoPoint/ThreePoint/Isometric: ver snapPerspective() (Fase C3.1)
    // -- a implementacao que existia aqui era codigo morto nunca chamado pela
    // UI, com um algoritmo estruturalmente diferente do que geometry_snapping_engine.py
    // realmente usa (reprojecao por lastPoint em vez de travar direcao no
    // inicio do traco). Removida para nao deixar duas implementacoes
    // divergentes do mesmo tipo de guia coexistindo no motor.

    return rawPoint;
}

// ---------------------------------------------------------------------------
// Perspectiva (1P/2P/3P/Isometric) -- Fase C3.1
//
// Porte fiel de snap_ray_perspective (geometry_snapping_engine.py), o
// algoritmo que a UI realmente usa hoje para essas 4 guias. Sem estado: quem
// chama (GeometryToolController) informa a direcao travada, se houver, e
// recebe de volta o que persistir para a proxima chamada -- mesmo contrato
// ja usado por CurvilinearSnapEngine::snap().
// ---------------------------------------------------------------------------

utils::Point2D GuideSnapEngine::snapPerspective(
    const GuideConfig& config,
    const utils::Point2D& rawPoint,
    const utils::Point2D& strokeStart,
    const utils::Point2D* lockedDir,
    double zoom,
    utils::Point2D& outLockedDir,
    bool& outHasLockedDir
) noexcept {
    outHasLockedDir = false;

    if (lockedDir != nullptr) {
        const double t = (rawPoint.x - strokeStart.x) * lockedDir->x + (rawPoint.y - strokeStart.y) * lockedDir->y;
        const utils::Point2D projected{ strokeStart.x + t * lockedDir->x, strokeStart.y + t * lockedDir->y };
        const double strayDx = rawPoint.x - projected.x;
        const double strayDy = rawPoint.y - projected.y;
        const double stray = std::sqrt(strayDx * strayDx + strayDy * strayDy);
        // Trava magnetica, nao rigida -- mesmo fix e mesmo raciocinio do
        // CurvilinearSnapEngine::snap() (Fase C3.5). Reusa config.snapRadius
        // como tolerancia de afastamento antes de soltar a trava.
        if (config.snapRadius <= 0.0 || stray <= config.snapRadius) {
            outLockedDir = *lockedDir;
            outHasLockedDir = true;
            return projected;
        }
    }

    const double dx = rawPoint.x - strokeStart.x;
    const double dy = rawPoint.y - strokeStart.y;
    const double dist = std::sqrt(dx * dx + dy * dy);
    if (dist < (2.5 / std::max(0.01, zoom))) {
        return strokeStart;
    }

    const double ux = dx / dist;
    const double uy = dy / dist;

    std::vector<utils::Point2D> candidates;

    if (config.type == GuideType::OnePoint) {
        double lA = std::hypot(config.vpA.x - strokeStart.x, config.vpA.y - strokeStart.y);
        if (lA == 0.0) lA = 1.0;
        candidates.push_back(utils::Point2D{ (config.vpA.x - strokeStart.x) / lA, (config.vpA.y - strokeStart.y) / lA });
        candidates.push_back(utils::Point2D{ 1.0, 0.0 });
        candidates.push_back(utils::Point2D{ 0.0, 1.0 });
    } else if (config.type == GuideType::TwoPoint) {
        double lA = std::hypot(config.vpA.x - strokeStart.x, config.vpA.y - strokeStart.y);
        double lB = std::hypot(config.vpB.x - strokeStart.x, config.vpB.y - strokeStart.y);
        if (lA == 0.0) lA = 1.0;
        if (lB == 0.0) lB = 1.0;
        candidates.push_back(utils::Point2D{ (config.vpA.x - strokeStart.x) / lA, (config.vpA.y - strokeStart.y) / lA });
        candidates.push_back(utils::Point2D{ (config.vpB.x - strokeStart.x) / lB, (config.vpB.y - strokeStart.y) / lB });
        const double hdx = config.vpB.x - config.vpA.x;
        const double hdy = config.vpB.y - config.vpA.y;
        double hlen = std::hypot(hdx, hdy);
        if (hlen == 0.0) hlen = 1.0;
        candidates.push_back(utils::Point2D{ -hdy / hlen, hdx / hlen });
    } else if (config.type == GuideType::ThreePoint) {
        const utils::Point2D* vps[3] = { &config.vpA, &config.vpB, &config.vpC };
        for (const utils::Point2D* vp : vps) {
            double l = std::hypot(vp->x - strokeStart.x, vp->y - strokeStart.y);
            if (l == 0.0) l = 1.0;
            candidates.push_back(utils::Point2D{ (vp->x - strokeStart.x) / l, (vp->y - strokeStart.y) / l });
        }
    } else if (config.type == GuideType::Isometric) {
        const double cos30 = std::cos(PI / 6.0);
        const double sin30 = std::sin(PI / 6.0);
        candidates.push_back(utils::Point2D{ 0.0, 1.0 });
        candidates.push_back(utils::Point2D{ cos30, sin30 });
        candidates.push_back(utils::Point2D{ -cos30, sin30 });
    }

    utils::Point2D bestDir{ 1.0, 0.0 };
    double maxDot = -1.0;
    for (const auto& c : candidates) {
        const double dot = std::abs(c.x * ux + c.y * uy);
        if (dot > maxDot) {
            maxDot = dot;
            bestDir = c;
        }
    }

    const double t = (rawPoint.x - strokeStart.x) * bestDir.x + (rawPoint.y - strokeStart.y) * bestDir.y;
    outLockedDir = bestDir;
    outHasLockedDir = true;
    return utils::Point2D{ strokeStart.x + t * bestDir.x, strokeStart.y + t * bestDir.y };
}

} // namespace aladyn::engine::math
