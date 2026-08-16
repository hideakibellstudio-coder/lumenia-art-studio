#ifndef ALADYN_ENGINE_TEXTURE2D_HPP
#define ALADYN_ENGINE_TEXTURE2D_HPP

#include <vector>
#include <cstdint>
#include <cstddef>

namespace aladyn::engine::texture {

enum class TextureWrapMode {
    Repeat,
    Clamp
};

class Texture2D {
public:
    Texture2D(int width, int height, uint8_t fillValue = 255);
    Texture2D(int width, int height, std::vector<uint8_t> data);

    [[nodiscard]] int getWidth() const noexcept { return m_width; }
    [[nodiscard]] int getHeight() const noexcept { return m_height; }
    [[nodiscard]] uint8_t* getData() noexcept { return m_data.data(); }
    [[nodiscard]] const uint8_t* getData() const noexcept { return m_data.data(); }

    [[nodiscard]] uint8_t samplePixel(int x, int y, TextureWrapMode wrapMode = TextureWrapMode::Repeat) const noexcept;
    [[nodiscard]] double sampleNormalized(double u, double v, TextureWrapMode wrapMode = TextureWrapMode::Repeat) const noexcept;

    [[nodiscard]] inline uint8_t samplePixelFast(int x, int y) const noexcept {
        if (m_width <= 0 || m_height <= 0) return 255;
        if ((m_width & (m_width - 1)) == 0 && (m_height & (m_height - 1)) == 0) {
            return m_data[static_cast<size_t>((y & (m_height - 1)) * m_width + (x & (m_width - 1)))];
        }
        x = (x % m_width + m_width) % m_width;
        y = (y % m_height + m_height) % m_height;
        return m_data[static_cast<size_t>(y * m_width + x)];
    }

    [[nodiscard]] inline uint8_t sampleNormalizedFastByte(double u, double v) const noexcept {
        if (m_width <= 0 || m_height <= 0) return 255;
        const double px = u * static_cast<double>(m_width);
        const double py = v * static_cast<double>(m_height);
        const int x0 = static_cast<int>(px);
        const int y0 = static_cast<int>(py);
        return samplePixelFast(x0, y0);
    }

    void setPixel(int x, int y, uint8_t value) noexcept;

private:
    int m_width{0};
    int m_height{0};
    std::vector<uint8_t> m_data;
};

} // namespace aladyn::engine::texture

#endif // ALADYN_ENGINE_TEXTURE2D_HPP
