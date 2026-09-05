#include "TileUndoManager.hpp"
#include "../compression/Lz4Codec.hpp"
#include <algorithm>

namespace aladyn::engine::canvas {

TileUndoManager::TileUndoManager(size_t maxSteps, size_t maxMemoryMB, bool scratchDiskEnabled)
    : m_maxSteps(maxSteps),
      m_maxMemoryBytes(maxMemoryMB * 1024 * 1024),
      m_scratchDisk(std::make_unique<ScratchDiskManager>(scratchDiskEnabled)) {}

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
    m_currentStep = UndoStep();
    m_currentStep.description = description;
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

    static const uint8_t s_emptyTileData[canvas::Tile::TILE_SIZE * canvas::Tile::TILE_SIZE * sizeof(raster::ColorRGBA)] = {0};
    constexpr size_t s_emptyTileBytes = sizeof(s_emptyTileData);

    for (auto& snap : m_currentStep.snapshots) {
        document::Layer* layer = stack.getDrawingLayer(snap.layerIndex);
        if (!layer) continue;

        Tile* tile = layer->getTileGrid().getTile(snap.tileX, snap.tileY);
        const uint8_t* currentData = nullptr;
        size_t currentSize = 0;

        if (tile) {
            const auto& buf = tile->getBuffer();
            currentData = buf.getData();
            currentSize = buf.getSizeInBytes();
        } else {
            currentData = s_emptyTileData;
            currentSize = s_emptyTileBytes;
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
        const size_t stepBytes = calculateStepBytes(m_currentStep);
        m_currentMemoryBytes += stepBytes;
        m_undoStack.push_back(std::move(m_currentStep));

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

        m_redoStack.clear();
    }
}

bool TileUndoManager::pageOldestStepToDisk() {
    if (!m_scratchDisk || !m_scratchDisk->isEnabled()) return false;

    // Encontra o passo mais antigo não paginado
    for (auto& step : m_undoStack) {
        if (!step.isPagedToDisk) {
            size_t bytesFreed = 0;
            for (auto& snap : step.snapshots) {
                if (!snap.isPagedToDisk) {
                    snap.diskOffsetBefore = m_scratchDisk->writeBlock(snap.beforeData);
                    snap.pagedBeforeSize = snap.beforeData.size();
                    bytesFreed += snap.beforeData.capacity();
                    snap.beforeData.clear();
                    snap.beforeData.shrink_to_fit();

                    snap.diskOffsetAfter = m_scratchDisk->writeBlock(snap.afterData);
                    snap.pagedAfterSize = snap.afterData.size();
                    bytesFreed += snap.afterData.capacity();
                    snap.afterData.clear();
                    snap.afterData.shrink_to_fit();

                    snap.isPagedToDisk = true;
                }
            }
            step.isPagedToDisk = true;
            m_currentMemoryBytes = (m_currentMemoryBytes > bytesFreed) ? (m_currentMemoryBytes - bytesFreed) : 0;
            return true;
        }
    }
    return false;
}

bool TileUndoManager::restoreStepFromDisk(UndoStep& step) {
    if (!step.isPagedToDisk || !m_scratchDisk) return false;

    for (auto& snap : step.snapshots) {
        if (snap.isPagedToDisk) {
            bool ok1 = m_scratchDisk->readBlock(snap.diskOffsetBefore, snap.pagedBeforeSize, snap.beforeData);
            bool ok2 = m_scratchDisk->readBlock(snap.diskOffsetAfter, snap.pagedAfterSize, snap.afterData);
            if (!ok1 || !ok2) return false;
            snap.isPagedToDisk = false;
        }
    }
    step.isPagedToDisk = false;
    return true;
}

void TileUndoManager::cancelStep() noexcept {
    m_isRecording = false;
    m_currentStep.snapshots.clear();
    m_currentStep.description.clear();
    m_recordedTiles.clear();
}

bool TileUndoManager::undo(document::LayerStack& stack) {
    if (m_undoStack.empty()) return false;

    UndoStep step = std::move(m_undoStack.back());
    m_undoStack.pop_back();

    if (step.isPagedToDisk) {
        restoreStepFromDisk(step);
    }

    std::vector<uint8_t> decompressedBuffer;

    for (const auto& snap : step.snapshots) {
        document::Layer* layer = stack.getDrawingLayer(snap.layerIndex);

        if (layer) {
            Tile* tile = layer->getTileGrid().getOrCreateTile(snap.tileX, snap.tileY);
            if (!tile) continue;

            if (snap.isCompressed) {
                decompressedBuffer.resize(snap.uncompressedBeforeBytes);
                if (compression::Lz4Codec::decompress(snap.beforeData, decompressedBuffer)) {
                    if (decompressedBuffer.size() == tile->getBuffer().getSizeInBytes()) {
                        std::memcpy(tile->getBuffer().getData(), decompressedBuffer.data(), decompressedBuffer.size());
                        tile->setDirty(true);
                    }
                }
            } else if (snap.beforeData.size() == tile->getBuffer().getSizeInBytes()) {
                std::memcpy(tile->getBuffer().getData(), snap.beforeData.data(), snap.beforeData.size());
                tile->setDirty(true);
            }
        }
    }

    m_redoStack.push_back(std::move(step));
    return true;
}

bool TileUndoManager::redo(document::LayerStack& stack) {
    if (m_redoStack.empty()) return false;

    UndoStep step = std::move(m_redoStack.back());
    m_redoStack.pop_back();

    if (step.isPagedToDisk) {
        restoreStepFromDisk(step);
    }

    std::vector<uint8_t> decompressedBuffer;

    for (const auto& snap : step.snapshots) {
        document::Layer* layer = stack.getDrawingLayer(snap.layerIndex);

        if (layer) {
            Tile* tile = layer->getTileGrid().getOrCreateTile(snap.tileX, snap.tileY);
            if (!tile) continue;

            if (snap.isCompressed) {
                decompressedBuffer.resize(snap.uncompressedAfterBytes);
                if (compression::Lz4Codec::decompress(snap.afterData, decompressedBuffer)) {
                    if (decompressedBuffer.size() == tile->getBuffer().getSizeInBytes()) {
                        std::memcpy(tile->getBuffer().getData(), decompressedBuffer.data(), decompressedBuffer.size());
                        tile->setDirty(true);
                    }
                }
            } else if (snap.afterData.size() == tile->getBuffer().getSizeInBytes()) {
                std::memcpy(tile->getBuffer().getData(), snap.afterData.data(), snap.afterData.size());
                tile->setDirty(true);
            }
        }
    }

    m_undoStack.push_back(std::move(step));
    return true;
}

void TileUndoManager::clear() noexcept {
    m_undoStack.clear();
    m_redoStack.clear();
    m_currentMemoryBytes = 0;
    if (m_scratchDisk) {
        m_scratchDisk->purge();
    }
}

} // namespace aladyn::engine::canvas
