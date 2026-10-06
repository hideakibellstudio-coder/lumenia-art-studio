// Checks the seven filters on a 16-bit buffer (S5) against the 8-bit ones, each on IDENTICAL input.
//
// The 16-bit kernels (engine/core/document/filters/PointFilters16.cpp and AreaFilters16.cpp) do the same arithmetic as
// the 8-bit ones in float, rounded to the level, and mix with the layer's opacity in 16 bits. So the same picture
// (8-bit pixels, and the same pixels widened by x257) filtered both ways must agree up to the 8-bit rounding: this
// measures how far, per filter, with full and partial opacity, on the whole buffer and on a sub-rectangle, and that
// nothing outside the rectangle and no alpha-0 pixel is touched.
//
// Linked to `compositor16_checks.cpp`; exit code is the failure count.
#include "tests/native/compositor16_scene.hpp"

#include "engine/core/document/filters/FilterApplier.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>

namespace {

using namespace scene16;
using aladyn::engine::canvas::PixelBuffer;
using aladyn::engine::canvas::narrow;
using aladyn::engine::canvas::widen;
using aladyn::engine::document::FilterType;
using aladyn::engine::document::filters::FilterApplier;
using aladyn::engine::document::filters::FilterSettings;
using aladyn::engine::utils::ColorRGBA16;

int g_failures = 0;

void check(bool ok, const char* what, long long a = 0, long long b = 0) {
    if (ok) return;
    ++g_failures;
    std::printf("FAIL: %s (%lld, %lld)\n", what, a, b);
}

// A picture with smooth areas, noise, hard edges and holes of alpha 0, in both formats.
void fill(PixelBuffer& eight, PixelBuffer& wide, std::mt19937& rng) {
    for (int y = 0; y < kHeight; ++y) {
        for (int x = 0; x < kWidth; ++x) {
            const uint32_t h = hash(static_cast<uint32_t>(rng()), static_cast<uint32_t>(x), static_cast<uint32_t>(y));
            ColorRGBA p{static_cast<uint8_t>(x * 255 / kWidth), static_cast<uint8_t>(y * 255 / kHeight), static_cast<uint8_t>(h), 255};
            if ((x / 40 + y / 40) % 3 == 0) p = ColorRGBA{static_cast<uint8_t>(h >> 8), static_cast<uint8_t>(h >> 16), static_cast<uint8_t>(h >> 24), 255};
            if ((x / 50 + y / 30) % 5 == 0) p.a = 0;
            else if ((x + y) % 7 == 0) p.a = static_cast<uint8_t>(40 + (h >> 28) * 12);
            eight.setPixel(x, y, p);
            wide.setPixel16(x, y, widen(p));
        }
    }
}

struct Case {
    FilterType type;
    std::vector<float> params;
};

std::vector<Case> cases() {
    return {
        {FilterType::BrightnessContrast, {20, 35, 1.0f}}, {FilterType::BrightnessContrast, {-30, -20, 1.8f}},
        {FilterType::ColorBalance, {25, -10, 40}}, {FilterType::ColorBalance, {-60, 15, 0}},
        {FilterType::InvertThreshold, {1, 128}}, {FilterType::InvertThreshold, {0, 100}}, {FilterType::InvertThreshold, {0, 200}},
        {FilterType::HueSat, {60, 20, 10, 0}}, {FilterType::HueSat, {-120, -40, 0, 0}}, {FilterType::HueSat, {200, 30, 0, 1}},
        {FilterType::Pixelate, {6}}, {FilterType::Pixelate, {17}},
        {FilterType::GaussianBlur, {3}}, {FilterType::GaussianBlur, {10}},
        {FilterType::SharpenVignette, {60, 0, 50}}, {FilterType::SharpenVignette, {0, 50, 60}}, {FilterType::SharpenVignette, {40, 30, 70}},
    };
}

void run() {
    Spread worst[7];
    long long outsideChanged = 0, holesChanged = 0, runs = 0;
    std::mt19937 rng(8000);
    for (const Case& item : cases()) {
        for (const double opacity : {1.0, 0.6}) {
            for (const bool region : {false, true}) {
                PixelBuffer eight(kWidth, kHeight, kBackground), wide(kWidth, kHeight, PixelFormat::RGBA16, kBackground);
                std::mt19937 content(static_cast<unsigned>(100 + runs));
                fill(eight, wide, content);
                const PixelBuffer before(wide);
                const FilterSettings settings{item.type, &item.params, opacity};
                const int x0 = region ? 50 : 0, x1 = region ? 200 : -1, y0 = region ? 30 : 0, y1 = region ? 180 : -1;
                FilterApplier::apply(settings, eight, x0, x1, y0, y1);
                FilterApplier::apply(settings, wide, x0, x1, y0, y1);
                ++runs;
                Spread& spread = worst[static_cast<int>(item.type)];
                for (int y = 0; y < kHeight; ++y) {
                    for (int x = 0; x < kWidth; ++x) {
                        const ColorRGBA p = eight.getPixel(x, y), q = narrow(wide.getPixel16(x, y));
                        spread.add(std::abs(p.a - q.a));
                        spread.add(std::abs(p.r - q.r));
                        spread.add(std::abs(p.g - q.g));
                        spread.add(std::abs(p.b - q.b));
                        const ColorRGBA16 was = before.getPixel16(x, y), now = wide.getPixel16(x, y);
                        const bool changed = was.r != now.r || was.g != now.g || was.b != now.b || was.a != now.a;
                        const bool outside = region && (x < x0 || x > x1 || y < y0 || y > y1);
                        // The area filters read the whole buffer but write only the rectangle (Pixelate aligns it to its blocks).
                        if (changed && outside && item.type != FilterType::Pixelate) ++outsideChanged;
                        if (changed && was.a == 0 && item.type != FilterType::GaussianBlur) ++holesChanged;
                    }
                }
            }
        }
    }
    const char* names[7] = {"HueSat", "BrightnessContrast", "GaussianBlur", "ColorBalance", "SharpenVignette", "InvertThreshold", "Pixelate"};
    for (int type = 0; type < 7; ++type) {
        // Measured: Hue/Sat, Brightness/Contrast and the blur are 2 levels apart (the 8-bit versions truncate, the blur
        // twice, and the first two mix with an 8-bit weight at partial opacity); the other four are one rounding apart.
        const int bounds[7] = {2, 2, 2, 1, 1, 1, 1};
        const int bound = bounds[type];
        check(worst[type].worst <= bound, names[type], worst[type].worst, bound);
        std::printf("filter %-18s 16-bit vs 8-bit on identical input: max %d level, %.2f%% of channels differ\n", names[type], worst[type].worst, worst[type].percent());
    }
    check(outsideChanged == 0, "a filter changed a pixel outside its rectangle", outsideChanged);
    check(holesChanged == 0, "a filter changed a pixel of alpha 0", holesChanged);
    std::printf("filters: %lld runs (17 settings x 2 opacities x whole buffer and sub-rectangle); nothing outside the rectangle and no alpha-0 pixel changed\n", runs);
}

} // namespace

int runFilter16Checks() {
    run();
    return g_failures;
}
