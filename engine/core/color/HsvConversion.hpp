#ifndef ALADYN_ENGINE_HSV_CONVERSION_HPP
#define ALADYN_ENGINE_HSV_CONVERSION_HPP

// Conversão RGB <-> HSV em float [0, 1] (matiz em graus). Usada pelo filtro
// Matiz/Saturação; saiu de document/blending/BlendEquations.hpp em 2026-09-25
// para os filtros não dependerem da mesclagem de camadas.

#include <algorithm>
#include <cmath>

namespace aladyn::engine::color {

inline void rgbToHsv(float r, float g, float b, float& h, float& s, float& v) noexcept {
    const float minVal = std::min({r, g, b});
    const float maxVal = std::max({r, g, b});
    const float delta = maxVal - minVal;
    v = maxVal;
    if (maxVal == 0.0f || delta == 0.0f) {
        s = 0.0f;
        h = 0.0f;
        return;
    }
    s = delta / maxVal;
    if (r == maxVal) h = (g - b) / delta;
    else if (g == maxVal) h = 2.0f + (b - r) / delta;
    else h = 4.0f + (r - g) / delta;
    h *= 60.0f;
    if (h < 0.0f) h += 360.0f;
}

inline void hsvToRgb(float h, float s, float v, float& r, float& g, float& b) noexcept {
    if (s == 0.0f) {
        r = g = b = v;
        return;
    }
    h = std::fmod(h, 360.0f);
    if (h < 0.0f) h += 360.0f;
    const float c = v * s;
    const float x = c * (1.0f - std::abs(std::fmod(h / 60.0f, 2.0f) - 1.0f));
    const float m = v - c;
    float r1 = 0, g1 = 0, b1 = 0;
    if (h < 60.0f)       { r1 = c; g1 = x; b1 = 0; }
    else if (h < 120.0f) { r1 = x; g1 = c; b1 = 0; }
    else if (h < 180.0f) { r1 = 0; g1 = c; b1 = x; }
    else if (h < 240.0f) { r1 = 0; g1 = x; b1 = c; }
    else if (h < 300.0f) { r1 = x; g1 = 0; b1 = c; }
    else                 { r1 = c; g1 = 0; b1 = x; }
    r = r1 + m;
    g = g1 + m;
    b = b1 + m;
}

} // namespace aladyn::engine::color

#endif // ALADYN_ENGINE_HSV_CONVERSION_HPP
