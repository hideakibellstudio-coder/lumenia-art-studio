// Isolated checks of the engine pieces the nine brush engines and the file format stand on, with no
// Python and no bridge (ARCcC 15.4, rule 5: a pillar that releases on its own).
//
//   footprint     DabFootprint visits exactly the pixels a brute-force scan of the grid finds inside the
//                 dab, for round and flattened, rotated tips, near and across the canvas edge
//   permission    PixelPermission: selection and clipping base scale or refuse a pixel
//   straight-over StraightOver: opaque paint covers, Alpha Lock keeps the alpha
//   tip           TipShape: solid core, falls off monotonically, 0 outside the dab
//   codec         TileGridCodec: a layer survives encode -> decode, and a malformed block is refused
//                 without touching the grid
//
// Prints one line per check and exits 1 on the first failure.
#include "engine/core/canvas/TileGrid.hpp"
#include "engine/core/canvas/TileGridCodec.hpp"
#include "engine/core/document/Layer.hpp"
#include "engine/core/raster/DabFootprint.hpp"
#include "engine/core/raster/PixelPermission.hpp"
#include "engine/core/raster/StraightOver.hpp"
#include "engine/core/raster/TipShape.hpp"
#include "engine/core/selection/SelectionMask.hpp"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <set>
#include <stdexcept>
#include <utility>
#include <vector>

namespace {

using namespace aladyn::engine;

int g_failures = 0;

void check(bool ok, const char* what) {
    if (!ok) {
        std::printf("FAIL: %s\n", what);
        ++g_failures;
    }
}

struct Lcg {
    uint64_t state;
    uint32_t next() {
        state = state * 6364136223846793005ULL + 1442695040888963407ULL;
        return static_cast<uint32_t>(state >> 33);
    }
    double unit() { return static_cast<double>(next()) / 4294967296.0; }
};

// -- footprint ---------------------------------------------------------------------------------

using Pixel = std::pair<int, int>;

// What the geometry says, written from the definition of a rotated ellipse and not from the code
// under test: a pixel centre is inside when its position, rotated by the angle and stretched by the
// aspect, lies within `reach + 1` of the dab centre.
bool insideByDefinition(const utils::Dab& dab, double reach, double aspect, int x, int y, double& slack) {
    const double dx = x + 0.5 - dab.position.x;
    const double dy = y + 0.5 - dab.position.y;
    const double angle = -dab.angle * (3.14159265358979323846 / 180.0);
    const double along = dx * std::cos(angle) - dy * std::sin(angle);
    const double across = (dx * std::sin(angle) + dy * std::cos(angle)) / aspect;
    const double limit = (reach + 1.0) * (reach + 1.0);
    const double distSq = along * along + across * across;
    slack = std::abs(distSq - limit);
    return distSq <= limit;
}

constexpr int kGridWidth = 300, kGridHeight = 200;

// Pixels the footprint of `dab` visits, inside the canvas, against what the definition of the
// ellipse says. Returns the number of pixels that disagree.
int footprintMismatches(const utils::Dab& dab, double aspect) {
    canvas::TileGrid grid(kGridWidth, kGridHeight);
    const raster::DabFootprint footprint(dab, dab.radius, aspect, grid);
    std::set<Pixel> visited;
    footprint.forEachPixel(1 << 30, [&](utils::ColorRGBA&, const raster::DabPixel& pixel) {
        if (pixel.gx < kGridWidth && pixel.gy < kGridHeight) visited.insert({pixel.gx, pixel.gy});
        return false;
    });

    int mismatches = 0;
    for (int y = 0; y < kGridHeight; ++y) {
        for (int x = 0; x < kGridWidth; ++x) {
            double slack = 0.0;
            const bool inside = insideByDefinition(dab, dab.radius, aspect, x, y, slack);
            if (inside != (visited.count({x, y}) == 1) && slack > 1e-6) ++mismatches;
        }
    }
    return mismatches;
}

void checkFootprint() {
    const double aspects[] = {1.0, 0.45, 0.2};
    const double angles[] = {0.0, 35.0, 90.0, -20.0};
    Lcg rng{7};
    int dabs = 0, mismatches = 0;
    for (int i = 0; i < 60; ++i) {
        utils::Dab dab;
        dab.position = {rng.unit() * (kGridWidth + 40) - 20, rng.unit() * (kGridHeight + 40) - 20};
        dab.radius = 1.0 + rng.unit() * 59.0;
        dab.angle = angles[(i / 3) % 4];
        mismatches += footprintMismatches(dab, aspects[i % 3]);
        ++dabs;
    }
    // A circle whose edge just reaches the neighbouring tile: culling the tile by a hair loses a sliver of pixels.
    for (const double touch : {0.90, 0.95, 0.99, 1.0, 1.02}) {
        for (const double radius : {10.0, 30.0, 60.0}) {
            for (const double aspect : {1.0, 0.45}) {
                utils::Dab dab;
                dab.radius = radius;
                dab.position = {128.0 - touch * radius, 64.0};
                mismatches += footprintMismatches(dab, aspect);
                dab.position = {64.0, 128.0 - touch * radius};
                mismatches += footprintMismatches(dab, aspect);
                dabs += 2;
            }
        }
    }
    check(mismatches == 0, "footprint visits exactly the pixels inside the dab");
    std::printf("footprint: %d dabs, %d mismatching pixels\n", dabs, mismatches);
}

// -- permission --------------------------------------------------------------------------------

void checkPermission() {
    selection::SelectionMask mask(64, 64);
    mask.selectAll();
    mask.setValue(10, 10, 0);
    mask.setValue(11, 10, 128);

    raster::PixelContext selectionOnly;
    selectionOnly.selectionMask = &mask;
    const raster::PixelPermission bySelection(selectionOnly);
    double strength = 1.0;
    check(!bySelection.apply(10, 10, strength), "a pixel outside the selection is refused");
    strength = 1.0;
    check(bySelection.apply(11, 10, strength) && std::abs(strength - 128.0 / 255.0) < 1e-12, "a half-selected pixel is scaled");
    strength = 0.5;
    check(bySelection.apply(12, 10, strength) && strength == 0.5, "a fully selected pixel is untouched");

    // Sem seleção nenhum pixel é recusado, mesmo com a máscara presente
    selection::SelectionMask empty(64, 64);
    raster::PixelContext noSelection;
    noSelection.selectionMask = &empty;
    strength = 1.0;
    check(raster::PixelPermission(noSelection).apply(5, 5, strength) && strength == 1.0, "an empty selection restricts nothing");

    document::Layer base("base", 256, 256);
    base.getTileGrid().getOrCreateTile(0, 0)->getBuffer().setPixel(3, 4, utils::ColorRGBA{9, 9, 9, 204});
    raster::PixelContext clipped;
    clipped.clipBaseLayer = &base;
    const raster::PixelPermission byBase(clipped);
    strength = 1.0;
    check(byBase.apply(3, 4, strength) && std::abs(strength - 204.0 / 255.0) < 1e-12, "the clipping base scales by its alpha");
    strength = 1.0;
    check(!byBase.apply(5, 5, strength), "no alpha under the base: refused");
    strength = 1.0;
    check(!byBase.apply(200, 200, strength), "no tile under the base: refused");
}

// -- straight over -----------------------------------------------------------------------------

void checkStraightOver() {
    utils::ColorRGBA dst{10, 20, 30, 200};
    check(raster::straightOver(dst, utils::ColorRGBA{250, 0, 0, 255}, 1.0, false) && dst.r == 250 && dst.g == 0 && dst.a == 255,
          "full strength covers what is under it");

    dst = utils::ColorRGBA{10, 20, 30, 200};
    check(raster::straightOver(dst, utils::ColorRGBA{250, 0, 0, 255}, 0.6, true) && dst.a == 200,
          "Alpha Lock keeps the alpha of the destination");

    dst = utils::ColorRGBA{10, 20, 30, 0};
    check(!raster::straightOver(dst, utils::ColorRGBA{250, 0, 0, 255}, 0.6, true) && dst.a == 0,
          "Alpha Lock does not paint on empty pixels");

    dst = utils::ColorRGBA{0, 0, 0, 0};
    check(raster::straightOver(dst, utils::ColorRGBA{100, 150, 200, 255}, 0.5, false) && dst.a == 127 &&
              std::abs(static_cast<int>(dst.r) - 100) <= 1 && std::abs(static_cast<int>(dst.b) - 200) <= 1,
          "paint on an empty pixel keeps the colour and takes the strength as alpha");
}

// -- tip shape ---------------------------------------------------------------------------------

void checkTipShape() {
    brush::BrushProfile profile;
    profile.hardness = 0.6;
    const double radius = 20.0;
    const raster::TipShape tip(profile, radius);

    auto at = [&](double distance) {
        raster::DabPixel pixel{0, 0, 0, 0, distance, 0.0, 0.0, distance * distance};
        return tip.alphaAt(pixel);
    };
    check(at(0.0) == 1.0 && at(radius * 0.5) == 1.0, "the core of the tip is solid");
    bool monotonic = true;
    double previous = 1.0;
    for (double distance = 0.0; distance <= radius + 2.0; distance += 0.05) {
        const double alpha = at(distance);
        if (alpha > previous + 1e-12 || alpha < 0.0 || alpha > 1.0) monotonic = false;
        previous = alpha;
    }
    check(monotonic, "the tip falls off monotonically between 0 and 1");
    check(at(radius + 0.5) == 0.0, "nothing outside the dab");
}

// -- codec -------------------------------------------------------------------------------------

canvas::TileGrid paintedGrid(int width, int height, uint64_t seed) {
    canvas::TileGrid grid(width, height);
    Lcg rng{seed};
    for (int ty = 0; ty < grid.getTilesCountY(); ++ty) {
        for (int tx = 0; tx < grid.getTilesCountX(); ++tx) {
            if (rng.next() % 3 == 0) continue;  // a hole: this tile was never painted
            canvas::PixelBuffer& buffer = grid.getOrCreateTile(tx, ty)->getBuffer();
            for (int i = 0; i < 400; ++i) {
                const int x = static_cast<int>(rng.next() % canvas::Tile::TILE_SIZE);
                const int y = static_cast<int>(rng.next() % canvas::Tile::TILE_SIZE);
                buffer.setPixel(x, y, utils::ColorRGBA{static_cast<uint8_t>(rng.next()), static_cast<uint8_t>(rng.next()),
                                                       static_cast<uint8_t>(rng.next()), static_cast<uint8_t>(1 + rng.next() % 255)});
            }
        }
    }
    return grid;
}

bool sameVisiblePixels(const canvas::TileGrid& a, const canvas::TileGrid& b) {
    for (int y = 0; y < a.getHeight(); ++y) {
        for (int x = 0; x < a.getWidth(); ++x) {
            const auto pa = const_cast<canvas::TileGrid&>(a).getTile(x / 128, y / 128);
            const auto pb = const_cast<canvas::TileGrid&>(b).getTile(x / 128, y / 128);
            const utils::ColorRGBA ca = pa ? pa->getBuffer().getPixel(x % 128, y % 128) : utils::ColorRGBA{0, 0, 0, 0};
            const utils::ColorRGBA cb = pb ? pb->getBuffer().getPixel(x % 128, y % 128) : utils::ColorRGBA{0, 0, 0, 0};
            if (ca.a == 0 && cb.a == 0) continue;
            if (ca.r != cb.r || ca.g != cb.g || ca.b != cb.b || ca.a != cb.a) return false;
        }
    }
    return true;
}

bool refuses(const std::vector<uint8_t>& blob, canvas::TileGrid& grid) {
    try {
        canvas::TileGridCodec::decode(blob.data(), blob.size(), grid);
    } catch (const std::invalid_argument&) {
        return true;
    }
    return false;
}

void checkCodec() {
    const canvas::TileGrid original = paintedGrid(300, 200, 11);
    const std::vector<uint8_t> blob = canvas::TileGridCodec::encode(original);

    canvas::TileGrid decoded(300, 200);
    canvas::TileGridCodec::decode(blob.data(), blob.size(), decoded);
    check(sameVisiblePixels(original, decoded), "a layer survives encode and decode pixel for pixel");

    canvas::TileGrid untouched = paintedGrid(300, 200, 99);
    const canvas::TileGrid reference = paintedGrid(300, 200, 99);

    std::vector<uint8_t> truncated(blob.begin(), blob.end() - 1);
    check(refuses(truncated, untouched) && sameVisiblePixels(untouched, reference), "a truncated block is refused and the grid is left alone");

    std::vector<uint8_t> badMagic = blob;
    badMagic[0] = 'X';
    check(refuses(badMagic, untouched) && sameVisiblePixels(untouched, reference), "a block with the wrong magic is refused");

    canvas::TileGrid other(256, 200);
    check(refuses(blob, other), "a block for another canvas size is refused");

    std::vector<uint8_t> trailing = blob;
    trailing.push_back(0);
    check(refuses(trailing, untouched), "bytes after the last record are refused");
}

}  // namespace

int main() {
    checkFootprint();
    checkPermission();
    checkStraightOver();
    checkTipShape();
    checkCodec();
    if (g_failures == 0) std::printf("dab core checks: all passed\n");
    return g_failures == 0 ? 0 : 1;
}
