// Checks `CompositeProjection` (engine/core/document/projection/) against a model written another way.
//
// The projection remembers, per 128x128 tile of the composite buffer, whether the buffer there still equals what
// the layers compose to. The model below keeps the same thing as one bool per tile and answers every question by
// intersecting intervals (the implementation divides pixel coordinates into tile indices), so a wrong index, a
// wrong clip at the canvas edge or a wrong merge shows up as a difference. After each of thousands of random
// operations (mark stale, mark fresh, rectangles inside, across and outside the canvas, empty and inverted ones)
// the harness compares:
//
//   - the number of stale tiles and `anyStale`;
//   - `expandToStale(rect)`: the box around `rect` and the whole extent of every stale tile it touches;
//   - `staleRects(rect)`: the boxes are tile aligned (clipped to the canvas), do not overlap, and their tiles are
//     exactly the stale tiles `rect` touches, no more and no fewer.
//
// Then a few shapes with known answers (a stale canvas is one box, a checkerboard is one box per tile, a stale
// column is one box) and the edge cases (a canvas of 1x1, 127, 128 and 129 pixels).
//
// Exit code 1 on any difference. The Compositor side (what is recomposed, and where) is in
// compositor_stale_checks.cpp, linked into the same executable.
#include "engine/core/document/projection/CompositeProjection.hpp"

#include <algorithm>
#include <cstdio>
#include <random>
#include <set>
#include <utility>
#include <vector>

int runCompositorStaleChecks();

namespace {

using aladyn::engine::document::projection::CompositeProjection;
using aladyn::engine::document::projection::PixelRect;

constexpr int kTile = CompositeProjection::kTileSize;
int g_failures = 0;

void check(bool ok, const char* what, int a = 0, int b = 0) {
    if (ok) return;
    ++g_failures;
    std::printf("FAIL: %s (%d, %d)\n", what, a, b);
}

// A tile per bool; every answer is an interval intersection.
struct Model {
    int width, height, tilesX, tilesY;
    std::vector<char> stale;

    Model(int w, int h) : width(w), height(h), tilesX((w + kTile - 1) / kTile), tilesY((h + kTile - 1) / kTile),
                          stale(static_cast<size_t>(tilesX) * tilesY, 1) {}

    PixelRect extent(int tx, int ty) const {
        return {tx * kTile, ty * kTile, std::min((tx + 1) * kTile, width), std::min((ty + 1) * kTile, height)};
    }
    char& at(int tx, int ty) { return stale[static_cast<size_t>(ty) * tilesX + tx]; }
    char at(int tx, int ty) const { return stale[static_cast<size_t>(ty) * tilesX + tx]; }

    // `rect` clipped to the canvas shares pixels with the tile?
    bool touches(const PixelRect& rect, int tx, int ty) const {
        const PixelRect e = extent(tx, ty);
        return std::max(rect.x0, e.x0) < std::min(rect.x1, e.x1) && std::max(rect.y0, e.y0) < std::min(rect.y1, e.y1);
    }
    static bool inside(const PixelRect& e, const PixelRect& rect) {
        return e.x0 >= rect.x0 && e.x1 <= rect.x1 && e.y0 >= rect.y0 && e.y1 <= rect.y1;
    }
    void markStale(const PixelRect& rect) {
        for (int ty = 0; ty < tilesY; ++ty)
            for (int tx = 0; tx < tilesX; ++tx)
                if (touches(rect, tx, ty)) at(tx, ty) = 1;
    }
    void markFresh(const PixelRect& rect) {
        for (int ty = 0; ty < tilesY; ++ty)
            for (int tx = 0; tx < tilesX; ++tx)
                if (inside(extent(tx, ty), rect)) at(tx, ty) = 0;
    }
    int count() const { return static_cast<int>(std::count(stale.begin(), stale.end(), 1)); }
    PixelRect expand(const PixelRect& rect) const {
        PixelRect box = rect;
        for (int ty = 0; ty < tilesY; ++ty)
            for (int tx = 0; tx < tilesX; ++tx) {
                if (!at(tx, ty) || !touches(rect, tx, ty)) continue;
                const PixelRect e = extent(tx, ty);
                box = {std::min(box.x0, e.x0), std::min(box.y0, e.y0), std::max(box.x1, e.x1), std::max(box.y1, e.y1)};
            }
        return box;
    }
    std::set<std::pair<int, int>> staleTilesTouching(const PixelRect& rect) const {
        std::set<std::pair<int, int>> tiles;
        for (int ty = 0; ty < tilesY; ++ty)
            for (int tx = 0; tx < tilesX; ++tx)
                if (at(tx, ty) && touches(rect, tx, ty)) tiles.insert({tx, ty});
        return tiles;
    }
};

// The tiles the boxes cover, or false if a box is not tile aligned / clipped, or two boxes share a tile.
bool boxesToTiles(const Model& model, const std::vector<PixelRect>& boxes, std::set<std::pair<int, int>>& tiles) {
    for (const PixelRect& box : boxes) {
        if (box.empty() || box.x0 % kTile != 0 || box.y0 % kTile != 0) return false;
        if (box.x1 != std::min(((box.x1 + kTile - 1) / kTile) * kTile, model.width)) return false;
        if (box.y1 != std::min(((box.y1 + kTile - 1) / kTile) * kTile, model.height)) return false;
        for (int ty = box.y0 / kTile; ty * kTile < box.y1; ++ty)
            for (int tx = box.x0 / kTile; tx * kTile < box.x1; ++tx)
                if (!tiles.insert({tx, ty}).second) return false;
    }
    return true;
}

PixelRect randomRect(std::mt19937& rng, int width, int height) {
    std::uniform_int_distribution<int> px(-60, width + 60), py(-60, height + 60), size(-5, 300);
    const int x = px(rng), y = py(rng);
    return {x, y, x + size(rng), y + size(rng) / 2};
}

void compare(const char* label, const Model& model, const CompositeProjection& projection, std::mt19937& rng) {
    check(projection.staleTileCount() == static_cast<size_t>(model.count()), label, static_cast<int>(projection.staleTileCount()), model.count());
    check(projection.anyStale() == (model.count() > 0), "anyStale");
    for (int query = 0; query < 3; ++query) {
        const PixelRect rect = randomRect(rng, model.width, model.height);
        check(projection.expandToStale(rect) == model.expand(rect), "expandToStale", rect.x0, rect.y0);
        std::set<std::pair<int, int>> covered;
        const bool shaped = boxesToTiles(model, projection.staleRects(rect), covered);
        check(shaped, "staleRects boxes are tile aligned, clipped and disjoint", rect.x0, rect.y0);
        check(covered == model.staleTilesTouching(rect), "staleRects covers exactly the stale tiles the rect touches", rect.x0, rect.y0);
    }
}

void randomOperations(int width, int height, unsigned seed, int steps) {
    std::mt19937 rng(seed);
    CompositeProjection projection(width, height);
    Model model(width, height);
    compare("born stale", model, projection, rng);
    for (int step = 0; step < steps; ++step) {
        const int kind = static_cast<int>(rng() % 10);
        const PixelRect rect = randomRect(rng, width, height);
        if (kind == 0) {
            projection.markAllStale();
            std::fill(model.stale.begin(), model.stale.end(), static_cast<char>(1));
        } else if (kind <= 4) {
            projection.markStale(rect);
            model.markStale(rect);
        } else {
            // a fresh rectangle often covers whole tiles, so also try the whole canvas and tile-sized ones
            PixelRect fresh = rect;
            if (kind == 8) fresh = {0, 0, width, height};
            if (kind == 9) fresh = {static_cast<int>(rng() % 3) * kTile, 0, static_cast<int>(rng() % 3 + 1) * kTile + 5, height};
            projection.markFresh(fresh);
            model.markFresh(fresh);
        }
        compare("after an operation", model, projection, rng);
    }
}

void knownShapes() {
    // a stale canvas is one box; a canvas-wide rect that is only partly stale never reports a fresh tile
    CompositeProjection all(900, 700);
    check(all.staleRects({0, 0, 900, 700}).size() == 1, "a stale canvas is one box");
    check(all.staleRects({0, 0, 900, 700}).front() == PixelRect{0, 0, 900, 700}, "the box is clipped to the canvas");
    all.markFresh({0, 0, 900, 700});
    check(!all.anyStale() && all.staleRects({0, 0, 900, 700}).empty(), "fresh everywhere: no box");

    // a checkerboard has nothing to merge: one box per stale tile
    CompositeProjection board(5 * kTile, 4 * kTile);
    board.markFresh({0, 0, 5 * kTile, 4 * kTile});
    int expected = 0;
    for (int ty = 0; ty < 4; ++ty)
        for (int tx = 0; tx < 5; ++tx)
            if ((tx + ty) % 2 == 0) { board.markStale({tx * kTile, ty * kTile, (tx + 1) * kTile, (ty + 1) * kTile}); ++expected; }
    check(board.staleRects({0, 0, 5 * kTile, 4 * kTile}).size() == static_cast<size_t>(expected), "a checkerboard is one box per tile");

    // a stale column is one box, an L shape two
    CompositeProjection column(4 * kTile, 6 * kTile);
    column.markFresh({0, 0, 4 * kTile, 6 * kTile});
    column.markStale({kTile + 3, 0, kTile + 9, 6 * kTile});
    check(column.staleRects({0, 0, 4 * kTile, 6 * kTile}).size() == 1, "a stale column is one box");
    CompositeProjection shape(3 * kTile, 3 * kTile);
    shape.markFresh({0, 0, 3 * kTile, 3 * kTile});
    shape.markStale({0, 0, 5, 3 * kTile});
    shape.markStale({0, 2 * kTile, 3 * kTile, 3 * kTile});
    check(shape.staleRects({0, 0, 3 * kTile, 3 * kTile}).size() == 2, "an L shape is two boxes");

    // a tile only partly inside the fresh rectangle stays stale (a stale pixel shown is worse than redoing a tile)
    CompositeProjection partial(2 * kTile, kTile);
    partial.markFresh({0, 0, kTile + 50, kTile});
    check(partial.staleTileCount() == 1, "half of a tile fresh is not fresh");
    // the last tile of a canvas whose size is not a multiple of the tile is fresh when its clipped extent is covered
    CompositeProjection edge(kTile + 3, kTile);
    edge.markFresh({0, 0, kTile + 3, kTile});
    check(!edge.anyStale(), "the clipped edge tile is covered by a rect that ends at the canvas edge");
    // nothing to see outside the canvas
    CompositeProjection outside(kTile, kTile);
    outside.markFresh({0, 0, kTile, kTile});
    outside.markStale({kTile, 0, 3 * kTile, kTile});
    outside.markStale({-50, -50, 0, 0});
    outside.markStale({20, 20, 20, 90});
    check(!outside.anyStale(), "rectangles outside the canvas or without area mark nothing");
    check(outside.expandToStale({-9, -9, 4, 4}) == PixelRect{-9, -9, 4, 4}, "a rect outside the canvas expands to itself");
}

} // namespace

int main() {
    knownShapes();
    for (const auto& [w, h] : std::vector<std::pair<int, int>>{{1, 1}, {127, 129}, {128, 128}, {129, 127}, {300, 200}, {513, 257}, {1024, 1024}}) {
        randomOperations(w, h, static_cast<unsigned>(w * 31 + h), 600);
        std::printf("projection %dx%d: 600 random operations equal the model\n", w, h);
    }
    check(CompositeProjection{}.staleRects({0, 0, 10, 10}).empty() && !CompositeProjection{}.anyStale(), "a projection without canvas has nothing stale");
    const int compositorFailures = runCompositorStaleChecks();
    if (g_failures + compositorFailures > 0) {
        std::printf("composite projection checks: %d failures\n", g_failures + compositorFailures);
        return 1;
    }
    std::printf("composite projection checks: all equal\n");
    return 0;
}
