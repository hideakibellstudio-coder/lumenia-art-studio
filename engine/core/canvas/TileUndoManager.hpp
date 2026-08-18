#ifndef ALADYN_ENGINE_TILE_UNDO_MANAGER_HPP
#define ALADYN_ENGINE_TILE_UNDO_MANAGER_HPP

#include "TileGrid.hpp"
#include "../document/LayerStack.hpp"
#include <vector>
#include <string>
#include <deque>
#include <unordered_set>
#include <cstdint>
#include <cstring>
#include <memory>

namespace aladyn::engine::canvas {

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
    std::vector<uint8_t> beforeData;
    std::vector<uint8_t> afterData;
};

struct UndoStep {
    std::string description;
    std::vector<TileSnapshot> snapshots;
};

class TileUndoManager {
public:
    explicit TileUndoManager(size_t maxSteps = 50, size_t maxMemoryMB = 256)
        : m_maxSteps(maxSteps), m_maxMemoryBytes(maxMemoryMB * 1024 * 1024) {}

    void beginStep(const std::string& description = "Stroke");
    void recordTileBefore(int layerIndex, int tileX, int tileY, const uint8_t* data, size_t sizeInBytes);
    void commitStep(document::LayerStack& stack);

    bool undo(document::LayerStack& stack);
    bool redo(document::LayerStack& stack);

    void clear() noexcept;

    [[nodiscard]] bool canUndo() const noexcept { return !m_undoStack.empty(); }
    [[nodiscard]] bool canRedo() const noexcept { return !m_redoStack.empty(); }
    [[nodiscard]] size_t getUndoCount() const noexcept { return m_undoStack.size(); }
    [[nodiscard]] size_t getRedoCount() const noexcept { return m_redoStack.size(); }
    [[nodiscard]] size_t getMemoryUsageBytes() const noexcept { return m_currentMemoryBytes; }
    void setMaxMemoryMB(size_t mb) noexcept { m_maxMemoryBytes = mb * 1024 * 1024; }

private:
    static size_t calculateStepBytes(const UndoStep& step) noexcept;

    size_t m_maxSteps{50};
    size_t m_maxMemoryBytes{256 * 1024 * 1024}; // 256 MB de teto padrão
    size_t m_currentMemoryBytes{0};

    bool m_isRecording{false};
    UndoStep m_currentStep;
    std::unordered_set<TileSnapshotKey, TileSnapshotKeyHash> m_recordedTiles;
    std::deque<UndoStep> m_undoStack;
    std::deque<UndoStep> m_redoStack;
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_TILE_UNDO_MANAGER_HPP
