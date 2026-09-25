#ifndef ALADYN_ENGINE_TILE_UNDO_MANAGER_HPP
#define ALADYN_ENGINE_TILE_UNDO_MANAGER_HPP

#include "../canvas/TileGrid.hpp"
#include "../../infrastructure/storage/ScratchDiskManager.hpp"
#include "../document/LayerStack.hpp"
#include <vector>
#include <string>
#include <deque>
#include <unordered_set>
#include <cstdint>
#include <cstring>
#include <memory>
#include <atomic>
#include "../selection/SelectionMask.hpp"

namespace aladyn::engine::history {

struct TileSnapshotKey {
    int layerIndex{0};
    int tileX{0};
    int tileY{0};

    bool operator==(const TileSnapshotKey& other) const noexcept {
        return layerIndex == other.layerIndex && tileX == other.tileX && tileY == other.tileY;
    }
};

struct TileSnapshotKeyHash {
    std::size_t operator()(const TileSnapshotKey& k) const noexcept {
        std::size_t h1 = std::hash<int>{}(k.layerIndex);
        std::size_t h2 = std::hash<int>{}(k.tileX);
        std::size_t h3 = std::hash<int>{}(k.tileY);
        return h1 ^ (h2 << 1) ^ (h3 << 2);
    }
};

struct TileSnapshot {
    int layerIndex{0};
    int tileX{0};
    int tileY{0};

    bool isCompressed{false};
    size_t uncompressedBeforeBytes{0};
    size_t uncompressedAfterBytes{0};

    std::vector<uint8_t> beforeData;
    std::vector<uint8_t> afterData;

    // Paginação em Scratch Disk
    bool isPagedToDisk{false};
    uint64_t diskOffsetBefore{0};
    uint64_t diskOffsetAfter{0};
    size_t pagedBeforeSize{0};
    size_t pagedAfterSize{0};
};

struct UndoStep {
    uint64_t id{0};
    std::shared_ptr<document::LayerStack> structureBefore;
    std::shared_ptr<document::LayerStack> structureAfter;
    std::shared_ptr<selection::SelectionMask> selectionBefore;
    std::shared_ptr<selection::SelectionMask> selectionAfter;
    std::string description;
    std::vector<TileSnapshot> snapshots;
    bool isPagedToDisk{false};
};

class TileUndoManager {
public:
    explicit TileUndoManager(size_t maxSteps = 50, size_t maxMemoryMB = 256, bool scratchDiskEnabled = true,
                             std::unique_ptr<storage::ScratchDiskManager> storage = nullptr);
    ~TileUndoManager() = default;

    void beginStep(const std::string& description = "Stroke");
    void recordTileBefore(int layerIndex, int tileX, int tileY, const uint8_t* data, size_t sizeInBytes);
    void commitStep(document::LayerStack& stack);
    void cancelStep() noexcept;
    bool beginStructure(const document::LayerStack& stack, const selection::SelectionMask& selection);
    uint64_t commitStructure(const document::LayerStack& stack, const selection::SelectionMask& selection);
    bool cancelStructure(document::LayerStack& stack, selection::SelectionMask& selection);
    bool recordingStructure() const noexcept { return bool(m_structureBefore); }
    uint64_t undoId() const noexcept { return m_undoStack.empty() ? 0 : m_undoStack.back().id; }
    uint64_t redoId() const noexcept { return m_redoStack.empty() ? 0 : m_redoStack.back().id; }
    std::vector<uint64_t> historyIds() const {
        std::vector<uint64_t> ids;
        for (const auto& step : m_undoStack) ids.push_back(step.id);
        for (const auto& step : m_redoStack) ids.push_back(step.id);
        return ids;
    }

    bool undo(document::LayerStack& stack, selection::SelectionMask& selection);
    bool redo(document::LayerStack& stack, selection::SelectionMask& selection);

    void clear() noexcept;

    [[nodiscard]] bool canUndo() const noexcept { return !m_undoStack.empty(); }
    [[nodiscard]] bool canRedo() const noexcept { return !m_redoStack.empty(); }
    [[nodiscard]] size_t getUndoCount() const noexcept { return m_undoStack.size(); }
    [[nodiscard]] size_t getRedoCount() const noexcept { return m_redoStack.size(); }
    [[nodiscard]] size_t getMemoryUsageBytes() const noexcept { return m_currentMemoryBytes; }

    void setMaxMemoryMB(size_t mb) noexcept { m_maxMemoryBytes = mb * 1024 * 1024; }
    [[nodiscard]] size_t getMaxMemoryMB() const noexcept { return m_maxMemoryBytes / (1024 * 1024); }
    void setMaxSteps(size_t steps) noexcept { m_maxSteps = steps; }
    [[nodiscard]] size_t getMaxSteps() const noexcept { return m_maxSteps; }

    // ─── FASE 4: SCRATCH DISK PAGING & DIAGNÓSTICO ───────────────────────────
    void setScratchDiskEnabled(bool enabled);
    [[nodiscard]] bool isScratchDiskEnabled() const noexcept;
    [[nodiscard]] size_t getPagedStepsCount() const noexcept;
    [[nodiscard]] uint64_t getScratchDiskBytes() const noexcept;
    [[nodiscard]] const std::string& getLastError() const noexcept { return m_lastError; }

private:
    inline static std::atomic<uint64_t> m_nextId{1};
    std::shared_ptr<document::LayerStack> m_structureBefore;
    std::shared_ptr<selection::SelectionMask> m_selectionBefore;
    static size_t calculateStepBytes(const UndoStep& step) noexcept;
    bool pageOldestStepToDisk();
    bool moveStep(document::LayerStack& stack, selection::SelectionMask& selection, bool redo);
    void recalculateMemory() noexcept;
    std::string m_lastError;

    size_t m_maxSteps{50};
    size_t m_maxMemoryBytes{256 * 1024 * 1024}; // 256 MB de teto padrão
    size_t m_currentMemoryBytes{0};

    bool m_isRecording{false};
    UndoStep m_currentStep;
    std::unordered_set<TileSnapshotKey, TileSnapshotKeyHash> m_recordedTiles;
    std::deque<UndoStep> m_undoStack;
    std::deque<UndoStep> m_redoStack;

    std::unique_ptr<storage::ScratchDiskManager> m_scratchDisk;
};

} // namespace aladyn::engine::history

#endif // ALADYN_ENGINE_TILE_UNDO_MANAGER_HPP
