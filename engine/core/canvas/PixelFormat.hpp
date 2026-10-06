#ifndef ALADYN_ENGINE_PIXEL_FORMAT_HPP
#define ALADYN_ENGINE_PIXEL_FORMAT_HPP

// O formato de pixel de um documento: 8 bits por canal (o padrão, o que o motor sempre guardou) ou 16.
// É propriedade do documento: todas as camadas dele, os tiles, o histórico e o arquivo seguem o mesmo formato.
// O documento de 8 bits não muda um byte por causa do formato de 16 (S4 do plano do compositor).

#include "../../utils/ColorRGBA.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include <bit>
#include <cstddef>
#include <cstdint>

// Os canais de 16 bits ficam na memória e no arquivo .lmn na ordem da máquina; o motor só roda em little-endian.
static_assert(std::endian::native == std::endian::little, "16-bit pixels are stored in machine order (little-endian only)");

namespace aladyn::engine::canvas {

enum class PixelFormat : uint8_t {
    RGBA8 = 0,   // uint8_t  r, g, b, a: 4 bytes por pixel
    RGBA16 = 1,  // uint16_t r, g, b, a: 8 bytes por pixel
};

[[nodiscard]] constexpr size_t bytesPerPixel(PixelFormat format) noexcept {
    return format == PixelFormat::RGBA16 ? 8u : 4u;
}

// O formato que um byte lido de arquivo ou da ponte nomeia; false se não existe.
[[nodiscard]] constexpr bool isPixelFormatId(uint32_t id) noexcept { return id <= static_cast<uint32_t>(PixelFormat::RGBA16); }

[[nodiscard]] constexpr const char* pixelFormatName(PixelFormat format) noexcept {
    return format == PixelFormat::RGBA16 ? "RGBA16" : "RGBA8";
}

// 8 -> 16 bits por ×257 (0 -> 0, 255 -> 65535, e todo valor de 8 bits tem a sua imagem exata); 16 -> 8 pelo
// inteiro mais próximo. Os dois juntos são a identidade em 8 bits: um documento de 8 bits aberto em 16 e
// de volta não muda um nível.
[[nodiscard]] constexpr uint16_t widenChannel(uint8_t value) noexcept { return static_cast<uint16_t>(value * 257u); }
[[nodiscard]] constexpr uint8_t narrowChannel(uint16_t value) noexcept {
    return static_cast<uint8_t>((static_cast<uint32_t>(value) + 128u) / 257u);
}

[[nodiscard]] constexpr utils::ColorRGBA16 widen(utils::ColorRGBA c) noexcept {
    return {widenChannel(c.r), widenChannel(c.g), widenChannel(c.b), widenChannel(c.a)};
}
[[nodiscard]] constexpr utils::ColorRGBA narrow(utils::ColorRGBA16 c) noexcept {
    return {narrowChannel(c.r), narrowChannel(c.g), narrowChannel(c.b), narrowChannel(c.a)};
}

// O que o código genérico no pixel precisa saber do tipo (S5 e S6): o canal, o fundo de escala e o formato.
template <class Pixel>
struct PixelTraits;

template <>
struct PixelTraits<utils::ColorRGBA> {
    using Channel = uint8_t;
    static constexpr PixelFormat kFormat = PixelFormat::RGBA8;
    static constexpr uint32_t kMax = 255;
};

template <>
struct PixelTraits<utils::ColorRGBA16> {
    using Channel = uint16_t;
    static constexpr PixelFormat kFormat = PixelFormat::RGBA16;
    static constexpr uint32_t kMax = 65535;
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_PIXEL_FORMAT_HPP
