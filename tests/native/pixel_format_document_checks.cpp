// Checks that the pixel format of a document reaches its layers and its history, and that nothing 8-bit reads a
// 16-bit layer by mistake, without Python (S4). Linked into the executable of pixel_format_checks.cpp.
//
//   1. layers: every layer a 16-bit LayerStack creates (background, layer, group, filter layer, duplicate), copies
//      (copy constructor) or resizes is 16-bit, `swap` and `restore` carry the format; an 8-bit stack keeps making
//      8-bit layers;
//   2. tile history: a step on a 16-bit layer (a tile that did not exist, then a tile that did) undoes and redoes to
//      the exact bytes; a step recorded with an 8-bit sized "before" on a 16-bit layer cannot be undone, and says so
//      instead of writing half a tile (the stroke code still records 8-bit zero arrays until S6);
//   3. structure history: undoing and redoing a structural step on a 16-bit stack keeps the format and the pixels;
//   4. guards: each compositor refuses a layer of the other format (and a 16-bit output buffer), and the merge refuses
//      a stack whose layers disagree on the format.
#include "engine/core/document/Compositor.hpp"
#include "engine/core/document/FilterLayer.hpp"
#include "engine/core/document/LayerMerger.hpp"
#include "engine/core/document/LayerStack.hpp"
#include "engine/core/history/TileUndoManager.hpp"
#include "engine/core/selection/SelectionMask.hpp"

#include <cstdio>
#include <cstring>
#include <random>
#include <stdexcept>
#include <vector>

namespace {

using namespace aladyn::engine;
using canvas::PixelFormat;
using canvas::Tile;
using utils::ColorRGBA;
using utils::ColorRGBA16;

int g_failures = 0;

void check(bool ok, const char* what, int a = 0, int b = 0) {
    if (ok) return;
    ++g_failures;
    std::printf("FAIL: %s (%d, %d)\n", what, a, b);
}

void fillRandom(Tile& tile, std::mt19937& rng) {
    canvas::PixelBuffer& buffer = tile.getBuffer();
    for (int y = 0; y < Tile::TILE_SIZE; ++y)
        for (int x = 0; x < Tile::TILE_SIZE; ++x)
            buffer.setPixel16(x, y, {static_cast<uint16_t>(rng()), static_cast<uint16_t>(rng()), static_cast<uint16_t>(rng()), static_cast<uint16_t>(1 + rng() % 65535)});
}

std::vector<uint8_t> bytesOf(document::LayerStack& stack, int layer, int tx, int ty) {
    auto& grid = stack.getDrawingLayer(layer)->getTileGrid();
    const size_t bytes = Tile::bytesFor(grid.getFormat());
    const Tile* tile = grid.getTile(tx, ty);
    if (!tile) return std::vector<uint8_t>(bytes, 0);
    const uint8_t* data = tile->getBuffer().getData();
    return std::vector<uint8_t>(data, data + bytes);
}

bool allLayers(document::LayerStack& stack, PixelFormat format) {
    for (size_t i = 0; i < stack.getDrawingLayerCount(); ++i)
        if (stack.getDrawingLayer(static_cast<int>(i))->getTileGrid().getFormat() != format) return false;
    return stack.getPixelFormat() == format;
}

void layers() {
    document::LayerStack stack(300, 200, PixelFormat::RGBA16);
    const int painted = stack.addLayer("a");
    stack.addGroup("g");
    stack.addFilterLayer("f", document::filters::FilterType::GaussianBlur);
    stack.duplicateLayer(painted);
    check(stack.getDrawingLayerCount() == 5 && allLayers(stack, PixelFormat::RGBA16), "every layer of a 16-bit stack is 16-bit");
    document::LayerStack copy(stack);
    check(allLayers(copy, PixelFormat::RGBA16), "a copy of a 16-bit stack is 16-bit");
    stack.resize(400, 250);
    check(allLayers(stack, PixelFormat::RGBA16) && stack.getWidth() == 400, "resize keeps the format");
    document::LayerStack eight(300, 200);
    eight.addLayer("a");
    eight.addGroup("g");
    check(allLayers(eight, PixelFormat::RGBA8), "an 8-bit stack keeps making 8-bit layers");
    document::LayerStack small16(64, 64, PixelFormat::RGBA16), small8(64, 64);
    small16.swap(small8);
    check(small16.getPixelFormat() == PixelFormat::RGBA8 && small8.getPixelFormat() == PixelFormat::RGBA16 &&
          allLayers(small16, PixelFormat::RGBA8) && allLayers(small8, PixelFormat::RGBA16), "swap exchanges the format with the layers");
    small8.restore(small16);
    check(allLayers(small8, PixelFormat::RGBA8), "restore takes the format of the stack it copies");
    std::printf("layers: background, layer, group, filter, duplicate, copy and resize follow the stack's format\n");
}

void tileHistory() {
    std::mt19937 rng(51);
    document::LayerStack stack(256, 128, PixelFormat::RGBA16);
    selection::SelectionMask selection(256, 128);
    history::TileUndoManager history(50, 64, false);
    const int layer = stack.addLayer("paint");
    stack.selectLayer(layer);
    auto& grid = stack.getDrawingLayer(layer)->getTileGrid();
    const size_t bytes = Tile::bytesFor(PixelFormat::RGBA16);
    const auto zeros = std::vector<uint8_t>(bytes, 0);

    // A tile that was recorded and never created is not a change: the "before" is zeros, and so is what is there now.
    history.beginStep("recorded, never painted");
    history.recordTileBefore(layer, 1, 0, canvas::zeroTileData(), bytes);
    history.commitStep(stack);
    check(history.undoId() == 0, "a recorded tile that never existed is not a step");

    history.beginStep("new tile");
    history.recordTileBefore(layer, 0, 0, canvas::zeroTileData(), bytes);
    fillRandom(*grid.getOrCreateTile(0, 0), rng);
    history.commitStep(stack);
    const auto first = bytesOf(stack, layer, 0, 0);

    history.beginStep("existing tile");
    history.recordTileBefore(layer, 0, 0, grid.getTile(0, 0)->getBuffer().getData(), bytes);
    for (int i = 0; i < 40; ++i) grid.getTile(0, 0)->getBuffer().setPixel16(i, 3, {static_cast<uint16_t>(rng()), 0, 7, 65535});
    history.commitStep(stack);
    const auto second = bytesOf(stack, layer, 0, 0);
    check(first != second && first != zeros, "the fixture changed the tile");

    check(history.undo(stack, selection) && bytesOf(stack, layer, 0, 0) == first, "undo restores the exact bytes of a 16-bit tile");
    check(history.undo(stack, selection) && bytesOf(stack, layer, 0, 0) == zeros, "undo of a tile that did not exist restores zeros of a 16-bit tile");
    check(history.redo(stack, selection) && bytesOf(stack, layer, 0, 0) == first, "redo brings the first step back");
    check(history.redo(stack, selection) && bytesOf(stack, layer, 0, 0) == second, "redo brings the second step back");

    // The stroke code records a 64 KiB "before" for a tile that did not exist, whatever the format (until S6).
    const auto small = std::vector<uint8_t>(Tile::TILE_BYTES, 0);
    history.beginStep("8-bit sized before");
    history.recordTileBefore(layer, 1, 0, small.data(), small.size());
    fillRandom(*grid.getOrCreateTile(1, 0), rng);
    history.commitStep(stack);
    const auto painted = bytesOf(stack, layer, 1, 0);
    const auto id = history.undoId();
    check(!history.undo(stack, selection) && !history.getLastError().empty(), "an 8-bit sized snapshot of a 16-bit tile is refused");
    check(bytesOf(stack, layer, 1, 0) == painted && history.undoId() == id, "the refused undo wrote nothing and kept the step");
    std::printf("tile history: undo and redo of 16-bit tiles exact, an 8-bit sized snapshot refused\n");
}

void structureHistory() {
    std::mt19937 rng(61);
    document::LayerStack stack(256, 128, PixelFormat::RGBA16);
    selection::SelectionMask selection(256, 128);
    history::TileUndoManager history(50, 64, false);
    const int layer = stack.addLayer("p");
    fillRandom(*stack.getDrawingLayer(layer)->getTileGrid().getOrCreateTile(0, 0), rng);
    const auto pixels = bytesOf(stack, layer, 0, 0);
    check(history.beginStructure(stack, selection), "a structural step begins");
    stack.addLayer("q");
    check(history.commitStructure(stack, selection) != 0 && stack.getDrawingLayerCount() == 3, "and commits");
    check(history.undo(stack, selection) && stack.getDrawingLayerCount() == 2 && allLayers(stack, PixelFormat::RGBA16) &&
          bytesOf(stack, layer, 0, 0) == pixels, "undo of a structural step keeps the format and the pixels");
    check(history.redo(stack, selection) && stack.getDrawingLayerCount() == 3 && allLayers(stack, PixelFormat::RGBA16) &&
          bytesOf(stack, layer, 0, 0) == pixels, "redo keeps them too");
    std::printf("structure history: undo and redo keep the 16-bit format and pixels\n");
}

void guards() {
    document::LayerStack wide(256, 128, PixelFormat::RGBA16), eight(256, 128);
    wide.addLayer("x");
    eight.addLayer("x");
    document::Compositor compositor8(256, 128), compositor16(256, 128, PixelFormat::RGBA16);
    canvas::PixelBuffer out(256, 128, ColorRGBA{255, 255, 255, 255});
    const std::vector<uint8_t> blank(out.getData(), out.getData() + out.getSizeInBytes());
    const auto refuses = [&](document::Compositor& compositor, document::LayerStack& stack, canvas::PixelBuffer& target) {
        try { compositor.composite(stack.getAllLayersForComposition(), target); } catch (const std::logic_error&) { return true; }
        return false;
    };
    check(refuses(compositor8, wide, out) && std::memcmp(out.getData(), blank.data(), blank.size()) == 0,
          "the 8-bit compositor refuses a 16-bit layer and writes nothing");
    check(refuses(compositor16, eight, out) && std::memcmp(out.getData(), blank.data(), blank.size()) == 0,
          "the 16-bit compositor refuses an 8-bit layer and writes nothing");
    check(!refuses(compositor8, eight, out) && !refuses(compositor16, wide, out), "and each composes layers of its own format");
    canvas::PixelBuffer wideOut(256, 128, PixelFormat::RGBA16, ColorRGBA{255, 255, 255, 255});
    check(refuses(compositor16, wide, wideOut), "a 16-bit output buffer is refused: the screen is 8-bit");

    // A stack whose layers disagree on the format cannot be merged or flattened; one that agrees can, in both formats.
    std::vector<std::unique_ptr<document::Layer>> mixed;
    mixed.push_back(std::make_unique<document::Layer>("a", 64, 64, false, PixelFormat::RGBA8));
    mixed.push_back(std::make_unique<document::Layer>("b", 64, 64, false, PixelFormat::RGBA16));
    int active = 1;
    check(!document::LayerMerger::mergeLayerDown(mixed, active, 1) && mixed.size() == 2, "the merge refuses a stack of mixed formats and leaves it alone");
    const int group = wide.addGroup("g");
    check(wide.flattenGroup(group, false, false) && wide.mergeLayerDown(1, false, false), "a 16-bit stack flattens a group and merges a layer down");
    eight.addGroup("g");
    check(eight.mergeLayerDown(1, false, false), "and an 8-bit one still does");
    std::printf("guards: each compositor refuses the other format, the merge refuses a mixed stack\n");
}

} // namespace

int runPixelFormatDocumentChecks() {
    layers();
    tileHistory();
    structureHistory();
    guards();
    return g_failures;
}
