#ifndef ALADYN_ENGINE_TRANSFORM_HOMOGRAPHY_HPP
#define ALADYN_ENGINE_TRANSFORM_HOMOGRAPHY_HPP

// Transformação projetiva (homografia) usada por Transformar -> Distorcer.
// Cantos sempre na ordem TL, TR, BR, BL: (x0,y0, x1,y1, x2,y2, x3,y3).
// É o mesmo mapeamento que QTransform::quadToQuad usa na prévia da UI (a
// homografia que leva 4 pontos em 4 pontos é única), então prévia e commit
// coincidem.

#include <array>
#include <cmath>

namespace aladyn::engine::raster::transform {

using Quad = std::array<double, 8>;

struct Homography {
    // Linha-maior: [m0 m1 m2; m3 m4 m5; m6 m7 m8]
    std::array<double, 9> m{1, 0, 0, 0, 1, 0, 0, 0, 1};

    /// false quando o ponto cai na linha do horizonte (w ~ 0).
    bool apply(double x, double y, double& ox, double& oy) const noexcept {
        const double w = m[6] * x + m[7] * y + m[8];
        if (std::abs(w) < 1e-12) return false;
        ox = (m[0] * x + m[1] * y + m[2]) / w;
        oy = (m[3] * x + m[4] * y + m[5]) / w;
        return true;
    }
};

/// Quadrado unitário (0,0),(1,0),(1,1),(0,1) -> quad (Heckbert, 1989).
inline Homography unitSquareToQuad(const Quad& q) noexcept {
    const double x0 = q[0], y0 = q[1], x1 = q[2], y1 = q[3];
    const double x2 = q[4], y2 = q[5], x3 = q[6], y3 = q[7];
    const double sx = x0 - x1 + x2 - x3;
    const double sy = y0 - y1 + y2 - y3;
    Homography h;
    if (std::abs(sx) < 1e-12 && std::abs(sy) < 1e-12) {  // paralelogramo: afim
        h.m = {x1 - x0, x3 - x0, x0, y1 - y0, y3 - y0, y0, 0.0, 0.0, 1.0};
        return h;
    }
    const double dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2;
    const double det = dx1 * dy2 - dx2 * dy1;
    const double g = (sx * dy2 - dx2 * sy) / det;
    const double hh = (dx1 * sy - sx * dy1) / det;
    h.m = {x1 - x0 + g * x1, x3 - x0 + hh * x3, x0,
           y1 - y0 + g * y1, y3 - y0 + hh * y3, y0,
           g, hh, 1.0};
    return h;
}

/// Inversa por adjunta; false se singular.
inline bool invert(const Homography& h, Homography& inv) noexcept {
    const auto& a = h.m;
    const double c0 = a[4] * a[8] - a[5] * a[7];
    const double c1 = a[5] * a[6] - a[3] * a[8];
    const double c2 = a[3] * a[7] - a[4] * a[6];
    const double det = a[0] * c0 + a[1] * c1 + a[2] * c2;
    if (std::abs(det) < 1e-12) return false;
    inv.m = {c0, a[2] * a[7] - a[1] * a[8], a[1] * a[5] - a[2] * a[4],
             c1, a[0] * a[8] - a[2] * a[6], a[2] * a[3] - a[0] * a[5],
             c2, a[1] * a[6] - a[0] * a[7], a[0] * a[4] - a[1] * a[3]};
    for (auto& v : inv.m) v /= det;
    return true;
}

/// Quad estritamente convexo (sem auto-interseção nem canto colapsado).
/// Só nesse caso o mapeamento é bem-comportado dentro do quadrilátero.
inline bool isConvexQuad(const Quad& q) noexcept {
    for (double v : q) {
        if (!std::isfinite(v)) return false;
    }
    int sign = 0;
    for (int i = 0; i < 4; ++i) {
        const int j = (i + 1) % 4, k = (i + 2) % 4;
        const double ex = q[2 * j] - q[2 * i], ey = q[2 * j + 1] - q[2 * i + 1];
        const double fx = q[2 * k] - q[2 * j], fy = q[2 * k + 1] - q[2 * j + 1];
        const double cross = ex * fy - ey * fx;
        if (std::abs(cross) < 1e-6) return false;
        const int s = cross > 0 ? 1 : -1;
        if (sign == 0) sign = s;
        else if (s != sign) return false;
    }
    return true;
}

} // namespace aladyn::engine::raster::transform

#endif // ALADYN_ENGINE_TRANSFORM_HOMOGRAPHY_HPP
