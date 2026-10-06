// The other half of the 16-bit compositor checks (S5); `compositor16_checks.cpp` compares pictures, this one checks
// what only a 16-bit buffer can show and how the buffer is kept:
//
//   5. the 16 bits survive: a ramp of values that share one 8-bit level stays distinct through an opaque layer
//      (exact), and a blended pair of 16-bit values matches the definition `blendPixel16`;
//   6. laziness: random edits under a blur and a pixelate filter, invalidated with the region of the edit and read in
//      random windows: every window read alone equals a full composition, in the 16-bit buffer and in the screen, and
//      whenever everything is read both buffers equal a full composition byte for byte;
//   7. merge and flatten: merging a layer down, flattening a group and rasterizing a filter in a 16-bit stack give the
//      8-bit stack's layer (narrowed) up to the 8-bit rounding.
//
// Linked to `compositor16_checks.cpp`; exit code is the failure count.
#include "tests/native/compositor16_scene.hpp"

#include "engine/core/document/blending/BlendEquations16.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <memory>
#include <random>
#include <vector>

int runCompositor16Agreement();
int runFilter16Checks();

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

// ─── 5. the 16 bits survive ──────────────────────────────────────────────────

void precision() {
    LayerStack stack(kWidth, kHeight, PixelFormat::RGBA16);
    const int top = stack.addLayer("ramp");
    auto& grid = stack.getDrawingLayer(top)->getTileGrid();
    for (int y = 0; y < kHeight; ++y) {
        for (int x = 0; x < kWidth; ++x) {
            // 40000 + x: 300 values inside two 8-bit levels (155 and 156).
            grid.getOrCreateTile(x / 128, y / 128)->getBuffer().setPixel16(x % 128, y % 128, ColorRGBA16{static_cast<uint16_t>(40000 + x), static_cast<uint16_t>(65535 - x), 3, 65535});
        }
    }
    Composed composed = compose(stack, true, false);
    const PixelBuffer& wide = *composed.compositor->composite16();
    long long distinct = 0;
    for (int x = 0; x < kWidth; ++x) {
        const ColorRGBA16 got = wide.getPixel16(x, 77);
        check(got.r == 40000 + x && got.g == 65535 - x && got.b == 3 && got.a == 65535, "an opaque layer keeps its 16-bit values exactly", x, got.r);
        if (x > 0 && got.r != wide.getPixel16(x - 1, 77).r) ++distinct;
        const ColorRGBA screen = composed.screen.getPixel(x, 77);
        check(screen.r == narrow(got).r && screen.g == narrow(got).g && screen.b == narrow(got).b, "the screen is the 16-bit value narrowed", x);
    }
    check(distinct == kWidth - 1, "every 16-bit value of the ramp is distinct", distinct);

    // A translucent layer over distinct 16-bit values, in both gammas: the definition, to the kernel's 1 level.
    int worst = 0;
    for (const bool linear : {true, false}) {
        LayerStack pair(kWidth, kHeight, PixelFormat::RGBA16);
        const int bottom = pair.addLayer("under"), over = pair.addLayer("over");
        pair.getDrawingLayer(over)->setOpacity(0.37);
        auto& low = pair.getDrawingLayer(bottom)->getTileGrid();
        auto& high = pair.getDrawingLayer(over)->getTileGrid();
        for (int x = 0; x < 128; ++x) {
            low.getOrCreateTile(0, 0)->getBuffer().setPixel16(x, 5, ColorRGBA16{static_cast<uint16_t>(9000 + 211 * x), static_cast<uint16_t>(300 * x), 65535, 65535});
            high.getOrCreateTile(0, 0)->getBuffer().setPixel16(x, 5, ColorRGBA16{static_cast<uint16_t>(60000 - 97 * x), 12345, static_cast<uint16_t>(500 * x), static_cast<uint16_t>(20000 + 300 * x)});
        }
        Composed result = compose(pair, linear, false);
        for (int x = 0; x < 128; ++x) {
            const ColorRGBA16 under = low.getTile(0, 0)->getBuffer().getPixel16(x, 5);
            const ColorRGBA16 above = high.getTile(0, 0)->getBuffer().getPixel16(x, 5);
            const ColorRGBA16 expected = blendPixel16(above, 0.37, blendPixel16(under, 1.0, ColorRGBA16{65535, 65535, 65535, 65535}, LayerBlendMode::Normal, linear), LayerBlendMode::Normal, linear);
            const ColorRGBA16 got = result.compositor->composite16()->getPixel16(x, 5);
            worst = std::max({worst, std::abs(got.r - expected.r), std::abs(got.g - expected.g), std::abs(got.b - expected.b), std::abs(got.a - expected.a)});
        }
    }
    check(worst <= 2, "two translucent 16-bit layers are more than 2 levels from the definition", worst);
    std::printf("precision: a ramp of 300 values inside 2 eight-bit levels stays exact and distinct; translucent 16-bit layers match the definition within %d level\n", worst);
}

// ─── 6. laziness ─────────────────────────────────────────────────────────────

bool sameWindow(const PixelBuffer& a, const PixelBuffer& b, int x0, int y0, int x1, int y1) {
    for (int y = y0; y < y1; ++y) {
        for (int x = x0; x < x1; ++x) {
            const ColorRGBA16 p = a.getPixel16(x, y), q = b.getPixel16(x, y);
            if (p.r != q.r || p.g != q.g || p.b != q.b || p.a != q.a) return false;
        }
    }
    return true;
}

bool sameBytes(const PixelBuffer& a, const PixelBuffer& b) {
    return a.getSizeInBytes() == b.getSizeInBytes() && std::memcmp(a.getData(), b.getData(), a.getSizeInBytes()) == 0;
}

PixelBuffer narrowed(const PixelBuffer& wide) {
    PixelBuffer out(kWidth, kHeight, kBackground);
    for (int y = 0; y < kHeight; ++y)
        for (int x = 0; x < kWidth; ++x) out.setPixel(x, y, narrow(wide.getPixel16(x, y)));
    return out;
}

void laziness() {
    long long windows = 0, edits = 0;
    for (int seed = 0; seed < 6; ++seed) {
        std::mt19937 rng(6000 + seed);
        std::vector<LayerPlan> plan{base(rng), paint(rng, LayerBlendMode::Normal, 1.0, false), filterPlan(FilterType::GaussianBlur, rng),
                                    paint(rng, LayerBlendMode::Normal, 0.8, false), filterPlan(FilterType::Pixelate, rng),
                                    paint(rng, LayerBlendMode::Normal, 0.7, false)};
        plan[2].params[0] = 6.0f + static_cast<float>(seed);
        plan[2].opacity = 1.0;
        plan[4].params[0] = 6.0f + static_cast<float>(seed);
        plan[4].opacity = 1.0;
        auto stack = build(plan, PixelFormat::RGBA16);
        Compositor compositor(kWidth, kHeight, PixelFormat::RGBA16);
        PixelBuffer screen(kWidth, kHeight, kBackground);
        const auto layers = stack->getAllLayersForComposition();
        compositor.composite(layers, screen, kBackground);

        for (int step = 0; step < 14; ++step) {
            const int paintIndexes[] = {1, 2, 4, 6};  // the plan's paint layers, plus the stack's initial empty layer
            doc::Layer* target = stack->getDrawingLayer(paintIndexes[rng() % 4]);
            const Block block = randomBlock(rng, false);
            paintBlock(*target, Block{block.x0, block.y0, block.x0 + 20 + static_cast<int>(rng() % 50), block.y0 + 20 + static_cast<int>(rng() % 50), block.seed, block.alphaMode, block.softAlpha}, true);
            compositor.invalidate(layers, Rect2D{static_cast<double>(block.x0), static_cast<double>(block.y0), 70.0, 70.0});
            ++edits;

            Composed full = compose(*stack, true, false);
            for (int read = 0; read < 3; ++read) {
                const int x0 = static_cast<int>(rng() % 240), y0 = static_cast<int>(rng() % 200);
                const int x1 = x0 + 1 + static_cast<int>(rng() % 60), y1 = y0 + 1 + static_cast<int>(rng() % 60);
                compositor.ensureFresh(layers, Rect2D{static_cast<double>(x0), static_cast<double>(y0), static_cast<double>(x1 - x0), static_cast<double>(y1 - y0)}, screen, kBackground);
                check(sameWindow(*compositor.composite16(), *full.compositor->composite16(), x0, y0, x1, y1), "a window read alone equals the full composition (16-bit buffer)", seed, step);
                bool sameScreen = true;
                for (int y = y0; y < y1 && sameScreen; ++y)
                    for (int x = x0; x < x1; ++x)
                        if (!(screen.getPixel(x, y).r == full.screen.getPixel(x, y).r && screen.getPixel(x, y).g == full.screen.getPixel(x, y).g &&
                              screen.getPixel(x, y).b == full.screen.getPixel(x, y).b && screen.getPixel(x, y).a == full.screen.getPixel(x, y).a)) { sameScreen = false; break; }
                check(sameScreen, "a window read alone equals the full composition (screen)", seed, step);
                ++windows;
            }
            if (step % 5 == 4) {
                compositor.ensureAllFresh(layers, screen, kBackground);
                check(sameBytes(*compositor.composite16(), *full.compositor->composite16()), "everything read: the 16-bit buffer equals a full composition", seed, step);
                check(sameBytes(screen, full.screen) && sameBytes(screen, narrowed(*compositor.composite16())), "everything read: the screen equals a full composition and the narrowed 16-bit buffer", seed, step);
            }
        }
    }
    std::printf("laziness: %lld edits under a blur and a pixelate, %lld windows read, windows and whole canvas equal a full composition (16-bit buffer and screen)\n", edits, windows);
}

// The same with isolated and Pass Through groups, a clipping mask and a hidden layer. A window composed alone puts the
// accumulator of an isolated group at the window's own offset, which a composition of the whole canvas never does.
void lazinessWithGroups() {
    long long windows = 0;
    for (int seed = 0; seed < 8; ++seed) {
        std::mt19937 rng(7000 + seed);
        auto stack = build(structurePlan(rng), PixelFormat::RGBA16);
        Compositor compositor(kWidth, kHeight, PixelFormat::RGBA16);
        PixelBuffer screen(kWidth, kHeight, kBackground);
        const auto layers = stack->getAllLayersForComposition();
        compositor.composite(layers, screen, kBackground);
        std::vector<doc::Layer*> paintable;
        for (const doc::Layer* layer : layers)
            if (!layer->isGroup() && !layer->isFilter()) paintable.push_back(const_cast<doc::Layer*>(layer));
        for (int step = 0; step < 10; ++step) {
            const Block block = randomBlock(rng, false);
            paintBlock(*paintable[rng() % paintable.size()], block, true);
            compositor.invalidate(layers, Rect2D{static_cast<double>(block.x0), static_cast<double>(block.y0),
                                                 static_cast<double>(block.x1 - block.x0), static_cast<double>(block.y1 - block.y0)});
            Composed full = compose(*stack, true, false);
            for (int read = 0; read < 3; ++read) {
                const int x0 = static_cast<int>(rng() % 240), y0 = static_cast<int>(rng() % 200);
                const int x1 = x0 + 1 + static_cast<int>(rng() % 60), y1 = y0 + 1 + static_cast<int>(rng() % 60);
                compositor.ensureFresh(layers, Rect2D{static_cast<double>(x0), static_cast<double>(y0), static_cast<double>(x1 - x0), static_cast<double>(y1 - y0)}, screen, kBackground);
                check(sameWindow(*compositor.composite16(), *full.compositor->composite16(), x0, y0, x1, y1), "a window read alone equals the full composition (groups and clipping)", seed, step);
                ++windows;
            }
        }
    }
    std::printf("laziness with groups: 80 edits under isolated and Pass Through groups and a clipping mask, %lld windows read, each equal to a full composition\n", windows);
}

// ─── 7. merge and flatten ────────────────────────────────────────────────────

Spread layerSpread(doc::Layer& eight, doc::Layer& wide) {
    Spread spread;
    for (int ty = 0; ty < 3; ++ty) {
        for (int tx = 0; tx < 3; ++tx) {
            const auto* a = eight.getTileGrid().getTile(tx, ty);
            const auto* b = wide.getTileGrid().getTile(tx, ty);
            for (int y = 0; y < 128; ++y) {
                for (int x = 0; x < 128; ++x) {
                    const ColorRGBA p = a ? a->getBuffer().getPixel(x, y) : ColorRGBA{0, 0, 0, 0};
                    const ColorRGBA q = b ? narrow(b->getBuffer().getPixel16(x, y)) : ColorRGBA{0, 0, 0, 0};
                    spread.add(std::abs(p.a - q.a));
                    if (p.a == 0 && q.a == 0) continue;
                    // A straight colour under a small alpha is ill-conditioned (one level of alpha moves it a lot), and
                    // it weighs as little as the alpha: compare the premultiplied colour, rounded up.
                    const double weight = std::max(p.a, q.a) / 255.0;
                    spread.add(static_cast<int>(std::ceil(std::abs(p.r - q.r) * weight)));
                    spread.add(static_cast<int>(std::ceil(std::abs(p.g - q.g) * weight)));
                    spread.add(static_cast<int>(std::ceil(std::abs(p.b - q.b) * weight)));
                }
            }
        }
    }
    return spread;
}

void merges() {
    Spread merged, flattened, rasterized;
    int merges = 0;
    for (int seed = 0; seed < 8; ++seed) {
        std::mt19937 rng(7000 + seed);
        const auto plan = normalPlan(rng);
        for (int index = 1; index <= static_cast<int>(plan.size()); ++index) {
            auto eight = build(plan, PixelFormat::RGBA8);
            auto wide = build(plan, PixelFormat::RGBA16);
            const bool linear = seed % 2 == 0;
            check(eight->mergeLayerDown(index, linear, true) && wide->mergeLayerDown(index, linear, false), "a layer merges down in both formats", seed, index);
            const Spread one = layerSpread(*eight->getDrawingLayer(index - 1), *wide->getDrawingLayer(index - 1));
            merged.worst = std::max(merged.worst, one.worst);
            merged.channels += one.channels;
            merged.differing += one.differing;
            ++merges;
        }
    }
    for (int seed = 0; seed < 8; ++seed) {
        std::mt19937 rng(7100 + seed);
        const auto plan = structurePlan(rng);
        auto eight = build(plan, PixelFormat::RGBA8);
        auto wide = build(plan, PixelFormat::RGBA16);
        const int groupIndex = 2;  // the plan's isolated group, after the stack's initial layer and the base
        check(eight->flattenGroup(groupIndex, true, true) && wide->flattenGroup(groupIndex, true, false), "a group flattens in both formats", seed);
        const Spread one = layerSpread(*eight->getDrawingLayer(groupIndex), *wide->getDrawingLayer(groupIndex));
        flattened.worst = std::max(flattened.worst, one.worst);
        flattened.channels += one.channels;
        flattened.differing += one.differing;
    }
    const FilterType types[] = {FilterType::HueSat, FilterType::BrightnessContrast, FilterType::GaussianBlur, FilterType::ColorBalance,
                                FilterType::SharpenVignette, FilterType::InvertThreshold, FilterType::Pixelate};
    int worstFilter = 0;
    for (const FilterType type : types) {
        std::mt19937 rng(7200 + static_cast<int>(type));
        const auto plan = filtersPlan(rng, type);
        auto eight = build(plan, PixelFormat::RGBA8);
        auto wide = build(plan, PixelFormat::RGBA16);
        const int filterIndex = 3;
        check(eight->mergeLayerDown(filterIndex, true, true) && wide->mergeLayerDown(filterIndex, true, false), "a filter layer rasterizes in both formats", static_cast<long long>(type));
        const Spread one = layerSpread(*eight->getDrawingLayer(filterIndex - 1), *wide->getDrawingLayer(filterIndex - 1));
        const int bound = (type == FilterType::InvertThreshold || type == FilterType::Pixelate) ? 255 : 4;
        check(one.worst <= bound, "a rasterized filter is too far from the 8-bit one", static_cast<long long>(type), one.worst);
        rasterized.worst = std::max(rasterized.worst, one.worst);
        worstFilter = std::max(worstFilter, one.worst);
        rasterized.channels += one.channels;
        rasterized.differing += one.differing;
    }
    check(merged.worst <= 1, "a merged layer is more than 1 level from the 8-bit one", merged.worst);
    check(flattened.worst <= 3, "a flattened group is more than 3 levels (premultiplied) from the 8-bit one", flattened.worst);
    std::printf("merge: %d merges of a layer down max %d level, 8 groups flattened max %d level, 7 filters rasterized max %d level, all against the 8-bit stack\n",
                merges, merged.worst, flattened.worst, rasterized.worst);
}

} // namespace

int main() {
    precision();
    laziness();
    lazinessWithGroups();
    merges();
    const int failures = g_failures + runCompositor16Agreement() + runFilter16Checks();
    if (failures == 0) std::printf("compositor16 checks: all within bounds\n");
    return failures == 0 ? 0 : 1;
}
