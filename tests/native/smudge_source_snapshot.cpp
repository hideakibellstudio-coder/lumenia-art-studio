// The smudge deposit must depend only on the grid as it was BEFORE the dab (D15).
//
// SmudgeEngine::renderDab samples a trail pixel for every pixel it writes. Reading
// the live grid means the pixels an earlier tile of the same dab already wrote feed
// the samples of a later tile, so the result depends on the order the tiles are
// visited, that is, on where the tile seams happen to fall.
//
// The dab is translation-invariant (every position below is exact in binary), so the
// same scene shifted by a whole number of pixels must give the same pixels. Shifting
// by 64 px moves every seam; with live reads the two scenes differ.
#include "engine/core/brush/BrushProfile.hpp"
#include "engine/core/canvas/CanvasTexture.hpp"
#include "engine/core/canvas/TileGrid.hpp"
#include "engine/core/engines/SmudgeEngine.hpp"

#include <cstdio>
#include <vector>

using namespace aladyn::engine;

namespace {

constexpr int kWidth = 512;
constexpr int kHeight = 256;
constexpr int kSceneWidth = 220;  // columns of the scene, before the shift
constexpr int kShift = 64;        // half a tile: every seam moves

utils::ColorRGBA scenePixel(int x, int y) {
    // Four colour stripes of different widths with a vertical gradient: every pixel the
    // dab reads has a different neighbour on each side.
    static const utils::ColorRGBA stripes[4] = {
        {220, 40, 40, 255}, {40, 80, 220, 255}, {230, 200, 40, 255}, {60, 200, 90, 255}};
    const int band = (x / 37 + y / 53) % 4;
    utils::ColorRGBA c = stripes[band];
    c.a = static_cast<uint8_t>(160 + (y % 96));
    return c;
}

void writePixel(canvas::TileGrid& grid, int x, int y, utils::ColorRGBA color) {
    canvas::Tile* tile = grid.getOrCreateTile(x / canvas::Tile::TILE_SIZE, y / canvas::Tile::TILE_SIZE);
    tile->getBuffer().setPixel(x % canvas::Tile::TILE_SIZE, y % canvas::Tile::TILE_SIZE, color);
}

utils::ColorRGBA readPixel(canvas::TileGrid& grid, int x, int y) {
    canvas::Tile* tile = grid.getTile(x / canvas::Tile::TILE_SIZE, y / canvas::Tile::TILE_SIZE);
    return tile ? tile->getBuffer().getPixel(x % canvas::Tile::TILE_SIZE, y % canvas::Tile::TILE_SIZE)
                : utils::ColorRGBA{0, 0, 0, 0};
}

// Paints the scene shifted by `shift`, runs six dabs of the smudge engine along a
// diagonal (`direction` picks which), and returns the whole grid.
std::vector<utils::ColorRGBA> run(int shift, int direction) {
    canvas::TileGrid grid(kWidth, kHeight);
    for (int y = 30; y < 220; ++y)
        for (int x = 0; x < kSceneWidth; ++x)
            writePixel(grid, x + shift, y, scenePixel(x, y));

    brush::BrushProfile profile;
    profile.hardness = 0.5;
    profile.tip.aspectRatio = 1.0;
    profile.smudgeParams.colorPickup = 1.0;
    profile.smudgeParams.mixRatio = 1.0;
    profile.smudgeParams.smudgeStretch = 1.0;

    canvas::CanvasTexture texture;
    engines::SmudgeEngine engine;
    for (int step = 0; step < 6; ++step) {
        utils::Dab dab;
        // direction +1 moves down-right, -1 up-right: the trail sample lies behind the
        // movement, and which side of a tile seam it falls on decides if it was already written.
        dab.position = {96.25 + shift + step * 12.5, 140.25 + direction * step * 8.5};
        dab.radius = 40.0;
        dab.opacity = 1.0;
        engine.renderDab(dab, profile, texture, grid);
    }

    std::vector<utils::ColorRGBA> out;
    out.reserve(static_cast<size_t>(kWidth) * kHeight);
    for (int y = 0; y < kHeight; ++y)
        for (int x = 0; x < kWidth; ++x)
            out.push_back(readPixel(grid, x, y));
    return out;
}

bool same(utils::ColorRGBA a, utils::ColorRGBA b) { return a.r == b.r && a.g == b.g && a.b == b.b && a.a == b.a; }


// One direction: deterministic, the dabs do something, and the shifted scene matches.
int check(int direction) {
    const auto reference = run(0, direction);
    const auto again = run(0, direction);
    for (size_t i = 0; i < reference.size(); ++i) {
        if (!same(reference[i], again[i])) {
            std::printf("direction %d: not deterministic, pixel %zu changed between two identical runs\n", direction, i);
            return 2;
        }
    }

    // The dabs must have done something, or the comparison below proves nothing.
    int touched = 0;
    for (int y = 30; y < 220; ++y)
        for (int x = 0; x < kSceneWidth; ++x)
            touched += !same(reference[static_cast<size_t>(y) * kWidth + x], scenePixel(x, y));
    if (touched < 500) {
        std::printf("direction %d: the smudge dabs changed only %d pixels, the scenario tests nothing\n", direction, touched);
        return 3;
    }

    const auto shifted = run(kShift, direction);
    int different = 0, first_x = -1, first_y = -1;
    for (int y = 0; y < kHeight; ++y) {
        for (int x = 0; x < kSceneWidth + 80; ++x) {
            if (!same(reference[static_cast<size_t>(y) * kWidth + x],
                      shifted[static_cast<size_t>(y) * kWidth + x + kShift])) {
                if (different == 0) { first_x = x; first_y = y; }
                ++different;
            }
        }
    }
    if (different > 0) {
        std::printf("direction %d: the result depends on where the tile seams fall: %d pixels differ "
                    "(first at x=%d y=%d) after shifting the scene by %d px\n",
                    direction, different, first_x, first_y, kShift);
        return 1;
    }
    std::printf("direction %d: order independent, %d pixels changed by the dabs, 0 differ after the shift\n",
                direction, touched);
    return 0;
}

} // namespace

int main() {
    const int down = check(+1);
    const int up = check(-1);
    return down != 0 ? down : up;
}
