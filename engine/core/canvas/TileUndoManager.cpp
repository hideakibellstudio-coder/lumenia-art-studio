#include "TileUndoManager.hpp"
#include <algorithm>

namespace aladyn::engine::canvas {

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

    m_currentStep.snapshots.push_back(std::move(snap));
}

size_t TileUndoManager::calculateStepBytes(const UndoStep& step) noexcept {
    size_t total = 0;
    for (const auto& snap : step.snapshots) {
        total += snap.beforeData.size() + snap.afterData.size();
    }
    return total;
}

void TileUndoManager::commitStep(document::LayerStack& stack) {
    if (!m_isRecording) return;
    m_isRecording = false;

    // Grava o estado final ('afterData') de cada tile alterado
    auto it = m_currentStep.snapshots.begin();
    while (it != m_currentStep.snapshots.end()) {
        document::Layer* layer = stack.getDrawingLayer(it->layerIndex);

        if (layer) {
            Tile* tile = layer->getTileGrid().getTile(it->tileX, it->tileY);
            if (tile) {
                const auto& buf = tile->getBuffer();
                it->afterData.assign(buf.getData(), buf.getData() + buf.getSizeInBytes());
            }
        }

        // Se o tile não foi alterado de fato (before == after), ignora
        if (it->beforeData == it->afterData) {
            it = m_currentStep.snapshots.erase(it);
        } else {
            ++it;
        }
    }

    if (!m_currentStep.snapshots.empty()) {
        const size_t stepBytes = calculateStepBytes(m_currentStep);
        m_currentMemoryBytes += stepBytes;
        m_undoStack.push_back(std::move(m_currentStep));

        // Poda por contagem de passos E por teto de memória RAM
        while ((m_undoStack.size() > m_maxSteps || m_currentMemoryBytes > m_maxMemoryBytes) && m_undoStack.size() > 1) {
            m_currentMemoryBytes -= calculateStepBytes(m_undoStack.front());
            m_undoStack.pop_front();
        }

        m_redoStack.clear(); // Limpa a pilha de refazer ao realizar uma nova ação
    }
}

bool TileUndoManager::undo(document::LayerStack& stack) {
    if (m_undoStack.empty()) return false;

    UndoStep step = std::move(m_undoStack.back());
    m_undoStack.pop_back();

    for (const auto& snap : step.snapshots) {
        document::Layer* layer = stack.getDrawingLayer(snap.layerIndex);

        if (layer) {
            Tile* tile = layer->getTileGrid().getOrCreateTile(snap.tileX, snap.tileY);
            if (tile && snap.beforeData.size() == tile->getBuffer().getSizeInBytes()) {
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

    for (const auto& snap : step.snapshots) {
        document::Layer* layer = stack.getDrawingLayer(snap.layerIndex);

        if (layer) {
            Tile* tile = layer->getTileGrid().getOrCreateTile(snap.tileX, snap.tileY);
            if (tile && snap.afterData.size() == tile->getBuffer().getSizeInBytes()) {
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
    m_recordedTiles.clear();
    m_isRecording = false;
}

} // namespace aladyn::engine::canvas
