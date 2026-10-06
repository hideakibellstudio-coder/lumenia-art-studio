// Checks the 16-bit blend (S5): the tables, the row kernel against the definition, and the definition against the
// 8-bit blend.
//
// `blendPixel16` (engine/core/document/blending/BlendEquations16.hpp) is the DEFINITION of a 16-bit pixel: double
// arithmetic, rounded to the nearest level. `BlendKernel16::blendRow` is what runs, and for Normal (the path of nearly
// every layer) it is NOT bit-exact: it uses float tables. So this harness MEASURES how far it is, and fails only when
// the measurement leaves the bound the design promises (at most 1 level of 16 bits, alpha exact, the shortcuts exact).
//
//   1. tables: `toLinear` against the double curve, `encode` (interpolated) against the double curve, the round trip
//      encode(toLinear(v)) == v for all 65536 values, the saturation and the NaN;
//   2. Normal rows (linear and sRGB) against the definition on millions of pixels over every alpha pattern: maximum
//      difference, fraction of channels that differ, alpha exact, and the shortcuts (alpha 1 over anything, anything
//      under alpha 0) exact;
//      (measured on the scalar rows; the AVX2 rows are then checked to give the very same bytes, section 2b);
//   3. every other mode and Erase: rows equal the definition exactly, with guard pixels around the buffers;
//   4. the definition against the 8-bit Deep Color blend on 8-bit content widened by x257 and narrowed back: the
//      16-bit document must give the same picture as the 8-bit one up to the 8-bit rounding.
//
// Exit code 1 on any failure. The numbers are printed so the documentation can quote what was measured.
#include "engine/core/canvas/PixelFormat.hpp"
#include "engine/core/color/DeepColorLut.hpp"
#include "engine/core/color/LinearColorSpace16.hpp"
#include "engine/core/document/blending/BlendEquations.hpp"
#include "engine/core/document/blending/BlendEquations16.hpp"
#include "engine/core/document/blending/BlendKernel.hpp"
#include "engine/core/document/blending/BlendKernel16.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <limits>
#include <vector>

namespace {

using aladyn::engine::utils::ColorRGBA;
using aladyn::engine::utils::ColorRGBA16;
using aladyn::engine::canvas::narrow;
using aladyn::engine::canvas::widen;
using aladyn::engine::color::Srgb16Tables;
using aladyn::engine::color::linearToSrgb16;
using aladyn::engine::color::linearToSrgb16Reference;
using aladyn::engine::color::linearToSrgbReference;
using aladyn::engine::color::srgb16Tables;
using aladyn::engine::color::srgbToLinearReference;
using aladyn::engine::document::blending::BlendKernel;
using aladyn::engine::document::blending::BlendKernel16;
using aladyn::engine::document::blending::BlendSimdLevel;
using aladyn::engine::document::blending::BlendPlan16;
using aladyn::engine::document::blending::LayerBlendMode;
using aladyn::engine::document::blending::blendPixel;
using aladyn::engine::document::blending::blendPixel16;

struct SplitMix64 {
    uint64_t state;
    uint64_t next() {
        uint64_t z = (state += 0x9E3779B97F4A7C15ULL);
        z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
        z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
        return z ^ (z >> 31);
    }
    double unit() { return static_cast<double>(next() >> 11) * (1.0 / 9007199254740992.0); }
    uint16_t channel() { return static_cast<uint16_t>(next()); }
};

int g_failures = 0;

void fail(const char* section, const char* detail, long long index) {
    ++g_failures;
    if (g_failures <= 12) std::printf("FAIL [%s] %s (case %lld)\n", section, detail, index);
}

bool same(ColorRGBA16 a, ColorRGBA16 b) { return a.r == b.r && a.g == b.g && a.b == b.b && a.a == b.a; }

int distance(uint16_t a, uint16_t b) { return a > b ? a - b : b - a; }

// ─── 1. tables ───────────────────────────────────────────────────────────────

void checkTables() {
    const Srgb16Tables& tables = srgb16Tables();
    double worstLinear = 0.0;
    for (int v = 0; v < 65536; ++v) {
        const double definition = srgbToLinearReference(static_cast<double>(v) / 65535.0);
        worstLinear = std::max(worstLinear, std::abs(static_cast<double>(tables.toLinear[v]) - definition));
    }
    // The table is float: one ulp of a value near 1 is 6e-8, which is 0.004 of a 16-bit step in sRGB at the dark end
    // times the slope (12.92) of the curve; the bound is far from tight on purpose.
    if (worstLinear > 1e-7) fail("tables", "toLinear is more than 1e-7 away from the curve", 0);

    // The encode table in units of 16 bits, between table points and around the junction at 0.0031308.
    SplitMix64 rng{16};
    double worstEncode = 0.0, worstAboveToe = 0.0;
    long long beyondHalf = 0;
    const auto probe = [&](double linear) {
        const double exact = linearToSrgbReference(linear) * 65535.0;
        const float x = static_cast<float>(linear);
        const Srgb16Tables& t = tables;
        const float clamped = x > 1.0f ? 1.0f : (x >= 0.0f ? x : 0.0f);
        const float position = clamped * static_cast<float>(Srgb16Tables::kEncodeBuckets);
        const int bucket = static_cast<int>(position);
        const double value = t.encode[bucket] + (static_cast<double>(t.encode[bucket + 1]) - t.encode[bucket]) * (position - bucket);
        const double error = std::abs(value - exact);
        worstEncode = std::max(worstEncode, error);
        if (linear > 0.05) worstAboveToe = std::max(worstAboveToe, error);
        if (error > 0.5) ++beyondHalf;
    };
    for (int i = 0; i < 4000000; ++i) probe(rng.unit());
    for (int i = 0; i < 4000000; ++i) probe(std::pow(10.0, -6.0 * rng.unit()));
    for (int i = 0; i < 1000000; ++i) probe(0.0031308 + (rng.unit() - 0.5) * 0.002);
    probe(0.0);
    probe(1.0);
    // The worst error is in the bucket that holds the junction at 0.0031308, where the curve changes slope (12.92 below,
    // about 12.7 above) and the chord between the two table points cuts the corner: 0.2 of a step. Above the toe it is
    // far smaller (0.003 above 0.05).
    if (worstEncode > 0.25) fail("tables", "interpolated encode is more than 0.25 of a step away from the curve", 0);
    if (worstAboveToe > 0.01) fail("tables", "interpolated encode is more than 0.01 of a step away above 0.05", 0);
    if (beyondHalf != 0) fail("tables", "interpolated encode is more than half a step away", beyondHalf);

    long long roundTripDiffers = 0;
    int roundTripWorst = 0;
    for (int v = 0; v < 65536; ++v) {
        const int back = linearToSrgb16(tables, tables.toLinear[v]);
        if (back != v) ++roundTripDiffers;
        roundTripWorst = std::max(roundTripWorst, std::abs(back - v));
    }
    if (roundTripWorst > 1) fail("tables", "encode(toLinear(v)) is more than 1 level from v", roundTripWorst);

    if (linearToSrgb16(tables, 1.0f) != 65535 || linearToSrgb16(tables, 7.5f) != 65535) fail("tables", "saturation at 1", 0);
    if (linearToSrgb16(tables, 0.0f) != 0 || linearToSrgb16(tables, -3.0f) != 0) fail("tables", "saturation at 0", 0);
    if (linearToSrgb16(tables, std::numeric_limits<float>::quiet_NaN()) != 0) fail("tables", "NaN is not 0", 0);
    if (linearToSrgb16(tables, std::numeric_limits<float>::infinity()) != 65535) fail("tables", "infinity is not 65535", 0);
    std::printf("tables: toLinear max error %.3g, interpolated encode max error %.4f step (%.5f above 0.05), %lld beyond half, round trip differs on %lld of 65536 (worst %d)\n",
                worstLinear, worstEncode, worstAboveToe, beyondHalf, roundTripDiffers, roundTripWorst);
}

// ─── 2. Normal rows against the definition ───────────────────────────────────

enum AlphaPattern { kRandom, kOpaque, kTransparent, kMixed };

ColorRGBA16 randomPixel(SplitMix64& rng, int pattern) {
    ColorRGBA16 p{rng.channel(), rng.channel(), rng.channel(), rng.channel()};
    switch (pattern) {
        case kOpaque: p.a = 65535; break;
        case kTransparent: p.a = 0; break;
        case kMixed: {
            const uint64_t pick = rng.next() % 6;
            p.a = pick == 0 ? 0 : (pick == 1 ? 65535 : (pick == 2 ? static_cast<uint16_t>(1 + rng.next() % 4) : (pick == 3 ? static_cast<uint16_t>(65535 - rng.next() % 4) : p.a)));
            break;
        }
        default: break;
    }
    return p;
}

struct Spread {
    long long channels{0};
    long long differing{0};
    int worst{0};
    long long alphaDiffers{0};
    long long shortcutDiffers{0};
    long long pixels{0};
};

void measureNormal(bool linear, Spread& spread) {
    SplitMix64 rng{linear ? 101ULL : 202ULL};
    constexpr size_t kRow = 4096;
    std::vector<ColorRGBA16> src(kRow), dst(kRow), expected(kRow);
    const double opacities[] = {1.0, 0.999, 0.75, 0.5, 0.37, 0.05, 1e-4, 0.0};
    for (int round = 0; round < 280; ++round) {
        const double opacity = opacities[round % 8];
        const int srcPattern = (round / 8) % 4;
        const int dstPattern = (round / 32) % 4;
        for (size_t i = 0; i < kRow; ++i) {
            src[i] = randomPixel(rng, srcPattern);
            dst[i] = randomPixel(rng, dstPattern);
        }
        for (size_t i = 0; i < kRow; ++i) expected[i] = src[i].a == 0 ? dst[i] : blendPixel16(src[i], opacity, dst[i], LayerBlendMode::Normal, linear);
        const std::vector<ColorRGBA16> before = dst;
        const BlendPlan16 plan = BlendKernel16::plan(opacity, LayerBlendMode::Normal, linear);
        BlendKernel16::blendRow(plan, src.data(), dst.data(), kRow);
        for (size_t i = 0; i < kRow; ++i) {
            ++spread.pixels;
            const int dr = distance(dst[i].r, expected[i].r), dg = distance(dst[i].g, expected[i].g), db = distance(dst[i].b, expected[i].b);
            spread.channels += 3;
            spread.differing += (dr != 0) + (dg != 0) + (db != 0);
            spread.worst = std::max({spread.worst, dr, dg, db});
            if (dst[i].a != expected[i].a) ++spread.alphaDiffers;
            const bool shortcut = src[i].a == 0 || before[i].a == 0 || aladyn::engine::document::blending::detail16::effectiveAlpha(src[i].a, opacity) >= 1.0;
            if (shortcut && !same(dst[i], expected[i])) ++spread.shortcutDiffers;
        }
    }
}

void checkNormalRows() {
    for (const bool linear : {true, false}) {
        Spread spread;
        measureNormal(linear, spread);
        if (spread.worst > 1) fail("normal rows", linear ? "linear: more than 1 level from the definition" : "sRGB: more than 1 level from the definition", spread.worst);
        if (spread.alphaDiffers != 0) fail("normal rows", "alpha is not exact", spread.alphaDiffers);
        if (spread.shortcutDiffers != 0) fail("normal rows", "a shortcut (alpha 1, destination alpha 0, source alpha 0) is not exact", spread.shortcutDiffers);
        std::printf("normal rows (%s): %lld pixels, max difference %d level, %.4f%% of channels differ, alpha differs on %lld, shortcuts differ on %lld\n",
                    linear ? "linear" : "sRGB", spread.pixels, spread.worst, 100.0 * static_cast<double>(spread.differing) / static_cast<double>(spread.channels),
                    spread.alphaDiffers, spread.shortcutDiffers);
    }
}

// ─── 2b. the AVX2 rows ───────────────────────────────────────────────────────

// The AVX2 loop of Normal in linear gamma does the same operations as the scalar one, in the same order and type, so its
// bytes must be the same, not merely close. Every length 0..40 (tails of 0..7 pixels after groups of eight), eight
// opacities (and one below the AVX2 threshold, which stays scalar), destinations mostly opaque (the vector path) and
// sometimes translucent or empty (the groups it hands to the scalar row), with guard pixels around the buffers.
void checkAvx2Rows() {
    if (!BlendKernel::forceLevel(BlendSimdLevel::Avx2)) {
        std::printf("avx2 rows: this CPU has no AVX2, only the scalar rows exist\n");
        return;
    }
    SplitMix64 rng{303};
    const double opacities[] = {1.0, 0.999, 0.75, 0.5, 0.37, 0.05, 1e-4, 1e-13, 0.0};
    const ColorRGBA16 guard{0x1234, 0x5678, 0x9ABC, 0xDEF0};
    constexpr size_t kGuard = 8;
    long long pixels = 0, differing = 0, guardsHit = 0;
    for (int round = 0; round < 4000; ++round) {
        const size_t count = static_cast<size_t>(round % 41);
        const double opacity = opacities[round % 9];
        const int dstPattern = round % 11 == 0 ? kTransparent : (round % 7 == 0 ? kMixed : kOpaque);
        std::vector<ColorRGBA16> src(count), scalar(count + 2 * kGuard, guard), vector(count + 2 * kGuard, guard);
        for (size_t i = 0; i < count; ++i) {
            src[i] = randomPixel(rng, round % 4);
            scalar[kGuard + i] = vector[kGuard + i] = randomPixel(rng, dstPattern);
        }
        BlendKernel::forceLevel(BlendSimdLevel::Scalar);
        BlendKernel16::blendRow(BlendKernel16::plan(opacity, LayerBlendMode::Normal, true), src.data(), scalar.data() + kGuard, count);
        BlendKernel::forceLevel(BlendSimdLevel::Avx2);
        BlendKernel16::blendRow(BlendKernel16::plan(opacity, LayerBlendMode::Normal, true), src.data(), vector.data() + kGuard, count);
        for (size_t i = 0; i < scalar.size(); ++i) {
            const bool inside = i >= kGuard && i < kGuard + count;
            if (inside) { ++pixels; differing += !same(scalar[i], vector[i]); }
            else guardsHit += !same(vector[i], guard);
        }
    }
    if (differing != 0) fail("avx2 rows", "a pixel differs from the scalar row", differing);
    if (guardsHit != 0) fail("avx2 rows", "a guard pixel was written", guardsHit);
    std::printf("avx2 rows: %lld pixels over every length 0..40 and 9 opacities, identical to the scalar rows, guards untouched\n", pixels);
}

// ─── 3. the other modes ──────────────────────────────────────────────────────

void checkOtherModes() {
    constexpr int kModes = 13;
    constexpr size_t kGuard = 4;
    const double opacities[] = {1.0, 0.8, 0.31, 0.0};
    const size_t lengths[] = {0, 1, 2, 3, 7, 8, 9, 31, 64, 129};
    SplitMix64 rng{303};
    long long rows = 0, pixels = 0;
    for (int mode = 0; mode < kModes; ++mode) {
        if (mode == static_cast<int>(LayerBlendMode::Normal)) continue;
        for (const bool linear : {true, false}) {
            for (const double opacity : opacities) {
                const BlendPlan16 plan = BlendKernel16::plan(opacity, static_cast<LayerBlendMode>(mode), linear);
                for (const size_t length : lengths) {
                    for (int pattern = 0; pattern < 4; ++pattern) {
                        std::vector<ColorRGBA16> src(length + 2 * kGuard), dst(length + 2 * kGuard), expected;
                        for (auto& p : src) p = randomPixel(rng, pattern);
                        for (auto& p : dst) p = randomPixel(rng, (pattern + 1) % 4);
                        expected = dst;
                        for (size_t i = 0; i < length; ++i) {
                            if (src[kGuard + i].a != 0) expected[kGuard + i] = blendPixel16(src[kGuard + i], opacity, dst[kGuard + i], static_cast<LayerBlendMode>(mode), linear);
                        }
                        BlendKernel16::blendRow(plan, src.data() + kGuard, dst.data() + kGuard, length);
                        ++rows;
                        pixels += static_cast<long long>(length);
                        for (size_t i = 0; i < dst.size(); ++i) {
                            if (!same(dst[i], expected[i])) {
                                char detail[128];
                                std::snprintf(detail, sizeof detail, "mode=%d linear=%d opacity=%g length=%zu pattern=%d index=%zu", mode, linear, opacity, length, pattern, i);
                                fail("other modes", detail, static_cast<long long>(i));
                                break;
                            }
                        }
                    }
                }
            }
        }
    }
    std::printf("other modes: %lld rows (%lld pixels) of 12 modes x 2 gammas x 4 opacities equal the definition, guards untouched\n", rows, pixels);
}

// ─── 4. the definition against 8 bits ────────────────────────────────────────

void checkAgainstEightBits() {
    SplitMix64 rng{404};
    struct Row { const char* name; LayerBlendMode mode; bool linear; };
    const Row rows[] = {
        {"Normal linear", LayerBlendMode::Normal, true},        {"Normal sRGB", LayerBlendMode::Normal, false},
        {"Multiply", LayerBlendMode::Multiply, true},           {"Screen", LayerBlendMode::Screen, true},
        {"Overlay", LayerBlendMode::Overlay, true},             {"Darken", LayerBlendMode::Darken, true},
        {"Lighten", LayerBlendMode::Lighten, true},             {"Erase", LayerBlendMode::Erase, true},
        {"ColorDodge", LayerBlendMode::ColorDodge, true},       {"ColorBurn", LayerBlendMode::ColorBurn, true},
        {"Difference", LayerBlendMode::Difference, true},       {"Exclusion", LayerBlendMode::Exclusion, true},
        {"Add", LayerBlendMode::Add, true},
    };
    for (const Row& row : rows) {
        long long channels = 0, differing = 0;
        int worst = 0;
        for (int i = 0; i < 400000; ++i) {
            const ColorRGBA s{static_cast<uint8_t>(rng.next()), static_cast<uint8_t>(rng.next()), static_cast<uint8_t>(rng.next()), static_cast<uint8_t>(1 + rng.next() % 255)};
            const ColorRGBA d{static_cast<uint8_t>(rng.next()), static_cast<uint8_t>(rng.next()), static_cast<uint8_t>(rng.next()), static_cast<uint8_t>(rng.next() % 4 == 0 ? 255 : rng.next())};
            const double opacity = 0.05 + 0.95 * rng.unit();
            const ColorRGBA eight = blendPixel(s, opacity, d, row.mode, row.linear, true);
            const ColorRGBA wide = narrow(blendPixel16(widen(s), opacity, widen(d), row.mode, row.linear));
            const int diffs[4] = {std::abs(eight.r - wide.r), std::abs(eight.g - wide.g), std::abs(eight.b - wide.b), std::abs(eight.a - wide.a)};
            for (const int diff : diffs) {
                ++channels;
                differing += diff != 0;
                worst = std::max(worst, diff);
            }
        }
        // Erase is the one that differs: the 8-bit blend truncates the alpha it keeps (even in Deep Color), the 16-bit
        // one rounds, and narrowing the rounded value gives at most one level more.
        if (worst > 1) fail("against 8 bits", row.name, worst);
        if (row.mode != LayerBlendMode::Erase && worst != 0) fail("against 8 bits", "a mode other than Erase differs from the 8-bit Deep Color blend", worst);
        std::printf("against 8 bits: %-14s max difference %d level, %.3f%% of channels differ\n", row.name, worst,
                    100.0 * static_cast<double>(differing) / static_cast<double>(channels));
    }
}

} // namespace

int main() {
    checkTables();
    BlendKernel::forceLevel(BlendSimdLevel::Scalar);
    checkNormalRows();  // the scalar rows against the definition
    BlendKernel::forceLevel(BlendKernel::bestAvailableLevel());
    checkAvx2Rows();    // and the AVX2 rows, equal to those
    checkOtherModes();
    checkAgainstEightBits();
    if (g_failures == 0) std::printf("blend16 checks: all within bounds\n");
    return g_failures == 0 ? 0 : 1;
}
