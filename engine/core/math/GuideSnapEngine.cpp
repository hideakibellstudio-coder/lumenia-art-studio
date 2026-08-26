#include "GuideSnapEngine.hpp"
#include <cmath>
#include <algorithm>
#include <limits>

namespace aladyn::engine::math {

static constexpr double PI = 3.14159265358979323846;

Point2D GuideSnapEngine::projectToLine(const Point2D& p0, const Point2D& p1, const Point2D& q) noexcept {
    const double dx = p1.x - p0.x;
    const double dy = p1.y - p0.y;
    const double len2 = dx * dx + dy * dy;
    if (len2 < 1e-8) return p0;
    const double t = ((q.x - p0.x) * dx + (q.y - p0.y) * dy) / len2;
    return Point2D{ p0.x + t * dx, p0.y + t * dy };
}

static inline Point2D evalBezier(const Point2D& p0, const Point2D& p1, const Point2D& p2, const Point2D& p3, double t) noexcept {
    const double u = 1.0 - t;
    const double u2 = u * u;
    const double u3 = u2 * u;
    const double t2 = t * t;
    const double t3 = t2 * t;
    return Point2D{
        p0.x * u3 + p1.x * (3.0 * u2 * t) + p2.x * (3.0 * u * t2) + p3.x * t3,
        p0.y * u3 + p1.y * (3.0 * u2 * t) + p2.y * (3.0 * u * t2) + p3.y * t3
    };
}

static inline Point2D derivBezier(const Point2D& p0, const Point2D& p1, const Point2D& p2, const Point2D& p3, double t) noexcept {
    const double u = 1.0 - t;
    const double d0x = p1.x - p0.x, d0y = p1.y - p0.y;
    const double d1x = p2.x - p1.x, d1y = p2.y - p1.y;
    const double d2x = p3.x - p2.x, d2y = p3.y - p2.y;
    return Point2D{
        d0x * (3.0 * u * u) + d1x * (6.0 * u * t) + d2x * (3.0 * t * t),
        d0y * (3.0 * u * u) + d1y * (6.0 * u * t) + d2y * (3.0 * t * t)
    };
}

Point2D GuideSnapEngine::projectToBezier(const Point2D& p0, const Point2D& p1, const Point2D& p2, const Point2D& p3, const Point2D& q) noexcept {
    const int N = 32;
    double bestT = 0.0;
    double bestD2 = std::numeric_limits<double>::max();

    for (int i = 0; i <= N; ++i) {
        const double t = static_cast<double>(i) / N;
        const Point2D b = evalBezier(p0, p1, p2, p3, t);
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
        const Point2D b = evalBezier(p0, p1, p2, p3, t);
        const Point2D bp = derivBezier(p0, p1, p2, p3, t);
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

Point2D GuideSnapEngine::snapPoint(const GuideConfig& config, const Point2D& rawPoint, const Point2D* lastPoint) noexcept {
    if (config.type == GuideType::None) {
        return rawPoint;
    }

    const double maxRadius2 = config.snapRadius * config.snapRadius;

    if (config.type == GuideType::Straight) {
        const Point2D proj = projectToLine(config.p0, config.p1, rawPoint);
        const double dx = proj.x - rawPoint.x, dy = proj.y - rawPoint.y;
        return (dx * dx + dy * dy <= maxRadius2) ? proj : rawPoint;
    }

    if (config.type == GuideType::CurveRuler) {
        const Point2D proj = projectToBezier(config.p0, config.p1, config.p2, config.p3, rawPoint);
        const double dx = proj.x - rawPoint.x, dy = proj.y - rawPoint.y;
        return (dx * dx + dy * dy <= maxRadius2) ? proj : rawPoint;
    }

    if (config.type == GuideType::Isometric) {
        if (!lastPoint) return rawPoint;
        const Point2D lp = *lastPoint;
        const Point2D cand1 = projectToLine(lp, Point2D{ lp.x + std::cos(PI / 6.0), lp.y + std::sin(PI / 6.0) }, rawPoint);
        const Point2D cand2 = projectToLine(lp, Point2D{ lp.x, lp.y + 1.0 }, rawPoint);
        const Point2D cand3 = projectToLine(lp, Point2D{ lp.x + std::cos(5.0 * PI / 6.0), lp.y + std::sin(5.0 * PI / 6.0) }, rawPoint);

        double minD2 = (cand1.x - rawPoint.x)*(cand1.x - rawPoint.x) + (cand1.y - rawPoint.y)*(cand1.y - rawPoint.y);
        Point2D best = cand1;

        const double d2_2 = (cand2.x - rawPoint.x)*(cand2.x - rawPoint.x) + (cand2.y - rawPoint.y)*(cand2.y - rawPoint.y);
        if (d2_2 < minD2) { minD2 = d2_2; best = cand2; }

        const double d3_2 = (cand3.x - rawPoint.x)*(cand3.x - rawPoint.x) + (cand3.y - rawPoint.y)*(cand3.y - rawPoint.y);
        if (d3_2 < minD2) { minD2 = d3_2; best = cand3; }

        return (minD2 <= maxRadius2) ? best : rawPoint;
    }

    if (config.type == GuideType::OnePoint) {
        const Point2D pRay = projectToLine(config.vpA, rawPoint, rawPoint);
        const Point2D ray = projectToLine(config.vpA, (lastPoint ? *lastPoint : rawPoint), rawPoint);
        const Point2D pH = lastPoint ? projectToLine(*lastPoint, Point2D{ lastPoint->x + 1.0, lastPoint->y }, rawPoint) : rawPoint;
        const Point2D pV = lastPoint ? projectToLine(*lastPoint, Point2D{ lastPoint->x, lastPoint->y + 1.0 }, rawPoint) : rawPoint;

        double minD2 = (ray.x - rawPoint.x)*(ray.x - rawPoint.x) + (ray.y - rawPoint.y)*(ray.y - rawPoint.y);
        Point2D best = ray;

        if (lastPoint) {
            const double dH = (pH.x - rawPoint.x)*(pH.x - rawPoint.x) + (pH.y - rawPoint.y)*(pH.y - rawPoint.y);
            if (dH < minD2) { minD2 = dH; best = pH; }
            const double dV = (pV.x - rawPoint.x)*(pV.x - rawPoint.x) + (pV.y - rawPoint.y)*(pV.y - rawPoint.y);
            if (dV < minD2) { minD2 = dV; best = pV; }
        }
        return (minD2 <= maxRadius2) ? best : rawPoint;
    }

    if (config.type == GuideType::TwoPoint) {
        const Point2D rayA = projectToLine(config.vpA, (lastPoint ? *lastPoint : rawPoint), rawPoint);
        const Point2D rayB = projectToLine(config.vpB, (lastPoint ? *lastPoint : rawPoint), rawPoint);
        const Point2D pV = lastPoint ? projectToLine(*lastPoint, Point2D{ lastPoint->x, lastPoint->y + 1.0 }, rawPoint) : rawPoint;

        double minD2 = (rayA.x - rawPoint.x)*(rayA.x - rawPoint.x) + (rayA.y - rawPoint.y)*(rayA.y - rawPoint.y);
        Point2D best = rayA;

        const double dB = (rayB.x - rawPoint.x)*(rayB.x - rawPoint.x) + (rayB.y - rawPoint.y)*(rayB.y - rawPoint.y);
        if (dB < minD2) { minD2 = dB; best = rayB; }

        if (lastPoint) {
            const double dV = (pV.x - rawPoint.x)*(pV.x - rawPoint.x) + (pV.y - rawPoint.y)*(pV.y - rawPoint.y);
            if (dV < minD2) { minD2 = dV; best = pV; }
        }
        return (minD2 <= maxRadius2) ? best : rawPoint;
    }

    if (config.type == GuideType::ThreePoint) {
        const Point2D rayA = projectToLine(config.vpA, (lastPoint ? *lastPoint : rawPoint), rawPoint);
        const Point2D rayB = projectToLine(config.vpB, (lastPoint ? *lastPoint : rawPoint), rawPoint);
        const Point2D rayC = projectToLine(config.vpC, (lastPoint ? *lastPoint : rawPoint), rawPoint);

        double minD2 = (rayA.x - rawPoint.x)*(rayA.x - rawPoint.x) + (rayA.y - rawPoint.y)*(rayA.y - rawPoint.y);
        Point2D best = rayA;

        const double dB = (rayB.x - rawPoint.x)*(rayB.x - rawPoint.x) + (rayB.y - rawPoint.y)*(rayB.y - rawPoint.y);
        if (dB < minD2) { minD2 = dB; best = rayB; }

        const double dC = (rayC.x - rawPoint.x)*(rayC.x - rawPoint.x) + (rayC.y - rawPoint.y)*(rayC.y - rawPoint.y);
        if (dC < minD2) { minD2 = dC; best = rayC; }

        return (minD2 <= maxRadius2) ? best : rawPoint;
    }

    return rawPoint;
}

} // namespace aladyn::engine::math
