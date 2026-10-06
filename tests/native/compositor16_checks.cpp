// Checks the 16-bit compositor (S5) without Python: a document of 16-bit layers composed into the 8-bit screen buffer.
//
// A 16-bit document composes its layers in an internal 16-bit buffer (`Compositor::composite16`) and narrows to the
// 8-bit screen only the pixels it composed. These checks put the same content (every 8-bit pixel widened by x257) in
// an 8-bit document and in a 16-bit one, and measure how far apart the two pictures are. The 16-bit one is the more
// accurate (it rounds once, at the screen; the 8-bit one rounds at every layer), so the distance is not an error, but
// a wiring mistake (a wrong tile offset, clip alpha, group origin, filter format) would be far larger than the bounds:
//
//   1. Normal stacks, linear and sRGB gamma: the 16-bit composite against a per-pixel model that applies the
//      definition `blendPixel16` layer by layer (a kernel error of 1 level per layer at most), and against the 8-bit
//      document in 8-bit levels;
//   2. other modes over an opaque base: the 16-bit composite equals the per-pixel model EXACTLY (the rows of those
//      modes are the definition);
//   3. groups (isolated and Pass Through), clipping masks and hidden layers against the 8-bit document;
//   4. the seven filters among layers against the 8-bit document;
//   5. the 16 bits survive: values that share one 8-bit level stay distinct, and blended values match the definition;
//   6. laziness: invalidating a region and reading random windows gives, window by window and then for the whole
//      canvas, the very bytes of a full composition, in the 16-bit buffer and in the screen.
//
// Exit code is the failure count; the numbers are printed so the documentation can quote what was measured.
#include "tests/native/compositor16_scene.hpp"

#include "engine/core/document/Compositor.hpp"
#include "engine/core/document/CompositeRegionSupport.hpp"
#include "engine/core/document/blending/BlendEquations16.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <memory>
#include <random>
#include <vector>

namespace {

using namespace scene16;
using aladyn::engine::canvas::PixelBuffer;
using aladyn::engine::canvas::narrow;
using aladyn::engine::canvas::widen;
using aladyn::engine::document::Compositor;
using aladyn::engine::document::FilterType;
using aladyn::engine::document::LayerBlendMode;
using aladyn::engine::document::LayerStack;
using aladyn::engine::document::blending::blendPixel16;
using aladyn::engine::utils::ColorRGBA16;
using aladyn::engine::utils::Rect2D;

int g_failures = 0;

void check(bool ok, const char* what, long long a = 0, long long b = 0) {
    if (ok) return;
    ++g_failures;
    std::printf("FAIL: %s (%lld, %lld)\n", what, a, b);
}

// ─── 1-4: agreement ──────────────────────────────────────────────────────────

// The 16-bit composite against a model that blends the layers one pixel at a time with the definition: it follows the
// order of the stack, isolated groups (each accumulates its children, then blends onto what is below with the group's
// opacity and mode) and clipping masks (the opacity is scaled by the alpha of the base), and nothing else.
Spread againstModel(LayerStack& wide, const Compositor& compositor, bool linear) {
    Spread spread;
    const PixelBuffer& result = *compositor.composite16();
    const auto layers = wide.getAllLayersForComposition();
    const auto pixelOf = [](const doc::Layer& layer, int x, int y, bool& present) {
        const auto* tile = const_cast<doc::Layer&>(layer).getTileGrid().getTile(x / 128, y / 128);
        present = tile != nullptr;
        return tile ? tile->getBuffer().getPixel16(x % 128, y % 128) : ColorRGBA16{0, 0, 0, 0};
    };
    for (int y = 0; y < kHeight; ++y) {
        for (int x = 0; x < kWidth; ++x) {
            ColorRGBA16 accumulated{65535, 65535, 65535, 65535};
            ColorRGBA16 group{0, 0, 0, 0};
            const doc::Layer* active = nullptr;
            const auto flush = [&] {
                if (active && active->getEffectiveOpacity() > 0.0 && group.a != 0)
                    accumulated = blendPixel16(group, active->getEffectiveOpacity(), accumulated, active->getBlendMode(), linear);
            };
            for (const doc::Layer* layer : layers) {
                if (!layer->isVisible() || layer->getEffectiveOpacity() <= 0.0) continue;
                const doc::Layer* isolated = aladyn::engine::document::internal::getIsolatedGroupAncestor(layer);
                if (isolated != active) {
                    flush();
                    group = ColorRGBA16{0, 0, 0, 0};
                    active = isolated;
                }
                bool present = false;
                const ColorRGBA16 source = pixelOf(*layer, x, y, present);
                if (!present || source.a == 0) continue;
                double opacity = active ? aladyn::engine::document::internal::getRelativeOpacity(layer, active) : layer->getEffectiveOpacity();
                if (layer->isClippingMask() && layer->getClipBase()) {
                    const doc::Layer* clipBase = layer->getClipBase();
                    bool basePresent = false;
                    const ColorRGBA16 base = pixelOf(*clipBase, x, y, basePresent);
                    const double baseAlpha = aladyn::engine::document::blending::detail16::unit(base.a) * clipBase->getEffectiveOpacity();
                    if (!basePresent || baseAlpha <= 0.0) continue;
                    opacity *= baseAlpha;
                }
                ColorRGBA16& target = active ? group : accumulated;
                target = blendPixel16(source, opacity, target, layer->getBlendMode(), linear);
            }
            flush();
            const ColorRGBA16 got = result.getPixel16(x, y);
            spread.add(std::abs(got.r - accumulated.r));
            spread.add(std::abs(got.g - accumulated.g));
            spread.add(std::abs(got.b - accumulated.b));
            spread.add(std::abs(got.a - accumulated.a));
        }
    }
    return spread;
}

void normalStacks() {
    Spread model, screens;
    int scenes = 0;
    for (int seed = 0; seed < 24; ++seed) {
        std::mt19937 rng(1000 + seed);
        const bool linear = seed % 2 == 0;
        const auto plan = normalPlan(rng);
        auto eight = build(plan, PixelFormat::RGBA8);
        auto wide = build(plan, PixelFormat::RGBA16);
        Composed a = compose(*eight, linear, true), b = compose(*wide, linear, false);
        spreadOfScreens(a.screen, b.screen, screens);
        const Spread one = againstModel(*wide, *b.compositor, linear);
        model.worst = std::max(model.worst, one.worst);
        model.channels += one.channels;
        model.differing += one.differing;
        ++scenes;
    }
    check(model.worst <= 5, "a Normal stack is more than 5 levels of 16 bits from the per-pixel model", model.worst);
    check(screens.worst <= 3, "a Normal stack differs from the 8-bit document by more than 3 levels", screens.worst);
    std::printf("normal stacks: %d scenes, 16-bit composite vs the definition max %d level of 16 bits (%.4f%% of channels), screen vs the 8-bit document max %d level (%.2f%%)\n",
                scenes, model.worst, model.percent(), screens.worst, screens.percent());
}

void otherModes() {
    Spread model;
    int scenes = 0;
    for (int seed = 0; seed < 36; ++seed) {
        std::mt19937 rng(2000 + seed);
        const bool linear = seed % 2 == 0;
        const auto plan = modesPlan(rng, seed);
        auto wide = build(plan, PixelFormat::RGBA16);
        Composed b = compose(*wide, linear, false);
        const Spread one = againstModel(*wide, *b.compositor, linear);
        model.worst = std::max(model.worst, one.worst);
        model.channels += one.channels;
        model.differing += one.differing;
        ++scenes;
    }
    check(model.worst == 0, "other modes over an opaque base are not exactly the definition", model.worst);
    std::printf("other modes: %d scenes of 12 modes over an opaque base, 16-bit composite equals the definition exactly\n", scenes);
}

void structures() {
    Spread screens, model;
    for (int seed = 0; seed < 24; ++seed) {
        std::mt19937 rng(3000 + seed);
        const bool linear = seed % 3 != 0;
        const auto plan = structurePlan(rng);
        auto eight = build(plan, PixelFormat::RGBA8);
        auto wide = build(plan, PixelFormat::RGBA16);
        Composed a = compose(*eight, linear, true), b = compose(*wide, linear, false);
        spreadOfScreens(a.screen, b.screen, screens);
        model.merge(againstModel(*wide, *b.compositor, linear));
    }
    check(model.worst <= 4, "groups, clipping and hidden layers are more than 4 levels of 16 bits from the per-pixel model", model.worst);
    check(screens.worst <= 5, "groups, clipping and hidden layers differ from the 8-bit document by more than 5 levels", screens.worst);
    std::printf("structures: 24 scenes with isolated and Pass Through groups, clipping masks and hidden layers, 16-bit composite vs the definition max %d level of 16 bits (%.3f%% of channels), screen vs the 8-bit document max %d level (%.2f%%)\n",
                model.worst, model.percent(), screens.worst, screens.percent());
}

void filters() {
    const FilterType types[] = {FilterType::HueSat, FilterType::BrightnessContrast, FilterType::GaussianBlur, FilterType::ColorBalance,
                                FilterType::SharpenVignette, FilterType::InvertThreshold, FilterType::Pixelate};
    for (const FilterType type : types) {
        Spread screens;
        for (int seed = 0; seed < 6; ++seed) {
            std::mt19937 rng(4000 + static_cast<int>(type) * 31 + seed);
            const auto plan = filtersPlan(rng, type);
            auto eight = build(plan, PixelFormat::RGBA8);
            auto wide = build(plan, PixelFormat::RGBA16);
            Composed a = compose(*eight, true, true), b = compose(*wide, true, false);
            spreadOfScreens(a.screen, b.screen, screens);
        }
        // The two documents hand the filter inputs that differ by the 8-bit rounding of the layers below; Hue/Sat and
        // the threshold turn that into a different hue or a flipped pixel where the colour is near grey or near the
        // threshold, so for those two the bound is on how many channels are far, not on the worst one. Each filter on
        // identical input is checked exactly in filter16_checks.cpp.
        const bool unstable = type == FilterType::HueSat || type == FilterType::InvertThreshold;
        check(unstable ? screens.percentBeyondFour() < 3.0 : screens.worst <= 4, "a filter among layers is too far from the 8-bit document", static_cast<long long>(type), screens.worst);
        std::printf("filters: type %d, 6 scenes, screen vs the 8-bit document max %d level (%.2f%% of channels differ, %.3f%% by more than 4)\n",
                    static_cast<int>(type), screens.worst, screens.percent(), screens.percentBeyondFour());
    }
}

} // namespace

int runCompositor16Agreement() {
    normalStacks();
    otherModes();
    structures();
    filters();
    return g_failures;
}
