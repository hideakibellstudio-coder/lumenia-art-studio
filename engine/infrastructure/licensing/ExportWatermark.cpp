#include "ExportWatermark.hpp"

#include <algorithm>
#include <array>
#include <string_view>

namespace aladyn::engine::licensing {
namespace {

constexpr int kGlyphWidth = 5;
constexpr int kGlyphHeight = 7;
constexpr std::string_view kText = "LUMENIA FREE";

// 5x7 glyphs, one byte per row, bit 4 = leftmost column.
using Glyph = std::array<uint8_t, kGlyphHeight>;

Glyph glyphFor(char c) {
    switch (c) {
        case 'L': return {0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F};
        case 'U': return {0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E};
        case 'M': return {0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11};
        case 'E': return {0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F};
        case 'N': return {0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11};
        case 'I': return {0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E};
        case 'A': return {0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11};
        case 'F': return {0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10};
        case 'R': return {0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11};
        default: return {0, 0, 0, 0, 0, 0, 0};
    }
}

struct Canvas {
    uint8_t* pixels;
    int width;
    int height;
};

// Mixes `tone` into a square of `size` pixels; `weight` is out of 256.
void blendSquare(const Canvas& canvas, int x0, int y0, int size, uint8_t tone, int weight) {
    const int x1 = std::min(canvas.width, x0 + size);
    const int y1 = std::min(canvas.height, y0 + size);
    for (int y = std::max(0, y0); y < y1; ++y) {
        uint8_t* row = canvas.pixels + static_cast<size_t>(y) * static_cast<size_t>(canvas.width) * 4;
        for (int x = std::max(0, x0); x < x1; ++x) {
            uint8_t* p = row + static_cast<size_t>(x) * 4;
            for (int c = 0; c < 3; ++c) {
                p[c] = static_cast<uint8_t>((p[c] * (256 - weight) + tone * weight) >> 8);
            }
            p[3] = static_cast<uint8_t>(p[3] + (((255 - p[3]) * weight) >> 8));
        }
    }
}

void stampText(const Canvas& canvas, int originX, int originY, int module) {
    const int shadow = std::max(1, module / 3);
    for (size_t i = 0; i < kText.size(); ++i) {
        const Glyph glyph = glyphFor(kText[i]);
        const int glyphX = originX + static_cast<int>(i) * (kGlyphWidth + 1) * module;
        for (int row = 0; row < kGlyphHeight; ++row) {
            for (int col = 0; col < kGlyphWidth; ++col) {
                if (!(glyph[static_cast<size_t>(row)] & (0x10 >> col))) continue;
                const int x = glyphX + col * module;
                const int y = originY + row * module;
                blendSquare(canvas, x + shadow, y + shadow, module, 0, 72);
                blendSquare(canvas, x, y, module, 255, 104);
            }
        }
    }
}

} // namespace

void stampUnlicensedWatermark(uint8_t* rgba, int width, int height) {
    if (!rgba || width <= 0 || height <= 0) return;
    const Canvas canvas{rgba, width, height};
    const int module = std::max(1, std::min(width, height) / 240);
    const int textWidth = static_cast<int>(kText.size()) * (kGlyphWidth + 1) * module;
    const int stepX = textWidth + 16 * module;
    const int stepY = kGlyphHeight * module * 5;
    int row = 0;
    for (int y = stepY / 3; y < height; y += stepY, ++row) {
        const int offset = (row % 2) ? stepX / 2 : 0;
        for (int x = -offset; x < width; x += stepX) {
            stampText(canvas, x, y, module);
        }
    }
}

} // namespace aladyn::engine::licensing
