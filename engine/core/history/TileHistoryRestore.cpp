#include "TileUndoManager.hpp"
#include "../../infrastructure/compression/Lz4Codec.hpp"
#include <map>
#include <type_traits>

namespace aladyn::engine::history {

bool TileUndoManager::moveStep(document::LayerStack& stack, selection::SelectionMask& selection, bool redo) {
    m_lastError.clear();
    auto& source = redo ? m_redoStack : m_undoStack;
    auto& destination = redo ? m_undoStack : m_redoStack;
    if (source.empty()) return false;
    if (recordingStructure() || m_isRecording) {
        m_lastError = "history_busy";
        return false;
    }
    const auto fail = [this](const char* error) { m_lastError = error; return false; };
    try {
        const auto& step = source.back();
        const auto& structure = redo ? step.structureAfter : step.structureBefore;
        if (structure) {
            const auto& mask = redo ? step.selectionAfter : step.selectionBefore;
            if (!mask) return fail("history_invalid_snapshot");
            document::LayerStack prepared(*structure);
            auto preparedSelection = *mask;
            destination.emplace_back(); // Last allocation before publishing either state.
            stack.swap(prepared);
            static_assert(std::is_nothrow_move_assignable_v<selection::SelectionMask>);
            selection = std::move(preparedSelection);
        } else {
            // Only affected layer grids are cloned. COW keeps other pixels shared.
            std::map<int, canvas::TileGrid> prepared;
            constexpr size_t tileBytes = canvas::Tile::TILE_SIZE * canvas::Tile::TILE_SIZE * sizeof(utils::ColorRGBA);
            for (const auto& snap : step.snapshots) {
                auto* layer = stack.getDrawingLayer(snap.layerIndex);
                if (!layer) return fail("history_invalid_snapshot");
                const auto& original = layer->getTileGrid();
                if (snap.tileX < 0 || snap.tileX >= original.getTilesCountX() ||
                    snap.tileY < 0 || snap.tileY >= original.getTilesCountY())
                    return fail("history_invalid_snapshot");
                const auto bytes = redo ? snap.uncompressedAfterBytes : snap.uncompressedBeforeBytes;
                if (bytes != tileBytes) return fail("history_invalid_snapshot");
                std::vector<uint8_t> disk;
                const std::vector<uint8_t>* encoded = redo ? &snap.afterData : &snap.beforeData;
                if (snap.isPagedToDisk) {
                    const auto offset = redo ? snap.diskOffsetAfter : snap.diskOffsetBefore;
                    const auto size = redo ? snap.pagedAfterSize : snap.pagedBeforeSize;
                    if (!m_scratchDisk || !m_scratchDisk->readBlock(offset, size, disk))
                        return fail("scratch_read_failed");
                    encoded = &disk;
                }
                std::vector<uint8_t> decoded(tileBytes);
                if (snap.isCompressed) {
                    if (!compression::Lz4Codec::decompress(*encoded, decoded))
                        return fail("history_corrupt_snapshot");
                } else {
                    if (encoded->size() != tileBytes) return fail("history_invalid_snapshot");
                    decoded = *encoded;
                }
                auto [it, inserted] = prepared.try_emplace(snap.layerIndex, original.getWidth(), original.getHeight());
                if (inserted) it->second.copyFrom(original);
                auto* tile = it->second.getOrCreateTile(snap.tileX, snap.tileY);
                std::memcpy(tile->getBuffer().getData(), decoded.data(), tileBytes);
                tile->setDirty(true);
            }
            destination.emplace_back();
            static_assert(std::is_nothrow_move_assignable_v<canvas::TileGrid>);
            for (auto& [index, grid] : prepared)
                stack.getDrawingLayer(index)->getTileGrid() = std::move(grid);
        }
        static_assert(std::is_nothrow_move_assignable_v<UndoStep>);
        destination.back() = std::move(source.back());
        source.pop_back();
        // Paged records stay paged: reads allocate temporary working buffers only.
        return true;
    } catch (const std::exception&) {
        return fail("history_restore_failed");
    }
}

} // namespace aladyn::engine::history
