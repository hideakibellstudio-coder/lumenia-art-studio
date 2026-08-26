#include "SymmetryEngine.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::math {

static constexpr double PI = 3.14159265358979323846;

Point2D SymmetryEngine::mirrorPoint(double x, double y, double cx, double cy, double cosA, double sinA) noexcept {
    const double dx = x - cx;
    const double dy = y - cy;
    const double dot = dx * cosA + dy * sinA;
    const double perpX = dx - dot * cosA;
    const double perpY = dy - dot * sinA;
    return Point2D{ cx + dot * cosA - perpX, cy + dot * sinA - perpY };
}

void SymmetryEngine::apply(
    const SymmetryConfig& config,
    const raster::Dab& dab,
    const Point2D* strokeStart,
    std::vector<raster::Dab>& outDabs
) {
    if (config.mode == SymmetryMode::None) {
        outDabs.push_back(dab);
        return;
    }

    const double cx = config.cx;
    const double cy = config.cy;
    const double angle = config.angleRad;
    const double cosA = std::cos(angle);
    const double sinA = std::sin(angle);

    if (config.mode == SymmetryMode::Mirror) {
        if (config.stopAtCenter && strokeStart) {
            const double sideStart = -(strokeStart->x - cx) * sinA + (strokeStart->y - cy) * cosA;
            const double sideCurr  = -(dab.position.x - cx) * sinA + (dab.position.y - cy) * cosA;
            if (sideStart * sideCurr < 0.0) return;
        }

        outDabs.push_back(dab);

        const Point2D mp = mirrorPoint(dab.position.x, dab.position.y, cx, cy, cosA, sinA);
        raster::Dab mDab = dab;
        mDab.position = mp;
        mDab.angle = 2.0 * angle - dab.angle;
        outDabs.push_back(mDab);
        return;
    }

    if (config.mode == SymmetryMode::DoubleMirror) {
        const double anglePerp = angle + PI / 2.0;
        const double cosP = std::cos(anglePerp);
        const double sinP = std::sin(anglePerp);

        if (config.stopAtCenter && strokeStart) {
            const double s1Start = -(strokeStart->x - cx) * sinA + (strokeStart->y - cy) * cosA;
            const double s1Curr  = -(dab.position.x - cx) * sinA + (dab.position.y - cy) * cosA;
            if (s1Start * s1Curr < 0.0) return;

            const double s2Start = -(strokeStart->x - cx) * sinP + (strokeStart->y - cy) * cosP;
            const double s2Curr  = -(dab.position.x - cx) * sinP + (dab.position.y - cy) * cosP;
            if (s2Start * s2Curr < 0.0) return;
        }

        outDabs.push_back(dab);

        // 1. Espelho primário
        const Point2D m1 = mirrorPoint(dab.position.x, dab.position.y, cx, cy, cosA, sinA);
        raster::Dab d1 = dab;
        d1.position = m1;
        d1.angle = 2.0 * angle - dab.angle;
        outDabs.push_back(d1);

        // 2. Espelho secundário (perpendicular)
        const Point2D m2 = mirrorPoint(dab.position.x, dab.position.y, cx, cy, cosP, sinP);
        raster::Dab d2 = dab;
        d2.position = m2;
        d2.angle = 2.0 * anglePerp - dab.angle;
        outDabs.push_back(d2);

        // 3. Inversão diagonal (duplo espelho)
        const Point2D m3{ 2.0 * cx - dab.position.x, 2.0 * cy - dab.position.y };
        raster::Dab d3 = dab;
        d3.position = m3;
        d3.angle = dab.angle + PI;
        outDabs.push_back(d3);
        return;
    }

    if (config.mode == SymmetryMode::Radial) {
        const int segs = std::clamp(config.segments, 2, 32);
        const double step = (2.0 * PI) / segs;
        const double dx = dab.position.x - cx;
        const double dy = dab.position.y - cy;

        for (int i = 0; i < segs; ++i) {
            const double a = i * step;
            const double ca = std::cos(a);
            const double sa = std::sin(a);

            raster::Dab rDab = dab;
            rDab.position = Point2D{ cx + dx * ca - dy * sa, cy + dx * sa + dy * ca };
            rDab.angle = dab.angle + a;
            outDabs.push_back(rDab);
        }
        return;
    }

    if (config.mode == SymmetryMode::Kaleidoscope) {
        const int segs = std::clamp(config.segments, 2, 32);
        const double step = (2.0 * PI) / segs;
        const double dx = dab.position.x - cx;
        const double dy = dab.position.y - cy;

        for (int i = 0; i < segs; ++i) {
            const double a = i * step;
            const double ca = std::cos(a);
            const double sa = std::sin(a);

            raster::Dab rDab = dab;
            rDab.position = Point2D{ cx + dx * ca - dy * sa, cy + dx * sa + dy * ca };
            rDab.angle = dab.angle + a;
            outDabs.push_back(rDab);

            // Espelho em cada setor
            const double mirAngle = angle + a;
            const double cM = std::cos(mirAngle);
            const double sM = std::sin(mirAngle);
            const Point2D mp = mirrorPoint(rDab.position.x, rDab.position.y, cx, cy, cM, sM);

            raster::Dab kDab = rDab;
            kDab.position = mp;
            kDab.angle = 2.0 * mirAngle - rDab.angle;
            outDabs.push_back(kDab);
        }
        return;
    }
}

} // namespace aladyn::engine::math
