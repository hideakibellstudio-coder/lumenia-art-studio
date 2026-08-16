#include "Texture2D.hpp"
#include "../math/MathUtils.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::texture {

Texture2D::Texture2D(int width, int height, uint8_t fillValue)
    : m_width(width), m_height(height), m_data(static_cast<size_t>(width * height), fillValue) {}

Texture2D::Texture2D(int width, int height, std::vector<uint8_t> data)
    : m_width(width), m_height(height), m_data(std::move(data)) {
    if (m_data.size() != static_cast<size_t>(width * height)) {
        m_data.resize(static_cast<size_t>(width * height), 255);
    }
}

void Texture2D::setPixel(int x, int y, uint8_t value) noexcept {
    if (x < 0 || x >= m_width || y < 0 || y >= m_height) return;
    m_data[static_cast<size_t>(y * m_width + x)] = value;
}

uint8_t Texture2D::samplePixel(int x, int y, TextureWrapMode wrapMode) const noexcept {
    if (m_width <= 0 || m_height <= 0) return 255;

    if (wrapMode == TextureWrapMode::Repeat) {
        x = (x % m_width + m_width) % m_width;
        y = (y % m_height + m_height) % m_height;
    } else {
        x = std::clamp(x, 0, m_width - 1);
        y = std::clamp(y, 0, m_height - 1);
    }

    return m_data[static_cast<size_t>(y * m_width + x)];
}

double Texture2D::sampleNormalized(double u, double v, TextureWrapMode wrapMode) const noexcept {
    if (m_width <= 0 || m_height <= 0) return 1.0;

    double px = u * static_cast<double>(m_width);
    double py = v * static_cast<double>(m_height);

    const int x0 = static_cast<int>(std::floor(px));
    const int y0 = static_cast<int>(std::floor(py));
    const int x1 = x0 + 1;
    const int y1 = y0 + 1;

    const double fx = px - std::floor(px);
    const double fy = py - std::floor(py);

    const double v00 = static_cast<double>(samplePixel(x0, y0, wrapMode)) / 255.0;
    const double v10 = static_cast<double>(samplePixel(x1, y0, wrapMode)) / 255.0;
    const double v01 = static_cast<double>(samplePixel(x0, y1, wrapMode)) / 255.0;
    const double v11 = static_cast<double>(samplePixel(x1, y1, wrapMode)) / 255.0;

    const double top = math::MathUtils::lerp(v00, v10, fx);
    const double bottom = math::MathUtils::lerp(v01, v11, fx);

    return math::MathUtils::lerp(top, bottom, fy);
}

} // namespace aladyn::engine::texture
