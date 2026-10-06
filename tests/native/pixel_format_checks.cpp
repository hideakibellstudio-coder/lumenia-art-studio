// Checks the storage of a 16-bit pixel without Python: the channel conversion, the PixelBuffer, the Tile, the
// TileGrid and the layer block codec, in both pixel formats (S4).
//
//   1. conversion: every 8-bit value widens by x257 and narrows back to itself; every one of the 65536 16-bit values
//      narrows to the nearest 8-bit value (257 is odd: there are no ties); narrowing is monotonic;
//   2. buffer: fill (both colour types, uniform and not), the 8-bit view of a 16-bit pixel, the 16-bit view of an
//      8-bit one, size, reformat and resize keeping the format;
//   3. tile: a 16-bit tile is empty only when every 16-bit alpha is 0 (alpha 1 is not empty although it narrows to 0),
//      compresses and decompresses to the same bytes, and a read through an 8-bit scratch buffer adapts to the format;
//   4. grid: 16-bit tiles everywhere, copy-on-write copies adopt the source format, a resize with an offset equals the
//      same resize of two 8-bit grids holding the high and the low byte of every channel, prune keeps alpha 1,
//      adoptTile refuses a buffer of another format;
//   5. codec: both formats round trip, the 8-bit header says format 0 and the 16-bit one 1, the 16-bit alpha-1 tile is
//      stored, and a block of the wrong format, of an unknown format, truncated, or with a raw tile of the wrong
//      size is refused without touching the grid.
//
// Exit code is the failure count; the lines it prints are what tests/test_pixel_format_native.py asserts.
#include "engine/boundary/public-api/DecodedLayer.hpp"
#include "engine/core/canvas/CanvasLimits.hpp"
#include "engine/core/canvas/TileGrid.hpp"
#include "engine/core/canvas/TileGridCodec.hpp"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <memory>
#include <random>
#include <stdexcept>
#include <vector>

int runPixelFormatDocumentChecks();

namespace {

using namespace aladyn::engine;
using canvas::PixelBuffer;
using canvas::PixelFormat;
using canvas::Tile;
using canvas::TileGrid;
using utils::ColorRGBA;
using utils::ColorRGBA16;

int g_failures = 0;

void check(bool ok, const char* what, int a = 0, int b = 0) {
    if (ok) return;
    ++g_failures;
    std::printf("FAIL: %s (%d, %d)\n", what, a, b);
}

bool same(ColorRGBA16 a, ColorRGBA16 b) { return a.r == b.r && a.g == b.g && a.b == b.b && a.a == b.a; }
bool same(ColorRGBA a, ColorRGBA b) { return a.r == b.r && a.g == b.g && a.b == b.b && a.a == b.a; }

// Visible: alpha from 1, so no plane of the pixel is ever transparent.
ColorRGBA16 randomPixel(std::mt19937& rng) {
    return {static_cast<uint16_t>(rng()), static_cast<uint16_t>(rng()), static_cast<uint16_t>(rng()),
            static_cast<uint16_t>(1 + rng() % 65535)};
}

PixelBuffer& scratchFor(PixelFormat format) {
    static PixelBuffer scratch8(Tile::TILE_SIZE, Tile::TILE_SIZE, PixelFormat::RGBA8, ColorRGBA{0, 0, 0, 0});
    static PixelBuffer scratch16(Tile::TILE_SIZE, Tile::TILE_SIZE, PixelFormat::RGBA16, ColorRGBA{0, 0, 0, 0});
    return format == PixelFormat::RGBA16 ? scratch16 : scratch8;
}

// The pixel as 16-bit channels whatever the grid holds, read through the non-mutating view.
ColorRGBA16 pixelAt(TileGrid& grid, int x, int y) {
    if (x < 0 || y < 0 || x >= grid.getWidth() || y >= grid.getHeight()) return {0, 0, 0, 0};
    const Tile* tile = grid.getTile(x / Tile::TILE_SIZE, y / Tile::TILE_SIZE);
    if (!tile) return {0, 0, 0, 0};
    return tile->view(scratchFor(grid.getFormat())).getPixel16(x % Tile::TILE_SIZE, y % Tile::TILE_SIZE);
}

void fillTile(Tile& tile, std::mt19937& rng) {
    PixelBuffer& buffer = tile.getBuffer();
    for (int y = 0; y < Tile::TILE_SIZE; ++y)
        for (int x = 0; x < Tile::TILE_SIZE; ++x) buffer.setPixel16(x, y, randomPixel(rng));
}

// Smooth, so LZ4 shrinks it; with `alphaOne` only the alpha is 1 (the pixel narrows to transparent).
void fillSmooth(Tile& tile, bool alphaOne) {
    PixelBuffer& buffer = tile.getBuffer();
    for (int y = 0; y < Tile::TILE_SIZE; ++y)
        for (int x = 0; x < Tile::TILE_SIZE; ++x)
            buffer.setPixel16(x, y, {static_cast<uint16_t>(x * 300), static_cast<uint16_t>(y * 300), 4096, static_cast<uint16_t>(alphaOne ? 1 : 65535)});
}

void conversion() {
    for (int v = 0; v < 256; ++v) {
        const auto value = static_cast<uint8_t>(v);
        check(canvas::widenChannel(value) == v * 257, "widen is x257", v);
        check(canvas::narrowChannel(canvas::widenChannel(value)) == v, "narrow(widen(v)) == v", v);
    }
    int previous = 0;
    for (int w = 0; w < 65536; ++w) {
        const int narrowed = canvas::narrowChannel(static_cast<uint16_t>(w));
        check(narrowed == static_cast<int>(std::lround(w / 257.0)), "narrow is the nearest 8-bit value", w, narrowed);
        check(narrowed >= previous, "narrow is monotonic", w);
        previous = narrowed;
    }
    check(canvas::widenChannel(255) == 65535 && canvas::narrowChannel(65535) == 255 && canvas::narrowChannel(0) == 0, "the ends map to the ends");
    std::mt19937 rng(7);
    for (int i = 0; i < 100000; ++i) {
        const ColorRGBA c{static_cast<uint8_t>(rng()), static_cast<uint8_t>(rng()), static_cast<uint8_t>(rng()), static_cast<uint8_t>(rng())};
        check(same(canvas::narrow(canvas::widen(c)), c), "a colour survives widen then narrow", i);
    }
    check(canvas::bytesPerPixel(PixelFormat::RGBA8) == 4 && canvas::bytesPerPixel(PixelFormat::RGBA16) == 8 &&
          sizeof(ColorRGBA16) == 8 && Tile::bytesFor(PixelFormat::RGBA8) == Tile::TILE_BYTES &&
          Tile::bytesFor(PixelFormat::RGBA16) == 2 * Tile::TILE_BYTES, "sizes");
    check(canvas::isPixelFormatId(0) && canvas::isPixelFormatId(1) && !canvas::isPixelFormatId(2) && !canvas::isPixelFormatId(0xFFFFFFFFu), "format ids");
    check(canvas::maxCanvasDimension(PixelFormat::RGBA8) == 16384 && canvas::maxCanvasDimension(PixelFormat::RGBA16) == 8192, "canvas limits per format");
    bool refused = false;
    try { canvas::checkedCanvasDimension(8193, PixelFormat::RGBA16); } catch (const std::invalid_argument&) { refused = true; }
    check(refused && canvas::checkedCanvasDimension(8192, PixelFormat::RGBA16) == 8192 && canvas::checkedCanvasDimension(16384) == 16384, "8193 px is refused in 16 bits only");
    std::printf("conversion: 256 widen/narrow, 65536 narrow, 100000 colours, sizes and limits\n");
}

void buffer() {
    std::mt19937 rng(11);
    for (const auto& [w, h] : std::vector<std::pair<int, int>>{{1, 1}, {2, 1}, {3, 1}, {7, 3}, {37, 5}, {100, 1}}) {
        for (const PixelFormat format : {PixelFormat::RGBA8, PixelFormat::RGBA16}) {
            PixelBuffer buf(w, h, format, ColorRGBA{0, 0, 0, 0});
            check(buf.getSizeInBytes() == static_cast<size_t>(w) * h * canvas::bytesPerPixel(format) && buf.getFormat() == format, "buffer size", w, h);
            const ColorRGBA c{static_cast<uint8_t>(rng()), static_cast<uint8_t>(rng()), static_cast<uint8_t>(rng()), static_cast<uint8_t>(rng())};
            const ColorRGBA16 wide = randomPixel(rng);
            buf.fill(c);
            bool ok = true;
            for (int y = 0; y < h; ++y)
                for (int x = 0; x < w; ++x)
                    ok = ok && same(buf.getPixel(x, y), c) && same(buf.getPixel16(x, y), canvas::widen(c));
            check(ok, "fill with an 8-bit colour reads back in both views", w, h);
            buf.fill(wide);
            ok = true;
            for (int y = 0; y < h; ++y)
                for (int x = 0; x < w; ++x)
                    ok = ok && same(buf.getPixel16(x, y), format == PixelFormat::RGBA16 ? wide : canvas::widen(canvas::narrow(wide)));
            check(ok, "fill with a 16-bit colour (narrowed in an 8-bit buffer)", w, h);
        }
    }
    PixelBuffer uniform(9, 9, PixelFormat::RGBA16, ColorRGBA{0, 0, 0, 0});
    uniform.fill(ColorRGBA16{0x2222, 0x2222, 0x2222, 0x2222});
    bool bytesEqual = true;
    for (size_t i = 0; i < uniform.getSizeInBytes(); ++i) bytesEqual = bytesEqual && uniform.getData()[i] == 0x22;
    check(bytesEqual, "a uniform 16-bit colour fills by byte");
    PixelBuffer b16(4, 4, PixelFormat::RGBA16, ColorRGBA{0, 0, 0, 0});
    b16.setPixel16(1, 2, {65535, 1, 300, 40000});
    check(same(b16.getPixel16(1, 2), ColorRGBA16{65535, 1, 300, 40000}) && same(b16.getPixel(1, 2), ColorRGBA{255, 0, 1, 156}), "set16 / get16 / the 8-bit view");
    b16.setPixel16(-1, 0, {1, 1, 1, 1});
    b16.setPixel16(4, 4, {1, 1, 1, 1});
    check(same(b16.getPixel16(9, 9), ColorRGBA16{0, 0, 0, 0}), "reads outside are transparent");
    b16.resize(6, 2);
    check(b16.getFormat() == PixelFormat::RGBA16 && b16.getSizeInBytes() == 6 * 2 * 8, "resize keeps the format");
    b16.reformat(PixelFormat::RGBA8);
    check(b16.getFormat() == PixelFormat::RGBA8 && b16.getSizeInBytes() == 6 * 2 * 4, "reformat resizes to the new format");
    PixelBuffer b8(3, 3, ColorRGBA{9, 8, 7, 6});
    b8.setPixel16(1, 1, {65535, 65535, 65535, 65535});
    check(same(b8.getPixel(1, 1), ColorRGBA{255, 255, 255, 255}) && same(b8.getPixel(0, 0), ColorRGBA{9, 8, 7, 6}), "an 8-bit buffer narrows what set16 gives it");
    std::printf("buffer: fill, views, size, reformat and resize in both formats\n");
}

void tile() {
    std::mt19937 rng(21);
    Tile t(2, 3, PixelFormat::RGBA16);
    check(t.getFormat() == PixelFormat::RGBA16 && t.getBuffer().getFormat() == PixelFormat::RGBA16 &&
          t.getBuffer().getSizeInBytes() == Tile::bytesFor(PixelFormat::RGBA16), "a 16-bit tile has a 16-bit buffer");
    check(t.isEmpty(), "a new tile is empty");
    t.getBuffer().setPixel16(5, 6, {100, 200, 300, 1});
    check(!t.isEmpty(), "alpha 1 in 16 bits is not empty (it narrows to 0)");
    t.getBuffer().setPixel16(5, 6, {100, 200, 300, 0});
    check(t.isEmpty(), "colour under alpha 0 is empty");
    fillSmooth(t, false);
    const std::vector<uint8_t> smooth(t.getBuffer().getData(), t.getBuffer().getData() + Tile::bytesFor(PixelFormat::RGBA16));
    check(t.compress() && t.isCompressed(), "a smooth 16-bit tile compresses");
    PixelBuffer& scratch = scratchFor(PixelFormat::RGBA8);
    const PixelBuffer& viewed = t.view(scratch);
    check(viewed.getFormat() == PixelFormat::RGBA16 && t.isCompressed() &&
          std::memcmp(viewed.getData(), smooth.data(), smooth.size()) == 0, "view through an 8-bit scratch adapts and leaves the tile compressed");
    check(t.decompress() && !t.isCompressed() && std::memcmp(t.getBuffer().getData(), smooth.data(), smooth.size()) == 0, "decompress restores the bytes");
    Tile noise(0, 0, PixelFormat::RGBA16);
    fillTile(noise, rng);
    const std::vector<uint8_t> noisy(noise.getBuffer().getData(), noise.getBuffer().getData() + Tile::bytesFor(PixelFormat::RGBA16));
    if (noise.compress()) check(noise.decompress() && std::memcmp(noise.getBuffer().getData(), noisy.data(), noisy.size()) == 0, "noise survives compression");
    Tile tile8(1, 1);
    fillSmooth(tile8, false);
    PixelBuffer wide(Tile::TILE_SIZE, Tile::TILE_SIZE, PixelFormat::RGBA16, ColorRGBA{0, 0, 0, 0});
    check(tile8.compress() && tile8.view(wide).getFormat() == PixelFormat::RGBA8, "an 8-bit tile read through a 16-bit scratch adapts the other way");
    Tile shared(0, 0, std::make_shared<PixelBuffer>(Tile::TILE_SIZE, Tile::TILE_SIZE, PixelFormat::RGBA16, ColorRGBA{0, 0, 0, 0}));
    check(shared.getFormat() == PixelFormat::RGBA16, "a tile built on a shared buffer takes its format");
    const uint8_t* zero = canvas::zeroTileData();
    bool zeros = true;
    for (size_t i = 0; i < Tile::bytesFor(PixelFormat::RGBA16); ++i) zeros = zeros && zero[i] == 0;
    check(zeros, "zeroTileData covers the largest tile");
    std::printf("tile: 16-bit emptiness, compression, adaptive view and shared buffer checked\n");
}

// Mirrors a 16-bit grid into two 8-bit grids: the high bytes and the low bytes of every channel.
void split(TileGrid& wide, TileGrid& high, TileGrid& low) {
    wide.forEachTile([&](const auto& idx, Tile& source) {
        Tile* h = high.getOrCreateTile(idx.x, idx.y);
        Tile* l = low.getOrCreateTile(idx.x, idx.y);
        for (int y = 0; y < Tile::TILE_SIZE; ++y)
            for (int x = 0; x < Tile::TILE_SIZE; ++x) {
                const ColorRGBA16 p = source.getBuffer().getPixel16(x, y);
                h->getBuffer().setPixel(x, y, {static_cast<uint8_t>(p.r >> 8), static_cast<uint8_t>(p.g >> 8), static_cast<uint8_t>(p.b >> 8), static_cast<uint8_t>(p.a >> 8)});
                l->getBuffer().setPixel(x, y, {static_cast<uint8_t>(p.r), static_cast<uint8_t>(p.g), static_cast<uint8_t>(p.b), static_cast<uint8_t>(p.a)});
            }
    });
}

int differences(TileGrid& wide, TileGrid& high, TileGrid& low) {
    int bad = 0;
    for (int y = 0; y < wide.getHeight(); ++y)
        for (int x = 0; x < wide.getWidth(); ++x) {
            const ColorRGBA16 p = pixelAt(wide, x, y);
            const ColorRGBA16 h = pixelAt(high, x, y), l = pixelAt(low, x, y);
            const auto join = [](uint16_t hi, uint16_t lo) { return static_cast<uint16_t>(((hi & 255) << 8) | (lo & 255)); };
            // 8-bit grids give 16-bit views widened (x257): take the 8-bit value back out.
            const auto byte = [](uint16_t v) { return static_cast<uint16_t>(canvas::narrowChannel(v)); };
            const ColorRGBA16 expected{join(byte(h.r), byte(l.r)), join(byte(h.g), byte(l.g)), join(byte(h.b), byte(l.b)), join(byte(h.a), byte(l.a))};
            bad += same(p, expected) ? 0 : 1;
        }
    return bad;
}

void grid() {
    std::mt19937 rng(31);
    TileGrid g(300, 200, PixelFormat::RGBA16);
    for (const auto& [tx, ty] : std::vector<std::pair<int, int>>{{0, 0}, {1, 1}, {2, 0}, {2, 1}}) {
        Tile* t = g.getOrCreateTile(tx, ty);
        check(t && t->getFormat() == PixelFormat::RGBA16, "a 16-bit grid creates 16-bit tiles", tx, ty);
        if (t) fillTile(*t, rng);
    }
    check(g.getTileDataSize() == Tile::bytesFor(PixelFormat::RGBA16) && g.getTile(1, 0) == nullptr, "tile data size by format");
    TileGrid copy(300, 200);
    copy.copyFrom(g);
    check(copy.getFormat() == PixelFormat::RGBA16 && copy.getCowSharedTilesCount() == 4, "a copy adopts the source format and shares its buffers");
    const ColorRGBA16 before = pixelAt(g, 130, 140);
    copy.getTile(1, 1)->getBuffer().setPixel16(2, 12, {1, 2, 3, 4});
    check(same(pixelAt(g, 130, 140), before) && same(pixelAt(copy, 130, 140), ColorRGBA16{1, 2, 3, 4}), "writing the copy leaves the source alone");
    // Differential: the same resize on the 16-bit grid and on its two byte planes.
    for (const auto& r : std::vector<std::vector<int>>{{500, 130, 17, -9}, {260, 300, -130, 70}, {129, 129, 0, 0}, {300, 200, 5, 5}, {64, 64, -250, -150}}) {
        TileGrid wide(300, 200, PixelFormat::RGBA16), high(300, 200), low(300, 200);
        for (const auto& [tx, ty] : std::vector<std::pair<int, int>>{{0, 0}, {1, 0}, {2, 1}, {1, 1}}) fillTile(*wide.getOrCreateTile(tx, ty), rng);
        split(wide, high, low);
        wide.getTile(1, 0)->compress();  // one tile read from its compressed form during the resize
        wide.resizePreserve(r[0], r[1], r[2], r[3]);
        high.resizePreserve(r[0], r[1], r[2], r[3]);
        low.resizePreserve(r[0], r[1], r[2], r[3]);
        check(differences(wide, high, low) == 0 && wide.getFormat() == PixelFormat::RGBA16, "resizePreserve of a 16-bit grid equals the same resize of its byte planes", r[0], r[1]);
    }
    TileGrid pruned(256, 128, PixelFormat::RGBA16);
    pruned.getOrCreateTile(0, 0)->getBuffer().setPixel16(3, 3, {9, 9, 9, 1});
    pruned.getOrCreateTile(1, 0)->getBuffer().setPixel16(3, 3, {9, 9, 9, 0});
    check(pruned.pruneEmptyTiles() == 1 && pruned.getTile(0, 0) != nullptr && pruned.getTile(1, 0) == nullptr, "prune keeps a tile whose only content is alpha 1");
    TileGrid host(256, 128, PixelFormat::RGBA16);
    auto wideBuffer = std::make_shared<PixelBuffer>(Tile::TILE_SIZE, Tile::TILE_SIZE, PixelFormat::RGBA16, ColorRGBA{0, 0, 0, 0});
    auto narrowBuffer = std::make_shared<PixelBuffer>(Tile::TILE_SIZE, Tile::TILE_SIZE, PixelFormat::RGBA8, ColorRGBA{0, 0, 0, 0});
    check(host.adoptTile(0, 0, wideBuffer) != nullptr && host.adoptTile(1, 0, narrowBuffer) == nullptr && host.adoptTile(5, 5, wideBuffer) == nullptr &&
          host.adoptTile(1, 0, nullptr) == nullptr && host.getActiveTilesCount() == 1, "adoptTile takes only a buffer of the grid's format");
    std::printf("grid: 16-bit tiles, copy-on-write copy, 5 resizes equal their byte planes, prune and adoptTile checked\n");
}

std::vector<uint8_t> blockOf(TileGrid& g) { return canvas::TileGridCodec::encode(g); }

bool refuses(const std::vector<uint8_t>& blob, TileGrid& target) {
    try { canvas::TileGridCodec::decode(blob.data(), blob.size(), target); } catch (const std::invalid_argument&) { return true; }
    return false;
}

void codec() {
    std::mt19937 rng(41);
    for (const PixelFormat format : {PixelFormat::RGBA8, PixelFormat::RGBA16}) {
        TileGrid g(300, 200, format);
        const bool wide = format == PixelFormat::RGBA16;
        fillTile(*g.getOrCreateTile(0, 0), rng);          // noise: stored raw
        fillSmooth(*g.getOrCreateTile(1, 0), false);       // smooth: LZ4
        g.getOrCreateTile(2, 1)->getBuffer().setPixel16(1, 1, {5, 6, 7, 0});  // colour under alpha 0: a hole
        if (wide) g.getOrCreateTile(0, 1)->getBuffer().setPixel16(9, 9, {0, 0, 0, 1});  // only alpha 1: stored
        const auto blob = blockOf(g);
        uint32_t id = 99, count = 0;
        std::memcpy(&id, blob.data() + 20, 4);
        std::memcpy(&count, blob.data() + 16, 4);
        check(id == (wide ? 1u : 0u) && canvas::TileGridCodec::peekFormat(blob.data(), blob.size()) == format, "the header names the format", wide);
        check(count == (wide ? 3u : 2u), "only tiles with a visible pixel are stored", static_cast<int>(count), wide);
        TileGrid back(300, 200, format);
        canvas::TileGridCodec::decode(blob.data(), blob.size(), back);
        bool equal = back.getActiveTilesCount() == count;
        for (int y = 0; y < 200; ++y)
            for (int x = 0; x < 300; ++x) {
                const ColorRGBA16 want = pixelAt(g, x, y), got = pixelAt(back, x, y);
                equal = equal && (want.a == 0 ? got.a == 0 : same(want, got));
            }
        check(equal, "a block round trips every visible pixel", wide);
        if (wide) {
            TileGrid eight(300, 200);
            const auto before = eight.getActiveTilesCount();
            check(refuses(blob, eight) && eight.getActiveTilesCount() == before, "an 8-bit grid refuses a 16-bit block and stays as it was");
            auto bad = blob;
            bad[20] = 2;
            TileGrid any(300, 200, format);
            bool peeked = false;
            try { (void)canvas::TileGridCodec::peekFormat(bad.data(), bad.size()); } catch (const std::invalid_argument&) { peeked = true; }
            check(peeked && refuses(bad, any), "an unknown pixel format is refused");
            auto cut = blob;
            cut.resize(cut.size() - 3);
            TileGrid target(300, 200, format);
            fillTile(*target.getOrCreateTile(0, 0), rng);
            const ColorRGBA16 keep = pixelAt(target, 3, 3);
            check(refuses(cut, target) && same(pixelAt(target, 3, 3), keep), "a truncated 16-bit block leaves the grid alone");
            // A raw tile of 8-bit size inside a 16-bit block.
            std::vector<uint8_t> raw8(blob.begin(), blob.begin() + 24);
            const uint32_t one = 1, stored = Tile::TILE_BYTES;
            std::memcpy(raw8.data() + 16, &one, 4);
            raw8.insert(raw8.end(), 12, uint8_t{0});
            std::memcpy(raw8.data() + 24 + 8, &stored, 4);
            raw8.resize(24 + 12 + Tile::TILE_BYTES, 7);
            TileGrid shortTile(300, 200, format);
            check(refuses(raw8, shortTile) && shortTile.getActiveTilesCount() == 0, "a raw tile of 8-bit size in a 16-bit block is refused");
        } else {
            TileGrid sixteen(300, 200, PixelFormat::RGBA16);
            check(refuses(blob, sixteen), "a 16-bit grid refuses an 8-bit block");
        }
        std::printf("codec %s: header, round trip and refusals checked\n", canvas::pixelFormatName(format));
    }
    TileGrid tile16(128, 128, PixelFormat::RGBA16);
    fillSmooth(*tile16.getOrCreateTile(0, 0), false);
    auto blob16 = blockOf(tile16);
    TileGrid small8(128, 128);
    fillSmooth(*small8.getOrCreateTile(0, 0), false);
    auto blob8 = blockOf(small8);
    const uint32_t width = 9000;
    std::memcpy(blob16.data() + 8, &width, 4);
    std::memcpy(blob8.data() + 8, &width, 4);
    TileGrid wide16(9000, 128, PixelFormat::RGBA16), wide8(9000, 128);
    bool decoded8 = true;
    try { canvas::TileGridCodec::decode(blob8.data(), blob8.size(), wide8); } catch (const std::invalid_argument&) { decoded8 = false; }
    check(refuses(blob16, wide16) && decoded8, "9000 px is refused in a 16-bit block and read in an 8-bit one");
    bool layerRefused = false;
    try { boundary::DecodedLayer(9000, 128, blob16.data(), blob16.size()); } catch (const std::invalid_argument&) { layerRefused = true; }
    auto ok16 = blockOf(tile16);
    boundary::DecodedLayer layer(128, 128, ok16.data(), ok16.size());
    check(layerRefused && layer.pixelFormat() == PixelFormat::RGBA16 && layer.take().getFormat() == PixelFormat::RGBA16, "a decoded layer carries its block's format");
    std::printf("codec: canvas limits per format and the decoded layer checked\n");
}

} // namespace

int main() {
    conversion();
    buffer();
    tile();
    grid();
    codec();
    const int documentFailures = runPixelFormatDocumentChecks();
    if (g_failures + documentFailures > 0) {
        std::printf("pixel format checks: %d failures\n", g_failures + documentFailures);
        return 1;
    }
    std::printf("pixel format checks: all equal\n");
    return 0;
}
