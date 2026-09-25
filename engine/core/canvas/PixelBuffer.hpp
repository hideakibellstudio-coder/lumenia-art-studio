#ifndef ALADYN_ENGINE_PIXEL_BUFFER_HPP
#define ALADYN_ENGINE_PIXEL_BUFFER_HPP

#include "../../utils/ColorRGBA.hpp"
#include <vector>
#include <cstdint>
#include <cstring>
#include <algorithm>

namespace aladyn::engine::canvas {

class PixelBuffer {
public:
    PixelBuffer(int width, int height, utils::ColorRGBA fillColor = {255, 255, 255, 255})
        : m_width(width), m_height(height), m_data(static_cast<size_t>(width * height * 4)) {
        fill(fillColor);
    }

    void fill(utils::ColorRGBA color) {
        uint8_t* ptr = m_data.data();
        const size_t totalPixels = static_cast<size_t>(m_width * m_height);
        for (size_t i = 0; i < totalPixels; ++i) {
            ptr[i * 4 + 0] = color.r;
            ptr[i * 4 + 1] = color.g;
            ptr[i * 4 + 2] = color.b;
            ptr[i * 4 + 3] = color.a;
        }
    }

    void clearTransparent() {
        std::memset(m_data.data(), 0, m_data.size());
    }

    void resize(int width, int height, utils::ColorRGBA fillColor = {0, 0, 0, 0}) {
        m_width = width;
        m_height = height;
        m_data.assign(static_cast<size_t>(width * height * 4), 0);
        if (fillColor.r != 0 || fillColor.g != 0 || fillColor.b != 0 || fillColor.a != 0) {
            fill(fillColor);
        }
    }

    [[nodiscard]] int getWidth() const noexcept { return m_width; }
    [[nodiscard]] int getHeight() const noexcept { return m_height; }
    [[nodiscard]] uint8_t* getData() noexcept { return m_data.data(); }
    [[nodiscard]] const uint8_t* getData() const noexcept { return m_data.data(); }
    [[nodiscard]] size_t getSizeInBytes() const noexcept { return m_data.size(); }

    inline void setPixel(int x, int y, utils::ColorRGBA color) noexcept {
        if (x < 0 || x >= m_width || y < 0 || y >= m_height) return;
        const size_t idx = static_cast<size_t>((y * m_width + x) * 4);
        m_data[idx + 0] = color.r;
        m_data[idx + 1] = color.g;
        m_data[idx + 2] = color.b;
        m_data[idx + 3] = color.a;
    }

    inline utils::ColorRGBA getPixel(int x, int y) const noexcept {
        if (x < 0 || x >= m_width || y < 0 || y >= m_height) return {0, 0, 0, 0};
        const size_t idx = static_cast<size_t>((y * m_width + x) * 4);
        return {m_data[idx + 0], m_data[idx + 1], m_data[idx + 2], m_data[idx + 3]};
    }

private:
    int m_width{0};
    int m_height{0};
    std::vector<uint8_t> m_data;
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_PIXEL_BUFFER_HPP
