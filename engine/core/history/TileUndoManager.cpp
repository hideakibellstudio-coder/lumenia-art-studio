#include "TileUndoManager.hpp"
#include "../../infrastructure/compression/Lz4Codec.hpp"
#include <algorithm>

namespace aladyn::engine::history {

TileUndoManager::TileUndoManager(size_t maxSteps, size_t maxMemoryMB, bool scratchDiskEnabled,
                                 std::unique_ptr<storage::ScratchDiskManager> storage)
    : m_maxSteps(maxSteps),
      m_maxMemoryBytes(maxMemoryMB * 1024 * 1024),
      m_scratchDisk(storage ? std::move(storage) : std::make_unique<storage::ScratchDiskManager>(scratchDiskEnabled)) {}

void TileUndoManager::recalculateMemory() noexcept {
    m_currentMemoryBytes = 0;
    for (const auto& step : m_undoStack) m_currentMemoryBytes += calculateStepBytes(step);
    for (const auto& step : m_redoStack) m_currentMemoryBytes += calculateStepBytes(step);
}

void TileUndoManager::setScratchDiskEnabled(bool enabled) {
    if (m_scratchDisk) {
        m_scratchDisk->setEnabled(enabled);
    }
}

bool TileUndoManager::isScratchDiskEnabled() const noexcept {
    return m_scratchDisk ? m_scratchDisk->isEnabled() : false;
}

size_t TileUndoManager::getPagedStepsCount() const noexcept {
    size_t count = 0;
    for (const auto& s : m_undoStack) {
        if (s.isPagedToDisk) ++count;
    }
    return count;
}

uint64_t TileUndoManager::getScratchDiskBytes() const noexcept {
    return m_scratchDisk ? m_scratchDisk->getTotalBytesPaged() : 0;
}

void TileUndoManager::beginStep(const std::string& description) {
    if (recordingStructure()) return;
    m_currentStep = UndoStep();
    m_currentStep.description = description;
    m_currentStep.id = m_nextId++;
    m_recordedTiles.clear();
    m_isRecording = true;
}

void TileUndoManager::recordTileBefore(int layerIndex, int tileX, int tileY, const uint8_t* data, size_t sizeInBytes) {
    if (!m_isRecording || !data || sizeInBytes == 0) return;

    TileSnapshotKey key{layerIndex, tileX, tileY};
    if (m_recordedTiles.find(key) != m_recordedTiles.end()) {
        return; // Já gravamos o estado inicial deste tile no início deste passo
    }
    m_recordedTiles.insert(key);

    TileSnapshot snap;
    snap.layerIndex = layerIndex;
    snap.tileX = tileX;
    snap.tileY = tileY;
    snap.beforeData.assign(data, data + sizeInBytes);
    snap.uncompressedBeforeBytes = sizeInBytes;

    m_currentStep.snapshots.push_back(std::move(snap));
}

size_t TileUndoManager::calculateStepBytes(const UndoStep& step) noexcept {
    size_t total = sizeof(UndoStep);
    if (step.selectionBefore) total += step.selectionBefore->getSizeInBytes();
    if (step.selectionAfter) total += step.selectionAfter->getSizeInBytes();
    if (step.structureBefore) total += step.structureBefore->snapshotBytes();
    if (step.structureAfter) total += step.structureAfter->snapshotBytes();
    for (const auto& snap : step.snapshots) {
        total += sizeof(TileSnapshot);
        if (!snap.isPagedToDisk) {
            total += snap.beforeData.capacity() + snap.afterData.capacity();
        }
    }
    return total;
}

void TileUndoManager::commitStep(document::LayerStack& stack) {
    if (!m_isRecording) return;
    m_isRecording = false;

    std::vector<TileSnapshot> keptSnapshots;
    keptSnapshots.reserve(m_currentStep.snapshots.size());

    for (auto& snap : m_currentStep.snapshots) {
        document::Layer* layer = stack.getDrawingLayer(snap.layerIndex);
        if (!layer) continue;

        canvas::Tile* tile = layer->getTileGrid().getTile(snap.tileX, snap.tileY);
        const uint8_t* currentData = nullptr;
        size_t currentSize = 0;

        if (tile) {
            const auto& buf = tile->getBuffer();
            currentData = buf.getData();
            currentSize = buf.getSizeInBytes();
        } else {
            currentData = canvas::zeroTileData();
            currentSize = canvas::Tile::bytesFor(layer->getTileGrid().getFormat());
        }

        // Se o tile não foi alterado de fato, descarta
        if (currentSize == snap.beforeData.size() &&
            std::memcmp(snap.beforeData.data(), currentData, currentSize) == 0) {
            continue;
        }

        // Compressão LZ4 Streaming dos snapshots de histórico
        snap.uncompressedBeforeBytes = snap.beforeData.size();
        snap.beforeData = compression::Lz4Codec::compress(snap.beforeData.data(), snap.beforeData.size());

        snap.uncompressedAfterBytes = currentSize;
        snap.afterData = compression::Lz4Codec::compress(currentData, currentSize);
        snap.isCompressed = true;

        keptSnapshots.push_back(std::move(snap));
    }

    m_recordedTiles.clear();
    m_currentStep.snapshots = std::move(keptSnapshots);

    if (!m_currentStep.snapshots.empty()) {
        m_undoStack.push_back(std::move(m_currentStep));
        m_redoStack.clear();
        recalculateMemory();

        // Controle de Teto de RAM: primeiro pagina em disco (Scratch Disk) se habilitado
        while (m_currentMemoryBytes > m_maxMemoryBytes && m_undoStack.size() > 1) {
            if (m_scratchDisk && m_scratchDisk->isEnabled() && pageOldestStepToDisk()) {
                // Paginado para disco com sucesso: RAM foi liberada sem perder o passo
                continue;
            }
            // Se o scratch disk estiver desligado ou falhar, faz poda
            m_currentMemoryBytes -= calculateStepBytes(m_undoStack.front());
            m_undoStack.pop_front();
        }

        // Poda por contagem estrita de passos
        while (m_undoStack.size() > m_maxSteps && m_undoStack.size() > 1) {
            m_currentMemoryBytes -= calculateStepBytes(m_undoStack.front());
            m_undoStack.pop_front();
        }

    }
}

bool TileUndoManager::pageOldestStepToDisk() {
    if (!m_scratchDisk || !m_scratchDisk->isEnabled()) return false;

    // Encontra o passo mais antigo não paginado
    for (auto& step : m_undoStack) {
        if (!step.isPagedToDisk && !step.structureBefore) {
            std::vector<std::pair<uint64_t, uint64_t>> offsets;
            offsets.reserve(step.snapshots.size());
            for (const auto& snap : step.snapshots) {
                const auto before = m_scratchDisk->writeBlock(snap.beforeData);
                const auto after = before ? m_scratchDisk->writeBlock(snap.afterData) : std::nullopt;
                if (!before || !after) {
                    m_lastError = "scratch_write_failed";
                    return false; // No RAM buffer or offset has changed yet.
                }
                offsets.emplace_back(*before, *after);
            }
            size_t bytesFreed = 0;
            size_t index = 0;
            for (auto& snap : step.snapshots) {
                if (!snap.isPagedToDisk) {
                    snap.diskOffsetBefore = offsets[index].first;
                    snap.pagedBeforeSize = snap.beforeData.size();
                    bytesFreed += snap.beforeData.capacity();
                    std::vector<uint8_t>().swap(snap.beforeData);

                    snap.diskOffsetAfter = offsets[index].second;
                    snap.pagedAfterSize = snap.afterData.size();
                    bytesFreed += snap.afterData.capacity();
                    std::vector<uint8_t>().swap(snap.afterData);

                    snap.isPagedToDisk = true;
                }
                ++index;
            }
            step.isPagedToDisk = true;
            m_currentMemoryBytes = (m_currentMemoryBytes > bytesFreed) ? (m_currentMemoryBytes - bytesFreed) : 0;
            return true;
        }
    }
    return false;
}

void TileUndoManager::cancelStep() noexcept {
    m_isRecording = false;
    m_currentStep.snapshots.clear();
    m_currentStep.description.clear();
    m_recordedTiles.clear();
}

bool TileUndoManager::undo(document::LayerStack& stack, selection::SelectionMask& selection) {
    return moveStep(stack, selection, false);
}

bool TileUndoManager::redo(document::LayerStack& stack, selection::SelectionMask& selection) {
    return moveStep(stack, selection, true);
}

void TileUndoManager::clear() noexcept {
    if (recordingStructure()) return;
    m_undoStack.clear();
    m_redoStack.clear();
    m_currentMemoryBytes = 0;
    if (m_scratchDisk) {
        m_scratchDisk->purge();
    }
}

bool TileUndoManager::beginStructure(const document::LayerStack& stack, const selection::SelectionMask& selection) {
    if (recordingStructure() || m_isRecording) return false;
    auto mask = std::make_shared<selection::SelectionMask>(selection);
    m_structureBefore = std::make_shared<document::LayerStack>(stack);
    m_selectionBefore = std::move(mask);
    return true;
}

uint64_t TileUndoManager::commitStructure(const document::LayerStack& stack, const selection::SelectionMask& selection) {
    if (!recordingStructure()) return 0;
    UndoStep step;
    step.id = m_nextId++;
    step.selectionBefore = m_selectionBefore;
    step.selectionAfter = std::make_shared<selection::SelectionMask>(selection);
    step.structureBefore = m_structureBefore;
    step.structureAfter = std::make_shared<document::LayerStack>(stack);
    const auto id = step.id;
    m_undoStack.push_back(std::move(step));
    m_structureBefore.reset();
    m_selectionBefore.reset();
    m_redoStack.clear();
    m_currentMemoryBytes = 0;
    for (const auto& entry : m_undoStack) m_currentMemoryBytes += calculateStepBytes(entry);
    while (m_undoStack.size() > 1 && (m_undoStack.size() > m_maxSteps || m_currentMemoryBytes > m_maxMemoryBytes)) {
        m_currentMemoryBytes -= calculateStepBytes(m_undoStack.front());
        m_undoStack.pop_front();
    }
    return id;
}

bool TileUndoManager::cancelStructure(document::LayerStack& stack, selection::SelectionMask& selection) {
    if (!recordingStructure()) return false;
    auto mask = *m_selectionBefore;
    stack.restore(*m_structureBefore);
    selection = std::move(mask);
    m_structureBefore.reset();
    m_selectionBefore.reset();
    return true;
}

} // namespace aladyn::engine::history
