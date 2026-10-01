// Pins `blendPixel` (engine/core/document/blending/BlendEquations.hpp) pixel by pixel.
//
// The function was one 132-line branch with cyclomatic complexity 32; it is now a dispatcher over
// named paths. Splitting it must not move a single pixel, and the compositing golden only reaches
// the combinations its eight scenes happen to use. This harness hashes the output of 4096
// deterministic cases for every blend mode x linear/sRGB x 8-bit/deep colour (52 combinations,
// 212 992 pixels) and compares each hash with the one recorded from the implementation before the
// split. Header-only: it links no engine source.
//
//   blend_pixel_pins            checks the table, exit code 1 on any difference
//   blend_pixel_pins --print    prints the table (for a change of the maths made on purpose)
#include "engine/core/document/blending/BlendEquations.hpp"

#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {

using aladyn::engine::utils::ColorRGBA;
using aladyn::engine::document::blending::LayerBlendMode;
using aladyn::engine::document::blending::blendPixel;

constexpr int kModes = 13;
constexpr int kCasesPerCombination = 4096;
constexpr double kOpacities[] = {1.0, 0.5, 0.25, 0.999, 0.001, 0.73, 0.0};
constexpr uint8_t kEdges[] = {0, 1, 127, 128, 254, 255};

struct SplitMix64 {
    uint64_t state;
    uint64_t next() {
        uint64_t z = (state += 0x9E3779B97F4A7C15ULL);
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
};

ColorRGBA pick(SplitMix64& rng, bool edges) {
    const uint64_t bits = rng.next();
    if (edges) {
        return ColorRGBA{kEdges[bits % 6], kEdges[(bits >> 8) % 6], kEdges[(bits >> 16) % 6], kEdges[(bits >> 24) % 6]};
    }
    return ColorRGBA{static_cast<uint8_t>(bits), static_cast<uint8_t>(bits >> 8),
                     static_cast<uint8_t>(bits >> 16), static_cast<uint8_t>(bits >> 24)};
}

uint64_t hashCombination(int mode, bool linear, bool deep) {
    SplitMix64 rng{static_cast<uint64_t>(mode) * 4 + (linear ? 2 : 0) + (deep ? 1 : 0) + 1};
    uint64_t hash = 14695981039346656037ULL;  // FNV-1a
    for (int i = 0; i < kCasesPerCombination; ++i) {
        const ColorRGBA src = pick(rng, i % 3 == 0);
        const ColorRGBA dst = pick(rng, i % 5 == 0);
        const double opacity = kOpacities[rng.next() % 7];
        const ColorRGBA out = blendPixel(src, opacity, dst, static_cast<LayerBlendMode>(mode), linear, deep);
        for (const uint8_t byte : {out.r, out.g, out.b, out.a}) {
            hash = (hash ^ byte) * 1099511628211ULL;
        }
    }
    return hash;
}

// Recorded from the implementation before the split (index = mode * 4 + linear * 2 + deep).
constexpr uint64_t kExpected[kModes * 4] = {
    0x840a6068554f17b5ULL,
    0x37e55f9e4549ebafULL,
    0x3dc92b6e35ff4ebdULL,
    0xbfd3de3be4c5dd21ULL,
    0xa8def91025a6d26aULL,
    0xf4222954fc886464ULL,
    0x0ad8000e922f7a58ULL,
    0xf62b6238585233b2ULL,
    0x479f190d3aae80c3ULL,
    0x1857ca458f486a79ULL,
    0xa6ba0e16d76ffe91ULL,
    0x3c6f846bc6c0405aULL,
    0x8de21bc38273519eULL,
    0xb4580d68e2dd5963ULL,
    0x80a788b303c89cb5ULL,
    0xa546cdf0f6b3e57fULL,
    0xdc14812d4f03ff89ULL,
    0x98e4d6e83042e8aeULL,
    0xf371b3fbf2254dccULL,
    0xea8d45c39e5ba65fULL,
    0x2be3f29081aece39ULL,
    0x83900cb81739d44cULL,
    0x21d5a4e4af078fcfULL,
    0x484ccb82c4966ef2ULL,
    0x4161c8f28529ac77ULL,
    0x597eb63fef0884eeULL,
    0x7f363575d6c3383bULL,
    0x31eaa36d8baddc2aULL,
    0x6ef33bc7d44019d3ULL,
    0x5e1aab2e3effdc6dULL,
    0x5b6b075dcf3935b0ULL,
    0xafd84aef390730cdULL,
    0x3f1ca90ae3dc1923ULL,
    0x588a45841df004e5ULL,
    0x77b549d924d4002eULL,
    0x8e06aa1723279583ULL,
    0xb7f3bb6226977248ULL,
    0x35de57b5b0d894efULL,
    0x392d473b8ce62130ULL,
    0xedc8bb415a083fb1ULL,
    0x54085e22f31c7438ULL,
    0xdc85078046556ae4ULL,
    0xba5d00e1cf618132ULL,
    0x11e0c940b154ed73ULL,
    0x29862f8e6d707426ULL,
    0x8f47a459e9504b30ULL,
    0x823f003cd23e5003ULL,
    0xea68a57995e42858ULL,
    0x49f3da91d264249dULL,
    0xe6db147dfedd6777ULL,
    0xb5b3bebe29e98691ULL,
    0xd637768c20ea5dc7ULL
};

}  // namespace

int main(int argc, char** argv) {
    const bool print = argc > 1 && std::strcmp(argv[1], "--print") == 0;
    int different = 0;
    for (int mode = 0; mode < kModes; ++mode) {
        for (int flags = 0; flags < 4; ++flags) {
            const bool linear = (flags & 2) != 0;
            const bool deep = (flags & 1) != 0;
            const uint64_t got = hashCombination(mode, linear, deep);
            const int index = mode * 4 + flags;
            if (print) {
                std::printf("    0x%016llxULL,\n", static_cast<unsigned long long>(got));
            } else if (got != kExpected[index]) {
                std::printf("DIFFERENT mode=%d linear=%d deep=%d: got 0x%016llx, expected 0x%016llx\n", mode, linear, deep,
                            static_cast<unsigned long long>(got), static_cast<unsigned long long>(kExpected[index]));
                ++different;
            }
        }
    }
    if (print) return 0;
    if (different == 0) std::printf("blend pixel pins: %d combinations match\n", kModes * 4);
    return different == 0 ? 0 : 1;
}
