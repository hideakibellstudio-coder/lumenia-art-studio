#include "engine/core/canvas/TileUndoManager.hpp"
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif
#include <filesystem>
#include <iostream>
#include <map>
#include <random>
#include <stdexcept>

using namespace aladyn::engine;
using canvas::ScratchDiskManager;

void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }

class FaultDisk : public ScratchDiskManager {
public:
    FaultDisk() : ScratchDiskManager(false) { setEnabled(true); }
    std::map<uint64_t, std::vector<uint8_t>> blocks;
    int writes{0}, reads{0}, failWrite{-1}, failRead{-1}, corruptRead{-1};
    uint64_t offset{0};
    std::optional<uint64_t> writeBlock(const uint8_t* data, size_t size) override {
        if (++writes == failWrite) return std::nullopt;
        const auto result = offset;
        blocks.emplace(result, std::vector<uint8_t>(data, data + size));
        offset += size;
        return result;
    }
    bool readBlock(uint64_t at, size_t size, std::vector<uint8_t>& out) override {
        if (++reads == failRead) return false;
        const auto it = blocks.find(at);
        if (it == blocks.end() || it->second.size() != size) return false;
        out = it->second;
        if (reads == corruptRead) out.assign(1, 0); // Invalid LZ4, even though I/O succeeded.
        return true;
    }
};

void paintStep(canvas::TileUndoManager& history, document::LayerStack& stack, unsigned seed) {
    std::mt19937 rng(seed);
    auto& grid = stack.getDrawingLayer(0)->getTileGrid();
    history.beginStep("random pixels");
    for (int x = 0; x < grid.getTilesCountX(); ++x) {
        auto* tile = grid.getOrCreateTile(x, 0);
        require(tile != nullptr, "tile fixture returned null");
        auto& buffer = tile->getBuffer();
        history.recordTileBefore(0, x, 0, buffer.getData(), buffer.getSizeInBytes());
        for (size_t i = 0; i < buffer.getSizeInBytes(); ++i) buffer.getData()[i] = uint8_t(rng());
    }
    history.commitStep(stack);
}

std::vector<uint8_t> pixels(document::LayerStack& stack) {
    std::vector<uint8_t> result;
    auto& grid = stack.getDrawingLayer(0)->getTileGrid();
    for (int x = 0; x < grid.getTilesCountX(); ++x) {
        const auto& buffer = grid.getOrCreateTile(x, 0)->getBuffer();
        result.insert(result.end(), buffer.getData(), buffer.getData() + buffer.getSizeInBytes());
    }
    return result;
}

void replayFailure(bool redo, bool corruption) {
    auto disk = std::make_unique<FaultDisk>();
    auto* io = disk.get();
    canvas::TileUndoManager history(50, 1, true, std::move(disk));
    document::LayerStack stack(2048, 64);
    raster::SelectionMask selection(2048, 64);
    paintStep(history, stack, 1);
    auto first = pixels(stack);
    paintStep(history, stack, 2);
    auto second = pixels(stack);
    require(history.getPagedStepsCount() > 0, "fixture did not page history");
    if (redo) require(history.undo(stack, selection), "initial undo failed");
    std::cerr << "inject\n";
    const auto before = pixels(stack);
    const auto undoId = history.undoId(), redoId = history.redoId();
    const auto memory = history.getMemoryUsageBytes();
    io->reads = 0;
    (corruption ? io->corruptRead : io->failRead) = 2; // Fail after one tile was prepared.
    require(!(redo ? history.redo(stack, selection) : history.undo(stack, selection)), "failure reported success");
    std::cerr << "failed as expected\n";
    require(pixels(stack) == before, "pixels changed partially");
    require(history.undoId() == undoId && history.redoId() == redoId, "history moved on failure");
    require(history.getMemoryUsageBytes() == memory, "failed read leaked history accounting");
    require(!history.getLastError().empty(), "failure has no diagnostic");
    io->corruptRead = io->failRead = -1;
    require(redo ? history.redo(stack, selection) : history.undo(stack, selection), "retry failed");
    require(pixels(stack) == (redo ? second : first), "retry restored wrong pixels");
    require(history.getLastError().empty(), "successful retry retained old error");
    require(history.getMemoryUsageBytes() == memory, "successful read retained transient buffers");
}

void pagingFailure(int writeNumber) {
    auto disk = std::make_unique<FaultDisk>();
    auto* io = disk.get();
    io->failWrite = writeNumber;
    canvas::TileUndoManager history(50, 1, true, std::move(disk));
    document::LayerStack stack(2048, 64);
    raster::SelectionMask selection(2048, 64);
    paintStep(history, stack, 10);
    const auto first = pixels(stack);
    paintStep(history, stack, 20);
    require(io->writes >= writeNumber, "failure not exercised");
    require(history.getLastError() == "scratch_write_failed", "missing write failure diagnostic");
    require(history.undo(stack, selection), "latest complete step was lost");
    require(pixels(stack) == first, "paging failure lost part of a tile snapshot");
    require(history.redo(stack, selection), "redo after write failure failed");
}

void realDisk(const std::string& mode) {
    ScratchDiskManager disk;
    const std::vector<uint8_t> payload{1, 2, 3, 4, 5, 6};
    const auto offset = disk.writeBlock(payload);
    require(offset && *offset == 0, "offset zero is not a valid first record");
    std::vector<uint8_t> result{99, 98};
    if (mode == "disable") {
        disk.setEnabled(false);
        require(!disk.writeBlock(payload), "disabled scratch accepted a new write");
        require(disk.readBlock(*offset, payload.size(), result) && result == payload, "disable destroyed old records");
        disk.setEnabled(true);
        const auto next = disk.writeBlock(payload);
        require(next && *next != *offset, "reenable overwrote old record");
    } else {
        const auto path = disk.getFilePath(); // This manager exclusively created the test file.
        if (mode == "truncate") {
            std::filesystem::resize_file(path, 2);
        } else if (mode == "corrupt") {
            std::fstream edit(path, std::ios::in | std::ios::out | std::ios::binary);
            edit.put(char(88));
            edit.flush();
            require(bool(edit), "could not inject corruption");
        } else if (mode == "purge") {
            disk.purge();
        }
        require(!disk.readBlock(*offset, payload.size(), result), "damaged record was accepted");
        require(result == std::vector<uint8_t>({99, 98}), "failed read overwrote destination");
        if (mode == "purge") require(disk.getFilePath().empty(), "read recreated purged scratch");
    }
}

int main(int argc, char** argv) {
#ifdef _WIN32
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
#endif
    try {
        require(argc == 2, "scenario required");
        const std::string scenario = argv[1];
        if (scenario == "undo_read") replayFailure(false, false);
        else if (scenario == "redo_read") replayFailure(true, false);
        else if (scenario == "undo_corrupt") replayFailure(false, true);
        else if (scenario == "redo_corrupt") replayFailure(true, true);
        else if (scenario == "write_first") pagingFailure(1);
        else if (scenario == "write_partial") pagingFailure(3);
        else realDisk(scenario);
        std::cout << scenario << ": OK\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
