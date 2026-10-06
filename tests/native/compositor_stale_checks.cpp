// Checks what the Compositor recomposes, and where, now that it owns a `CompositeProjection` (S3).
//
// `invalidate` marks tiles stale without composing; `ensureFresh` recomposes only the stale tiles a rectangle
// touches; the region composites (stroke, paste, fill, transform) refresh whole tiles and never leave a tile
// half stale. The checks, on a 300x260 canvas (3x3 tiles) with plain layers:
//
//   1. a Compositor is born stale; `composite` makes it fresh;
//   2. laziness: after a layer changes, `invalidate` composes nothing (the buffer keeps the old pixels), a read
//      of another tile composes nothing, a read of the changed tile composes exactly it and the whole buffer
//      then equals a full composition;
//   3. `ensureFresh` writes only stale tiles: a sentinel in a fresh tile and one in a stale tile outside the
//      rectangle both survive, the stale tile inside it is composed;
//   4. a region composite over stale tiles refreshes the whole tiles it touches (a stroke on a stale canvas),
//      and not a neighbour it only grazes through the 2 px margin;
//   5. a stroke over stale tiles: the scratch ink is on screen, and a later `ensureFresh` over the same tile does
//      not erase it (the tile is fresh, so nothing is recomposed there);
//   6. the reach of a blur: an edit 8 px before a tile edge marks the next tile too (a blur of 12 px carries it there);
//   7. random edits under a blur and a pixelate filter, invalidated with the region of the edit and read in random
//      windows: every window read alone equals the full composition in that window, and whenever everything is
//      read the buffer equals a full composition.
//
// Exit code is the failure count; the lines it prints are what tests/test_composite_projection_native.py asserts.
#include "engine/core/canvas/PixelBuffer.hpp"
#include "engine/core/canvas/TileGrid.hpp"
#include "engine/core/document/Compositor.hpp"
#include "engine/core/document/FilterLayer.hpp"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <memory>
#include <random>
#include <vector>

namespace {

using aladyn::engine::canvas::PixelBuffer;
using aladyn::engine::canvas::TileGrid;
using aladyn::engine::document::Compositor;
using aladyn::engine::document::FilterLayer;
using aladyn::engine::document::FilterType;
using aladyn::engine::document::Layer;
using aladyn::engine::document::LayerBlendMode;
using aladyn::engine::utils::ColorRGBA;
using aladyn::engine::utils::Rect2D;

constexpr int kWidth = 300;
constexpr int kHeight = 260;
constexpr ColorRGBA kBackground{255, 255, 255, 255};
int g_failures = 0;

void check(bool ok, const char* what, long a = 0, long b = 0) {
    if (ok) return;
    ++g_failures;
    std::printf("FAIL: %s (%ld, %ld)\n", what, a, b);
}

void paint(TileGrid& grid, int x0, int y0, int x1, int y1, ColorRGBA color) {
    for (int y = std::max(0, y0); y < std::min(kHeight, y1); ++y)
        for (int x = std::max(0, x0); x < std::min(kWidth, x1); ++x)
            grid.getOrCreateTile(x / 128, y / 128)->getBuffer().setPixel(x % 128, y % 128, color);
}

struct Scene {
    std::vector<std::unique_ptr<Layer>> owned;
    std::vector<const Layer*> layers;
    Layer* add(const char* name) {
        owned.push_back(std::make_unique<Layer>(name, kWidth, kHeight));
        layers.push_back(owned.back().get());
        return owned.back().get();
    }
    FilterLayer* addFilter(FilterType type, float param) {
        auto filter = std::make_unique<FilterLayer>("filter", type, kWidth, kHeight);
        filter->setParam(0, param);
        FilterLayer* raw = filter.get();
        owned.push_back(std::move(filter));
        layers.push_back(raw);
        return raw;
    }
};

// What a full composition of the scene gives, made by a Compositor of its own.
PixelBuffer fullComposition(const Scene& scene) {
    Compositor reference(kWidth, kHeight);
    PixelBuffer expected(kWidth, kHeight, kBackground);
    reference.composite(scene.layers, expected, kBackground);
    return expected;
}

bool sameBuffer(const PixelBuffer& a, const PixelBuffer& b) {
    return std::memcmp(a.getData(), b.getData(), a.getSizeInBytes()) == 0;
}

bool sameRegion(const PixelBuffer& a, const PixelBuffer& b, int x0, int y0, int x1, int y1) {
    for (int y = y0; y < y1; ++y)
        for (int x = x0; x < x1; ++x) {
            const ColorRGBA p = a.getPixel(x, y), q = b.getPixel(x, y);
            if (p.r != q.r || p.g != q.g || p.b != q.b || p.a != q.a) return false;
        }
    return true;
}

bool pixelIs(const PixelBuffer& buffer, int x, int y, ColorRGBA color) {
    const ColorRGBA p = buffer.getPixel(x, y);
    return p.r == color.r && p.g == color.g && p.b == color.b && p.a == color.a;
}

Scene twoLayerScene() {
    Scene scene;
    paint(scene.add("base")->getTileGrid(), 0, 0, kWidth, kHeight, {200, 40, 40, 255});
    paint(scene.add("top")->getTileGrid(), 140, 140, 200, 200, {30, 30, 220, 255});
    return scene;
}

void bornStale() {
    Scene scene = twoLayerScene();
    Compositor compositor(kWidth, kHeight);
    check(compositor.staleTileCount() == 9, "a compositor is born with every tile stale", static_cast<long>(compositor.staleTileCount()));
    PixelBuffer buffer(kWidth, kHeight, kBackground);
    compositor.composite(scene.layers, buffer, kBackground);
    check(compositor.staleTileCount() == 0, "a full composition leaves nothing stale");
    check(sameBuffer(buffer, fullComposition(scene)), "the buffer equals a full composition");
}

void invalidateIsLazy() {
    Scene scene = twoLayerScene();
    Compositor compositor(kWidth, kHeight);
    PixelBuffer buffer(kWidth, kHeight, kBackground);
    compositor.composite(scene.layers, buffer, kBackground);

    paint(scene.owned[1]->getTileGrid(), 140, 140, 200, 200, {20, 220, 20, 255});  // blue -> green
    compositor.invalidate(scene.layers, Rect2D{140, 140, 60, 60});
    check(compositor.staleTileCount() == 1, "an edit inside one tile marks one tile", static_cast<long>(compositor.staleTileCount()));
    check(pixelIs(buffer, 150, 150, {30, 30, 220, 255}), "invalidate composes nothing: the old pixel is still there");
    compositor.ensureFresh(scene.layers, Rect2D{0, 0, 100, 100}, buffer, kBackground);
    check(compositor.staleTileCount() == 1 && pixelIs(buffer, 150, 150, {30, 30, 220, 255}), "reading another tile composes nothing");
    compositor.ensureFresh(scene.layers, Rect2D{150, 150, 1, 1}, buffer, kBackground);
    check(compositor.staleTileCount() == 0, "reading the tile composes it");
    check(sameBuffer(buffer, fullComposition(scene)), "the whole buffer equals a full composition again");

    // an edit at a tile boundary reaches the neighbour through the 2 px margin of the region composite
    compositor.invalidate(scene.layers, Rect2D{100, 100, 28, 28});
    check(compositor.staleTileCount() == 4, "the margin of a region touching tile corners marks the 2x2 tiles", static_cast<long>(compositor.staleTileCount()));
}

void ensureFreshWritesOnlyStaleTiles() {
    Scene scene = twoLayerScene();
    Compositor compositor(kWidth, kHeight);
    PixelBuffer buffer(kWidth, kHeight, kBackground);
    compositor.composite(scene.layers, buffer, kBackground);
    const ColorRGBA sentinel{1, 2, 3, 4};
    buffer.setPixel(10, 10, sentinel);    // tile (0,0): fresh, then stale
    buffer.setPixel(140, 10, sentinel);   // tile (1,0)
    compositor.invalidate(scene.layers, Rect2D{0, 0, 300, 260});
    check(compositor.staleTileCount() == 9, "an edit of the whole canvas marks every tile");
    compositor.ensureFresh(scene.layers, Rect2D{200, 200, 10, 10}, buffer, kBackground);
    check(compositor.staleTileCount() == 8, "one read composes one tile", static_cast<long>(compositor.staleTileCount()));
    check(pixelIs(buffer, 10, 10, sentinel) && pixelIs(buffer, 140, 10, sentinel), "stale tiles outside the read are not written");
    check(pixelIs(buffer, 150, 150, {30, 30, 220, 255}), "the stale tile that was read is composed");
    compositor.ensureAllFresh(scene.layers, buffer, kBackground);
    check(compositor.staleTileCount() == 0 && sameBuffer(buffer, fullComposition(scene)), "reading everything composes the rest");
}

void regionCompositeRefreshesWholeTiles() {
    Scene scene = twoLayerScene();
    Compositor compositor(kWidth, kHeight);
    PixelBuffer buffer(kWidth, kHeight, kBackground);
    compositor.invalidateAll();
    compositor.compositeRegion(scene.layers, Rect2D{10, 10, 20, 20}, buffer, kBackground);
    check(compositor.staleTileCount() == 8, "a stroke on a stale canvas refreshes the tile it is in", static_cast<long>(compositor.staleTileCount()));
    const PixelBuffer expected = fullComposition(scene);
    check(sameRegion(buffer, expected, 0, 0, 128, 128), "the whole tile is composed, not only the rectangle");
    compositor.invalidateAll();
    compositor.compositeRegion(scene.layers, Rect2D{120, 10, 8, 8}, buffer, kBackground);
    check(compositor.staleTileCount() == 8, "a rectangle at the tile edge refreshes its tile and only grazes the next one", static_cast<long>(compositor.staleTileCount()));
    check(sameRegion(buffer, expected, 0, 0, 128, 128), "the tile at the edge is composed whole");
}

void strokeInkSurvivesALaterRead() {
    Scene scene = twoLayerScene();
    Compositor compositor(kWidth, kHeight);
    PixelBuffer buffer(kWidth, kHeight, kBackground);
    TileGrid scratch(kWidth, kHeight);
    const ColorRGBA ink{250, 250, 0, 255};
    paint(scratch, 20, 20, 40, 40, ink);
    compositor.invalidateAll();
    compositor.compositeRegionWithScratch(scene.layers, Rect2D{10, 10, 40, 40}, buffer, kBackground, scratch, scene.layers[1],
                                          LayerBlendMode::Normal, 1.0);
    check(pixelIs(buffer, 30, 30, ink), "the ink is on screen");
    check(compositor.staleTileCount() == 8, "the tile under the stroke is fresh, the others stale", static_cast<long>(compositor.staleTileCount()));
    compositor.ensureFresh(scene.layers, Rect2D{0, 0, 128, 128}, buffer, kBackground);
    check(pixelIs(buffer, 30, 30, ink), "a read of the same tile does not erase the ink");
    compositor.ensureAllFresh(scene.layers, buffer, kBackground);
    check(pixelIs(buffer, 30, 30, ink), "neither does a read of everything");
    const PixelBuffer expected = fullComposition(scene);
    check(sameRegion(buffer, expected, 128, 0, kWidth, kHeight) && sameRegion(buffer, expected, 0, 128, 128, kHeight),
          "outside the stroke tile the buffer equals a full composition");
}

void filterReachMarksTheNeighbourTile() {
    // A blur of 12 px: an edit that ends 8 px before the tile edge changes pixels of the next tile, farther than
    // the 2 px margin of a region composite, so the next tile has to be marked stale too.
    Scene scene;
    paint(scene.add("base")->getTileGrid(), 0, 0, kWidth, kHeight, {120, 120, 120, 255});
    Layer* top = scene.add("top");
    paint(top->getTileGrid(), 40, 40, 100, 100, {240, 240, 240, 255});
    scene.addFilter(FilterType::GaussianBlur, 12.0f);
    Compositor compositor(kWidth, kHeight);
    PixelBuffer buffer(kWidth, kHeight, kBackground);
    compositor.composite(scene.layers, buffer, kBackground);
    paint(top->getTileGrid(), 100, 60, 120, 100, {10, 10, 10, 255});
    compositor.invalidate(scene.layers, Rect2D{100, 60, 20, 40});
    check(compositor.staleTileCount() == 2, "an edit within the reach of a blur of the tile edge marks the next tile", static_cast<long>(compositor.staleTileCount()));
    compositor.ensureFresh(scene.layers, Rect2D{128, 60, 8, 40}, buffer, kBackground);
    check(sameRegion(buffer, fullComposition(scene), 128, 60, 136, 100), "the pixels the blur carried into the next tile are composed");
}

void editsUnderFiltersStayEqualToAFullComposition() {
    std::mt19937 rng(20261003);
    for (int round = 0; round < 40; ++round) {
        Scene scene;
        Layer* base = scene.add("base");
        paint(base->getTileGrid(), 0, 0, kWidth, kHeight, {static_cast<uint8_t>(rng() % 256), 90, 160, 255});
        Layer* middle = scene.add("middle");
        Layer* top = scene.add("top");
        scene.addFilter(FilterType::GaussianBlur, static_cast<float>(3 + rng() % 10));
        if (round % 2 == 0) scene.addFilter(FilterType::Pixelate, 8.0f);
        Layer* painted[] = {base, middle, top};

        Compositor compositor(kWidth, kHeight);
        PixelBuffer buffer(kWidth, kHeight, kBackground);
        compositor.composite(scene.layers, buffer, kBackground);
        int reads = 0;
        for (int step = 0; step < 14; ++step) {
            const int x = static_cast<int>(rng() % 320) - 10, y = static_cast<int>(rng() % 280) - 10;
            const int w = 4 + static_cast<int>(rng() % 90), h = 4 + static_cast<int>(rng() % 90);
            paint(painted[rng() % 3]->getTileGrid(), x, y, x + w, y + h,
                  {static_cast<uint8_t>(rng() % 256), static_cast<uint8_t>(rng() % 256), static_cast<uint8_t>(rng() % 256), static_cast<uint8_t>(rng() % 2 ? 255 : 120)});
            const Rect2D region{static_cast<double>(x), static_cast<double>(y), static_cast<double>(w), static_cast<double>(h)};
            if (rng() % 4 == 0) {
                compositor.compositeRegion(scene.layers, region, buffer, kBackground);  // an eager path (stroke, paste, fill)
            } else {
                compositor.invalidate(scene.layers, region);
            }
            if (rng() % 2 == 0) {
                // a window read alone shows the full composition in that window, stale neighbours or not
                const int wx = static_cast<int>(rng() % 300), wy = static_cast<int>(rng() % 260);
                compositor.ensureFresh(scene.layers, Rect2D{static_cast<double>(wx), static_cast<double>(wy), 60, 60}, buffer, kBackground);
                check(sameRegion(buffer, fullComposition(scene), wx, wy, std::min(kWidth, wx + 60), std::min(kHeight, wy + 60)),
                      "a window read alone equals the full composition in that window", round, step);
            }
            if (rng() % 3 == 0) {
                compositor.ensureAllFresh(scene.layers, buffer, kBackground);
                ++reads;
                check(sameBuffer(buffer, fullComposition(scene)), "a full read under filters equals a full composition", round, step);
            }
        }
        compositor.ensureAllFresh(scene.layers, buffer, kBackground);
        check(compositor.staleTileCount() == 0 && sameBuffer(buffer, fullComposition(scene)), "after the last read the buffer equals a full composition", round);
        if (round == 39) std::printf("filters: 40 scenes x 14 edits, full reads equal a full composition (%d in the last scene)\n", reads);
    }
}

} // namespace

int runCompositorStaleChecks() {
    bornStale();
    invalidateIsLazy();
    ensureFreshWritesOnlyStaleTiles();
    regionCompositeRefreshesWholeTiles();
    strokeInkSurvivesALaterRead();
    filterReachMarksTheNeighbourTile();
    editsUnderFiltersStayEqualToAFullComposition();
    std::printf("compositor: laziness, stale-only writes, whole-tile region composites, stroke ink and filters checked\n");
    return g_failures;
}
