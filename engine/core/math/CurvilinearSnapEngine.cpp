#include "CurvilinearSnapEngine.hpp"
#include <cmath>
#include <algorithm>
#include <limits>

namespace aladyn::engine::math {

static constexpr double PI = 3.14159265358979323846;

// ═══════════════════════════════════════════════════════════════════════
// Curvilinear (6P fisheye) — Fase C2b
//
// Porta fiel de camera_3d_projector.py + geometry_snapping_engine.py
// (snap_curvilinear / get_dynamic_curves_at_point / find_nearest_primary_grid_curve).
// Sem estado: quem chama (GeometryToolController) continua dono do ciclo de
// vida do traço (curva travada, ponto de início), como já faz hoje.
// ═══════════════════════════════════════════════════════════════════════

void CurvilinearSnapEngine::rotate3DForward(double x, double y, double z, double yawRad, double pitchRad,
                                       double& outX, double& outY, double& outZ) noexcept {
    const double ch = std::cos(yawRad), sh = std::sin(yawRad);
    const double cv = std::cos(pitchRad), sv = std::sin(pitchRad);
    const double xr = x * ch - z * sh;
    const double yr = y;
    const double zr = x * sh + z * ch;
    outX = xr;
    outY = yr * cv - zr * sv;
    outZ = yr * sv + zr * cv;
}

void CurvilinearSnapEngine::rotate3DBackward(double x, double y, double z, double yawRad, double pitchRad,
                                        double& outX, double& outY, double& outZ) noexcept {
    const double ch = std::cos(yawRad), sh = std::sin(yawRad);
    const double cv = std::cos(pitchRad), sv = std::sin(pitchRad);
    const double xu = x;
    const double yu = y * cv + z * sv;
    const double zu = -y * sv + z * cv;
    outX = xu * ch + zu * sh;
    outY = yu;
    outZ = -xu * sh + zu * ch;
}

double CurvilinearSnapEngine::curvilinearCameraRadius(double fov, double baseRadius) noexcept {
    const double fovRad = fov * PI / 180.0;
    const double tanF = std::tan(fovRad / 4.0);
    return tanF > 1e-5 ? baseRadius / tanF : 1e9;
}

bool CurvilinearSnapEngine::curveFromNormal(double a, double b, double c, double R, double cx, double cy,
                                       CurveFamily family, CurvilinearCurve& out) noexcept {
    const double norm = std::sqrt(a * a + b * b + c * c);
    if (norm <= 1e-6) return false;
    a /= norm; b /= norm; c /= norm;

    out.family = family;

    if (std::abs(c) < 1e-6) {
        const double denom = std::sqrt(a * a + b * b);
        if (denom < 1e-6) return false;
        const double dx = b / denom, dy = a / denom;
        out.kind = CurveKind::Line;
        out.p1 = Point2D{ cx - dx * 100000.0, cy - dy * 100000.0 };
        out.p2 = Point2D{ cx + dx * 100000.0, cy + dy * 100000.0 };
        out.dir = Point2D{ dx, dy };
        return true;
    }

    out.kind = CurveKind::Circle;
    out.center = Point2D{ cx + (-R * a / c), cy + (R * b / c) };
    out.radius = R / std::abs(c);
    return true;
}

Point2D CurvilinearSnapEngine::closestPointOnCurve(const CurvilinearCurve& curve, const Point2D& pt) noexcept {
    if (curve.kind == CurveKind::Line) {
        const double vx = curve.p2.x - curve.p1.x;
        const double vy = curve.p2.y - curve.p1.y;
        const double len2 = vx * vx + vy * vy;
        if (len2 < 1e-6) return curve.p1;
        const double t = ((pt.x - curve.p1.x) * vx + (pt.y - curve.p1.y) * vy) / len2;
        return Point2D{ curve.p1.x + t * vx, curve.p1.y + t * vy };
    }
    const double dx = pt.x - curve.center.x;
    const double dy = pt.y - curve.center.y;
    const double dist = std::sqrt(dx * dx + dy * dy);
    if (dist > 1e-5) {
        return Point2D{ curve.center.x + (dx / dist) * curve.radius, curve.center.y + (dy / dist) * curve.radius };
    }
    return Point2D{ curve.center.x + curve.radius, curve.center.y };
}

std::vector<CurvilinearCurve> CurvilinearSnapEngine::candidates(const GuideConfig& config, const Point2D& clickPt) noexcept {
    std::vector<CurvilinearCurve> curves;

    const double R = curvilinearCameraRadius(config.fov, config.baseRadius);
    const double X = (clickPt.x - config.cx) / R;
    const double Y = -(clickPt.y - config.cy) / R;
    const double r2 = X * X + Y * Y;
    const double denom = r2 + 1.0;
    const double x3 = 2.0 * X / denom, y3 = 2.0 * Y / denom, z3 = (r2 - 1.0) / denom;

    const double yawRad = config.yaw * PI / 180.0;
    const double pitchRad = config.pitch * PI / 180.0;
    double xw, yw, zw;
    rotate3DForward(x3, y3, z3, yawRad, pitchRad, xw, yw, zw);

    // 1. Curva Vertical (V)
    if (config.showV || config.showGroundVerticals || config.showCeilingVerticals || config.showStraightVerticals) {
        double aV, bV, cV;
        rotate3DBackward(zw, 0.0, -xw, yawRad, pitchRad, aV, bV, cV);
        if (config.showStraightVerticals) {
            const double Tx = bV * z3 - cV * y3;
            const double Ty = cV * x3 - aV * z3;
            const double Tz = aV * y3 - bV * x3;
            const double dz = 1.0 - z3;
            double dx = Tx * dz + x3 * Tz;
            double dy = -(Ty * dz + y3 * Tz);
            const double l = std::sqrt(dx * dx + dy * dy);
            if (l > 1e-9) { dx /= l; dy /= l; }
            CurvilinearCurve line;
            line.kind = CurveKind::Line;
            line.family = CurveFamily::GroundV;
            line.p1 = Point2D{ clickPt.x - dx * 20000.0, clickPt.y - dy * 20000.0 };
            line.p2 = Point2D{ clickPt.x + dx * 20000.0, clickPt.y + dy * 20000.0 };
            line.dir = Point2D{ dx, dy };
            curves.push_back(line);
        } else {
            CurvilinearCurve cv;
            if (curveFromNormal(aV, bV, cV, R, config.cx, config.cy, CurveFamily::GroundV, cv)) {
                curves.push_back(cv);
            }
        }
    }

    // 2. Curva Transversal (H)
    if (config.showH || config.showGround || config.showCeiling) {
        double aH, bH, cH;
        rotate3DBackward(0.0, -zw, yw, yawRad, pitchRad, aH, bH, cH);
        CurvilinearCurve ch;
        if (curveFromNormal(aH, bH, cH, R, config.cx, config.cy, CurveFamily::GroundX, ch)) {
            curves.push_back(ch);
        }
    }

    // 3. Curva de Profundidade (D)
    if (config.showD || config.showGround || config.showCeiling) {
        double aD, bD, cD;
        rotate3DBackward(-yw, xw, 0.0, yawRad, pitchRad, aD, bD, cD);
        CurvilinearCurve cd;
        if (curveFromNormal(aD, bD, cD, R, config.cx, config.cy, CurveFamily::GroundZ, cd)) {
            curves.push_back(cd);
        }
    }

    return curves;
}

bool CurvilinearSnapEngine::nearestPrimaryGridCurve(const GuideConfig& config, const Point2D& pt, double maxDist, CurvilinearCurve& out) noexcept {
    const double R = curvilinearCameraRadius(config.fov, config.baseRadius);
    const double dRad = config.density * PI / 180.0;
    const double yawRad = config.yaw * PI / 180.0;
    const double pitchRad = config.pitch * PI / 180.0;
    if (dRad < 1e-6) return false;
    const int steps = static_cast<int>(PI / dRad) + 1;

    std::vector<CurvilinearCurve> grid;
    grid.reserve(static_cast<size_t>(steps) * 3);

    if (config.showV) {
        for (int i = 0; i < steps; ++i) {
            double a, b, c;
            rotate3DBackward(std::cos(i * dRad), 0.0, std::sin(i * dRad), yawRad, pitchRad, a, b, c);
            CurvilinearCurve cv;
            if (curveFromNormal(a, b, c, R, config.cx, config.cy, CurveFamily::GroundV, cv)) grid.push_back(cv);
        }
    }
    if (config.showH) {
        for (int i = 0; i < steps; ++i) {
            const double ang = -PI / 2.0 + i * dRad;
            double a, b, c;
            rotate3DBackward(0.0, -std::sin(ang), std::cos(ang), yawRad, pitchRad, a, b, c);
            CurvilinearCurve ch;
            if (curveFromNormal(a, b, c, R, config.cx, config.cy, CurveFamily::GroundX, ch)) grid.push_back(ch);
        }
    }
    if (config.showD) {
        for (int i = 0; i < steps; ++i) {
            double a, b, c;
            rotate3DBackward(-std::sin(i * dRad), std::cos(i * dRad), 0.0, yawRad, pitchRad, a, b, c);
            CurvilinearCurve cd;
            if (curveFromNormal(a, b, c, R, config.cx, config.cy, CurveFamily::GroundZ, cd)) grid.push_back(cd);
        }
    }

    bool found = false;
    double bestD = maxDist;
    for (const auto& c : grid) {
        const Point2D cp = closestPointOnCurve(c, pt);
        const double d = std::sqrt((pt.x - cp.x) * (pt.x - cp.x) + (pt.y - cp.y) * (pt.y - cp.y));
        if (d < bestD) {
            bestD = d;
            out = c;
            found = true;
        }
    }
    return found;
}

Point2D CurvilinearSnapEngine::snap(
    const GuideConfig& config,
    const Point2D& rawPoint,
    const Point2D& strokeStart,
    const std::vector<CurvilinearCurve>& candidates,
    int lockedIndex,
    bool isStroking,
    double zoom,
    int& outLockedIndex
) noexcept {
    outLockedIndex = -1;

    if (lockedIndex >= 0 && lockedIndex < static_cast<int>(candidates.size())) {
        const Point2D locked = closestPointOnCurve(candidates[lockedIndex], rawPoint);
        const double strayDx = rawPoint.x - locked.x;
        const double strayDy = rawPoint.y - locked.y;
        const double stray = std::sqrt(strayDx * strayDx + strayDy * strayDy);
        // Trava magnetica, nao rigida (Fase C3.5 -- bug reportado: tracos
        // muito rapidos travam numa curva cedo demais, a partir de uma unica
        // amostra de gesto grosseira, e ficam presos nela pelo resto do
        // traco mesmo quando o cursor claramente segue outra curva. Reusa
        // config.snapRadius (mesmo campo que Straight/CurveRuler usam como
        // raio de atracao) como raio de tolerancia: se o cursor se afastar
        // da curva travada alem dele, solta a trava e reavalia do zero
        // neste frame em vez de projetar para sempre num alvo que deixou de
        // ser a intencao do gesto. snapRadius <= 0 desativa (compatibilidade).
        if (config.snapRadius <= 0.0 || stray <= config.snapRadius) {
            outLockedIndex = lockedIndex;
            return locked;
        }
    }

    const double dx = rawPoint.x - strokeStart.x;
    const double dy = rawPoint.y - strokeStart.y;
    const double dist = std::sqrt(dx * dx + dy * dy);

    // Filtro por snap_mode (v/h/d) -- mapeamento direto mode->familia (fix
    // Fase C3.0, espelha a correcao equivalente em geometry_snapping_engine.py;
    // familias geradas sao sempre ground_v/ground_x/ground_z, nunca "*_h"/"*_d",
    // entao o filtro por sufixo original nunca batia com H ou D).
    std::vector<int> idx;
    idx.reserve(candidates.size());
    for (int i = 0; i < static_cast<int>(candidates.size()); ++i) {
        if (config.snapMode == 0) { idx.push_back(i); continue; }
        if (config.snapMode != 1 && config.snapMode != 2 && config.snapMode != 3) continue;
        CurveFamily wanted = config.snapMode == 2 ? CurveFamily::GroundX
                            : config.snapMode == 3 ? CurveFamily::GroundZ
                            : CurveFamily::GroundV;
        if (candidates[i].family == wanted) idx.push_back(i);
    }

    if (idx.empty()) {
        return rawPoint;
    }

    // Modo restrito (v/h/d) durante o traço: trava direto na primeira curva
    // da família filtrada, sem passar pela pontuação por distância/direção
    // (espelha o `if mode in ("v","h","d") and is_stroking: lock = curves[0]`
    // do Python).
    if (config.snapMode != 0 && isStroking) {
        outLockedIndex = idx[0];
        return closestPointOnCurve(candidates[idx[0]], rawPoint);
    }

    const double sens = config.snapSensitivity;
    const double lockThresh = std::max(2.0, (7.5 - sens * 1.2)) / std::max(0.01, zoom);

    if (dist < lockThresh) {
        int bestI = idx[0];
        double bestDist = std::numeric_limits<double>::max();
        for (int i : idx) {
            const Point2D cp = closestPointOnCurve(candidates[i], rawPoint);
            const double d = std::sqrt((rawPoint.x - cp.x) * (rawPoint.x - cp.x) + (rawPoint.y - cp.y) * (rawPoint.y - cp.y));
            if (d < bestDist) { bestDist = d; bestI = i; }
        }
        // Sem travar: aproximação por proximidade, não por direção do gesto
        // (espelha o retorno `None` de lock em snap_curvilinear() para este caso).
        return closestPointOnCurve(candidates[bestI], rawPoint);
    }

    const double ux = dx / dist, uy = dy / dist;
    int bestI = idx[0];
    double bestScore = -1.0;
    for (int i : idx) {
        const auto& c = candidates[i];
        const Point2D cp = closestPointOnCurve(c, rawPoint);
        double tdx, tdy;
        if (c.kind == CurveKind::Line) {
            tdx = c.dir.x; tdy = c.dir.y;
        } else {
            const double cdx = cp.x - c.center.x, cdy = cp.y - c.center.y;
            const double clen = std::sqrt(cdx * cdx + cdy * cdy);
            const double inv = clen > 1e-9 ? 1.0 / clen : 1.0;
            tdx = -cdy * inv; tdy = cdx * inv;
        }
        const double dot = std::abs(ux * tdx + uy * tdy);
        const double d = std::sqrt((rawPoint.x - cp.x) * (rawPoint.x - cp.x) + (rawPoint.y - cp.y) * (rawPoint.y - cp.y));
        const double score = dot / std::max(1.0, d * 0.05);
        if (score > bestScore) { bestScore = score; bestI = i; }
    }

    if (isStroking) outLockedIndex = bestI;
    return closestPointOnCurve(candidates[bestI], rawPoint);
}

} // namespace aladyn::engine::math
