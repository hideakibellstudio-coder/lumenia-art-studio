#ifndef ALADYN_ENGINE_PIXEL_BUFFER_HPP
#define ALADYN_ENGINE_PIXEL_BUFFER_HPP

#include "PixelFormat.hpp"
#include "../../utils/ColorRGBA.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include <cassert>
#include <vector>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include <memory>
#include <new>
#include <type_traits>
#include <utility>

namespace aladyn::engine::canvas {

namespace detail {

// Alocador que não zera na construção. O PixelBuffer escreve cada byte logo depois (`fill`), então o
// zero do `std::vector` era uma primeira passada inteira sobre a memória: 1 GiB num canvas de 16384².
template <class T>
struct DefaultInitAllocator : std::allocator<T> {
    template <class U>
    struct rebind { using other = DefaultInitAllocator<U>; };

    using std::allocator<T>::allocator;

    template <class U>
    void construct(U* ptr) noexcept(std::is_nothrow_default_constructible_v<U>) {
        ::new (static_cast<void*>(ptr)) U;
    }
    template <class U, class... Args>
    void construct(U* ptr, Args&&... args) {
        ::new (static_cast<void*>(ptr)) U(std::forward<Args>(args)...);
    }
};

} // namespace detail

// Pixels em linhas, `getFormat()` bytes por pixel: 8 bits por canal (o padrão do motor, 4 bytes) ou 16 (8 bytes,
// canais em uint16 na ordem da máquina; o motor só roda em máquinas little-endian). `getData()` é sempre a memória
// crua; quem sabe o formato lê pelos canais com `pixels<ColorRGBA>()` ou `pixels<ColorRGBA16>()`.
class PixelBuffer {
public:
    PixelBuffer(int width, int height, utils::ColorRGBA fillColor = {255, 255, 255, 255})
        : PixelBuffer(width, height, PixelFormat::RGBA8, fillColor) {}

    // `fillColor` é uma cor de 8 bits; num buffer de 16 bits ela entra alargada (×257).
    PixelBuffer(int width, int height, PixelFormat format, utils::ColorRGBA fillColor)
        : m_width(width), m_height(height), m_format(format), m_data(byteCount(width, height, format)) {
        fill(fillColor);
    }

    [[nodiscard]] PixelFormat getFormat() const noexcept { return m_format; }
    [[nodiscard]] size_t getBytesPerPixel() const noexcept { return bytesPerPixel(m_format); }

    void fill(utils::ColorRGBA color) noexcept {
        if (m_format == PixelFormat::RGBA16) {
            fill(widen(color));
            return;
        }
        const uint8_t pixel[4] = {color.r, color.g, color.b, color.a};
        fillWithPixel(pixel, 4);
    }

    void fill(utils::ColorRGBA16 color) noexcept {
        if (m_format == PixelFormat::RGBA8) {
            fill(narrow(color));
            return;
        }
        const uint16_t channels[4] = {color.r, color.g, color.b, color.a};
        uint8_t pixel[8];
        std::memcpy(pixel, channels, sizeof(pixel));
        fillWithPixel(pixel, 8);
    }

    void clearTransparent() {
        std::memset(m_data.data(), 0, m_data.size());
    }

    void resize(int width, int height, utils::ColorRGBA fillColor = {0, 0, 0, 0}) {
        m_width = width;
        m_height = height;
        m_data.clear();
        m_data.resize(byteCount(width, height, m_format));
        fill(fillColor);
    }

    // Muda o formato do buffer, com o mesmo tamanho em pixels; o conteúdo fica indefinido (quem chama escreve em
    // seguida). É como um buffer de leitura de tile (`Tile::view`) se ajusta ao formato do tile que vai receber.
    void reformat(PixelFormat format) {
        if (format == m_format) return;
        m_format = format;
        m_data.clear();
        m_data.resize(byteCount(m_width, m_height, format));
    }

    // Devolve a memória ao sistema e deixa o buffer 0x0 (o buffer de exibição só existe com perfil de cor).
    void release() noexcept {
        std::vector<uint8_t, detail::DefaultInitAllocator<uint8_t>>().swap(m_data);
        m_width = 0;
        m_height = 0;
    }

    [[nodiscard]] int getWidth() const noexcept { return m_width; }
    [[nodiscard]] int getHeight() const noexcept { return m_height; }
    [[nodiscard]] uint8_t* getData() noexcept { return m_data.data(); }
    [[nodiscard]] const uint8_t* getData() const noexcept { return m_data.data(); }
    [[nodiscard]] size_t getSizeInBytes() const noexcept { return m_data.size(); }

    // Os pixels como `Pixel` (ColorRGBA ou ColorRGBA16); o tipo tem de ser o do formato do buffer.
    template <class Pixel>
    [[nodiscard]] Pixel* pixels() noexcept {
        assert(PixelTraits<Pixel>::kFormat == m_format);
        return reinterpret_cast<Pixel*>(m_data.data());
    }
    template <class Pixel>
    [[nodiscard]] const Pixel* pixels() const noexcept {
        assert(PixelTraits<Pixel>::kFormat == m_format);
        return reinterpret_cast<const Pixel*>(m_data.data());
    }

    // A visão de 8 bits de um pixel: num buffer de 16 bits `setPixel` alarga e `getPixel` estreita ao inteiro mais
    // próximo. Quem precisa dos 16 bits usa `setPixel16`/`getPixel16`.
    inline void setPixel(int x, int y, utils::ColorRGBA color) noexcept {
        if (x < 0 || x >= m_width || y < 0 || y >= m_height) return;
        if (m_format == PixelFormat::RGBA16) {
            pixels<utils::ColorRGBA16>()[static_cast<size_t>(y) * m_width + x] = widen(color);
            return;
        }
        const size_t idx = static_cast<size_t>((y * m_width + x) * 4);
        m_data[idx + 0] = color.r;
        m_data[idx + 1] = color.g;
        m_data[idx + 2] = color.b;
        m_data[idx + 3] = color.a;
    }

    inline utils::ColorRGBA getPixel(int x, int y) const noexcept {
        if (x < 0 || x >= m_width || y < 0 || y >= m_height) return {0, 0, 0, 0};
        if (m_format == PixelFormat::RGBA16) return narrow(pixels<utils::ColorRGBA16>()[static_cast<size_t>(y) * m_width + x]);
        const size_t idx = static_cast<size_t>((y * m_width + x) * 4);
        return {m_data[idx + 0], m_data[idx + 1], m_data[idx + 2], m_data[idx + 3]};
    }

    inline void setPixel16(int x, int y, utils::ColorRGBA16 color) noexcept {
        if (x < 0 || x >= m_width || y < 0 || y >= m_height) return;
        if (m_format == PixelFormat::RGBA8) {
            setPixel(x, y, narrow(color));
            return;
        }
        pixels<utils::ColorRGBA16>()[static_cast<size_t>(y) * m_width + x] = color;
    }

    inline utils::ColorRGBA16 getPixel16(int x, int y) const noexcept {
        if (x < 0 || x >= m_width || y < 0 || y >= m_height) return {0, 0, 0, 0};
        if (m_format == PixelFormat::RGBA8) return widen(getPixel(x, y));
        return pixels<utils::ColorRGBA16>()[static_cast<size_t>(y) * m_width + x];
    }

private:
    // Um pixel escrito e depois copiado para o resto, em blocos que dobram: velocidade de memcpy em vez de
    // um laço de um pixel por vez. Pixel com todos os bytes iguais (transparente, branco, cinza alargado) é um memset.
    void fillWithPixel(const uint8_t* pixel, size_t pixelBytes) noexcept {
        const size_t total = m_data.size();
        if (total == 0) return;
        uint8_t* ptr = m_data.data();
        bool uniform = true;
        for (size_t i = 1; i < pixelBytes; ++i) uniform = uniform && pixel[i] == pixel[0];
        if (uniform) {
            std::memset(ptr, pixel[0], total);
            return;
        }
        std::memcpy(ptr, pixel, pixelBytes);
        for (size_t done = pixelBytes; done < total;) {
            const size_t chunk = std::min(done, total - done);
            std::memcpy(ptr + done, ptr, chunk);
            done += chunk;
        }
    }

    // Widen before multiplying: `width * height * 4` in int overflows past ~23170 px per side.
    static size_t byteCount(int width, int height, PixelFormat format) noexcept {
        return static_cast<size_t>(width) * static_cast<size_t>(height) * bytesPerPixel(format);
    }

    int m_width{0};
    int m_height{0};
    PixelFormat m_format{PixelFormat::RGBA8};
    std::vector<uint8_t, detail::DefaultInitAllocator<uint8_t>> m_data;
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_PIXEL_BUFFER_HPP
