// Checks the row blend kernel and the Deep Color tables against their definitions, pixel by pixel.
//
// `BlendKernel::blendRow` (engine/core/document/blending/BlendKernel.hpp) must give the same pixels as
//
//     for i: if (src[i].a != 0) dst[i] = blendPixel(src[i], opacity, dst[i], mode, linear, deep);
//
// at every SIMD level the CPU offers, and `DeepColorLut` must give the same bytes as the `pow` based
// `linearToSRGBPrecise` / `blendLinearNormalHighPrecision`. Nothing here is a tolerance: one different
// byte fails the run. The sections:
//
//   1. the Deep Color tables: toLinear, every step of the staircase and its neighbours (in ulps), tens of
//      millions of doubles (uniform, log-uniform, around each threshold), and the whole blend against
//      `blendLinearNormalHighPrecision`;
//   2. rows: every blend mode x linear/sRGB x 8-bit/deep x 7 opacities x 13 lengths x 7 alpha patterns
//      at each level, with guard pixels around the buffers (a write outside [0, count) fails);
//   3. a large Normal/linear buffer: scalar level == AVX2 level == the definition.
//
// Exit code 1 on any difference. A CPU without AVX2 skips the AVX2 level and says so.
#include "engine/core/color/DeepColorLut.hpp"
#include "engine/core/document/blending/BlendEquations.hpp"
#include "engine/core/document/blending/BlendKernel.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

namespace {

using aladyn::engine::utils::ColorRGBA;
using aladyn::engine::color::DeepColorLut;
using aladyn::engine::color::blendLinearNormalDeep;
using aladyn::engine::color::blendLinearNormalHighPrecision;
using aladyn::engine::color::deepColorLut;
using aladyn::engine::color::linearToSRGBPrecise;
using aladyn::engine::color::linearToSRGBPreciseFast;
using aladyn::engine::document::blending::BlendKernel;
using aladyn::engine::document::blending::BlendPlan;
using aladyn::engine::document::blending::BlendSimdLevel;
using aladyn::engine::document::blending::LayerBlendMode;
using aladyn::engine::document::blending::blendPixel;

struct SplitMix64 {
    uint64_t state;
    uint64_t next() {
        uint64_t z = (state += 0x9E3779B97F4A7C15ULL);
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
    double unit() { return static_cast<double>(next() >> 11) * (1.0 / 9007199254740992.0); }
};

int g_failures = 0;

bool equal(ColorRGBA a, ColorRGBA b) { return a.r == b.r && a.g == b.g && a.b == b.b && a.a == b.a; }

void report(const char* section, const char* detail, long long index) {
    ++g_failures;
    if (g_failures <= 12) std::printf("DIFFERENT [%s] %s (case %lld)\n", section, detail, index);
}

// ─── 1. Deep Color tables ────────────────────────────────────────────────────

double toLinearDefinition(int c) {
    const double s = static_cast<double>(c) / 255.0;
    return (s <= 0.04045) ? s / 12.92 : std::pow((s + 0.055) / 1.055, 2.4);
}

void checkToLinear(const DeepColorLut& lut) {
    for (int c = 0; c < 256; ++c) {
        const double definition = toLinearDefinition(c);
        if (std::memcmp(&lut.toLinear[c], &definition, sizeof(double)) != 0) {
            report("deep toLinear", "table differs from the expression", c);
        }
    }
    std::printf("deep lut: toLinear 256 values equal\n");
}

// threshold[k] is the smallest double whose image is >= k: the image of it is >= k, and of the double
// right below it is < k, for each of the 255 steps.
void checkThresholds(const DeepColorLut& lut) {
    for (unsigned k = 1; k <= 255; ++k) {
        const double at = lut.threshold[k];
        const double below = std::nextafter(at, 0.0);
        if (linearToSRGBPrecise(at) < k) report("deep threshold", "image at the threshold is below the step", k);
        if (linearToSRGBPrecise(below) >= k) report("deep threshold", "image just below the threshold reaches the step", k);
        if (k > 1 && !(lut.threshold[k] > lut.threshold[k - 1])) report("deep threshold", "not increasing", k);
    }
    std::printf("deep lut: 255 steps, each threshold and its predecessor double checked\n");
}

long long g_doublesChecked = 0;

void compareDouble(const DeepColorLut& lut, double x) {
    const uint8_t expected = linearToSRGBPrecise(x);
    const uint8_t got = linearToSRGBPreciseFast(lut, x);
    ++g_doublesChecked;
    if (expected != got) report("deep staircase", "fast != precise", g_doublesChecked);
}

void checkStaircase(const DeepColorLut& lut) {
    for (const double x : {0.0, -0.0, 1.0, 1.0000001, 5.0, -3.0, HUGE_VAL, -HUGE_VAL, 0.0031308,
                           std::nextafter(0.0031308, 1.0), std::nextafter(0.0031308, 0.0)}) {
        compareDouble(lut, x);
    }
    for (long k = 0; k <= 65536; ++k) compareDouble(lut, static_cast<double>(k) / 65536.0);
    // around every threshold: +-64 doubles
    for (unsigned step = 1; step <= 255; ++step) {
        double up = lut.threshold[step];
        double down = lut.threshold[step];
        compareDouble(lut, up);
        for (int i = 0; i < 64; ++i) {
            up = std::nextafter(up, 2.0);
            down = std::nextafter(down, 0.0);
            compareDouble(lut, up);
            compareDouble(lut, down);
        }
    }
    SplitMix64 rng{20261002};
    for (int i = 0; i < 12000000; ++i) compareDouble(lut, rng.unit());
    for (int i = 0; i < 12000000; ++i) compareDouble(lut, std::exp(-18.4 * rng.unit()));  // ~1e-8 .. 1
    std::printf("deep lut: %lld doubles give the same byte as the pow based definition\n", g_doublesChecked);
}

ColorRGBA randomPixel(SplitMix64& rng, bool edges) {
    static const uint8_t kEdges[] = {0, 1, 2, 127, 128, 254, 255};
    const uint64_t bits = rng.next();
    if (edges) {
        return ColorRGBA{kEdges[bits % 7], kEdges[(bits >> 8) % 7], kEdges[(bits >> 16) % 7], kEdges[(bits >> 24) % 7]};
    }
    return ColorRGBA{static_cast<uint8_t>(bits), static_cast<uint8_t>(bits >> 8), static_cast<uint8_t>(bits >> 16),
                     static_cast<uint8_t>(bits >> 24)};
}

void checkDeepBlend(const DeepColorLut& lut) {
    SplitMix64 rng{77};
    static const double kAlphas[] = {0.0, 1e-9, 0.001, 0.25, 0.5, 0.73, 0.999, 1.0, 1.5};
    long long count = 0;
    for (int i = 0; i < 6000000; ++i) {
        const ColorRGBA src = randomPixel(rng, i % 3 == 0);
        const ColorRGBA dst = randomPixel(rng, i % 5 == 0);
        const uint64_t pick = rng.next();
        const double alpha = (pick & 1) ? (static_cast<double>(src.a) / 255.0) * kAlphas[(pick >> 1) % 9]
                                         : kAlphas[(pick >> 1) % 9];
        ++count;
        if (!equal(blendLinearNormalHighPrecision(src, alpha, dst), blendLinearNormalDeep(lut, src, alpha, dst))) {
            report("deep blend", "table blend != definition", count);
        }
    }
    std::printf("deep lut: %lld blends equal blendLinearNormalHighPrecision\n", count);
}

// ─── 2. rows ─────────────────────────────────────────────────────────────────

constexpr int kModes = 13;
constexpr size_t kGuard = 3;  // guard pixels on each side; also keeps the row off a 32 byte boundary
constexpr double kOpacities[] = {1.0, 0.5, 0.25, 0.999, 0.001, 0.73, 0.0};
constexpr size_t kLengths[] = {0, 1, 2, 7, 8, 9, 15, 16, 17, 31, 64, 128, 1000};
constexpr int kPatterns = 7;
const ColorRGBA kGuardPixel{0xA5, 0x5A, 0x3C, 0xC3};

void fillPattern(int pattern, SplitMix64& rng, std::vector<ColorRGBA>& src, std::vector<ColorRGBA>& dst, size_t count) {
    for (size_t i = 0; i < count; ++i) {
        ColorRGBA s = randomPixel(rng, pattern == 4);
        ColorRGBA d = randomPixel(rng, pattern == 4);
        switch (pattern) {
            case 1: d.a = 255; break;                                          // opaque destination, any source
            case 2: d.a = 255; if ((i / 8) % 10 < 7) s.a = 0; break;           // sparse ink in runs
            case 3: d.a = 255; s.a = 255; break;                               // all covering
            case 4: break;                                                     // edge values everywhere
            case 5: if (rng.next() % 20 != 0) d.a = 255; break;                // a few translucent destinations
            case 6: s.a = 0; break;                                            // no ink at all
            default: break;                                                    // random everything
        }
        src[kGuard + i] = s;
        dst[kGuard + i] = d;
    }
}

struct RowStats {
    long long rows = 0;
    long long pixels = 0;
};

RowStats checkRows(const char* levelName) {
    RowStats stats;
    SplitMix64 rng{4242};
    std::vector<ColorRGBA> src(1000 + 2 * kGuard), dst(1000 + 2 * kGuard), expected, got;
    for (int mode = 0; mode < kModes; ++mode) {
        for (int flags = 0; flags < 4; ++flags) {
            const bool linear = (flags & 2) != 0;
            const bool deep = (flags & 1) != 0;
            for (const double opacity : kOpacities) {
                const BlendPlan plan = BlendKernel::plan(opacity, static_cast<LayerBlendMode>(mode), linear, deep);
                for (const size_t length : kLengths) {
                    for (int pattern = 0; pattern < kPatterns; ++pattern) {
                        std::fill(src.begin(), src.end(), kGuardPixel);
                        std::fill(dst.begin(), dst.end(), kGuardPixel);
                        fillPattern(pattern, rng, src, dst, length);
                        expected = dst;
                        got = dst;
                        for (size_t i = 0; i < length; ++i) {
                            const ColorRGBA s = src[kGuard + i];
                            if (s.a == 0) continue;
                            expected[kGuard + i] = blendPixel(s, opacity, dst[kGuard + i], static_cast<LayerBlendMode>(mode), linear, deep);
                        }
                        BlendKernel::blendRow(plan, src.data() + kGuard, got.data() + kGuard, length);
                        ++stats.rows;
                        stats.pixels += static_cast<long long>(length);
                        for (size_t i = 0; i < got.size(); ++i) {
                            if (!equal(expected[i], got[i])) {
                                char detail[160];
                                std::snprintf(detail, sizeof detail, "%s mode=%d linear=%d deep=%d opacity=%g length=%zu pattern=%d index=%zu",
                                              levelName, mode, linear, deep, opacity, length, pattern, i);
                                report("row", detail, stats.rows);
                                break;
                            }
                        }
                    }
                }
            }
        }
    }
    return stats;
}

// ─── 3. a large Normal/linear buffer ─────────────────────────────────────────

std::vector<ColorRGBA> runLarge(BlendSimdLevel level, const std::vector<ColorRGBA>& src, const std::vector<ColorRGBA>& dst,
                                double opacity) {
    BlendKernel::forceLevel(level);
    const BlendPlan plan = BlendKernel::plan(opacity, LayerBlendMode::Normal, true, false);
    std::vector<ColorRGBA> out = dst;
    // rows of an odd length, the way tiles cut them
    const size_t width = 997;
    for (size_t at = 0; at < src.size(); at += width) {
        const size_t count = std::min(width, src.size() - at);
        BlendKernel::blendRow(plan, src.data() + at, out.data() + at, count);
    }
    return out;
}

void checkLarge(bool haveAvx2) {
    constexpr size_t kPixels = 4u * 1024 * 1024;
    SplitMix64 rng{909};
    std::vector<ColorRGBA> src(kPixels), dst(kPixels);
    for (size_t i = 0; i < kPixels; ++i) {
        src[i] = randomPixel(rng, i % 11 == 0);
        dst[i] = randomPixel(rng, i % 13 == 0);
        if (rng.next() % 16 != 0) dst[i].a = 255;
    }
    for (const double opacity : {1.0, 0.37}) {
        std::vector<ColorRGBA> definition = dst;
        for (size_t i = 0; i < kPixels; ++i) {
            if (src[i].a != 0) definition[i] = blendPixel(src[i], opacity, dst[i], LayerBlendMode::Normal, true, false);
        }
        const std::vector<ColorRGBA> scalar = runLarge(BlendSimdLevel::Scalar, src, dst, opacity);
        const std::vector<ColorRGBA> avx2 = haveAvx2 ? runLarge(BlendSimdLevel::Avx2, src, dst, opacity) : scalar;
        for (size_t i = 0; i < kPixels; ++i) {
            if (!equal(definition[i], scalar[i])) { report("large", "scalar level != definition", static_cast<long long>(i)); break; }
            if (!equal(definition[i], avx2[i])) { report("large", "avx2 level != definition", static_cast<long long>(i)); break; }
        }
    }
    std::printf("large buffer: %zu pixels x 2 opacities, scalar level == %s == definition\n", kPixels,
                haveAvx2 ? "avx2 level" : "(avx2 not available)");
}

}  // namespace

int main() {
    const DeepColorLut& lut = deepColorLut();
    checkToLinear(lut);
    checkThresholds(lut);
    checkStaircase(lut);
    checkDeepBlend(lut);

    const bool haveAvx2 = BlendKernel::bestAvailableLevel() == BlendSimdLevel::Avx2;
    BlendKernel::forceLevel(BlendSimdLevel::Scalar);
    const RowStats scalar = checkRows("scalar");
    std::printf("rows scalar: %lld rows, %lld pixels equal the definition\n", scalar.rows, scalar.pixels);
    if (haveAvx2) {
        BlendKernel::forceLevel(BlendSimdLevel::Avx2);
        const RowStats avx2 = checkRows("avx2");
        std::printf("rows avx2: %lld rows, %lld pixels equal the definition\n", avx2.rows, avx2.pixels);
    } else {
        std::printf("rows avx2: skipped (this CPU has no AVX2)\n");
    }
    checkLarge(haveAvx2);

    if (g_failures != 0) {
        std::printf("blend kernel checks: %d DIFFERENCES\n", g_failures);
        return 1;
    }
    std::printf("blend kernel checks: all equal\n");
    return 0;
}
