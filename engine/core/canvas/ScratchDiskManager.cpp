#include "ScratchDiskManager.hpp"
#include <filesystem>
#include <chrono>
#include <cstdio>
#include <random>

#ifdef _WIN32
#include <process.h>
#define GETPID _getpid
#else
#include <unistd.h>
#define GETPID getpid
#endif

namespace aladyn::engine::canvas {

ScratchDiskManager::ScratchDiskManager(bool enabled)
    : m_enabled(enabled) {
    if (m_enabled) {
        ensureFileOpen();
    }
}

ScratchDiskManager::~ScratchDiskManager() {
    purge();
}

void ScratchDiskManager::setEnabled(bool enabled) noexcept {
    std::lock_guard<std::mutex> lock(m_mutex);
    m_enabled = enabled;
    if (!m_enabled) {
        if (m_file.is_open()) {
            m_file.close();
        }
        if (!m_filePath.empty()) {
            std::remove(m_filePath.c_str());
            m_filePath.clear();
        }
    }
}

bool ScratchDiskManager::ensureFileOpen() {
    if (!m_enabled) return false;
    if (m_file.is_open()) return true;

    try {
        const auto tempDir = std::filesystem::temp_directory_path();
        const auto pid = GETPID();
        const auto now = std::chrono::high_resolution_clock::now().time_since_epoch().count();
        
        static std::mt19937_64 rng(static_cast<uint64_t>(now));
        const uint64_t rnd = rng();

        char filename[128];
        std::snprintf(filename, sizeof(filename), "lumenia_scratch_%d_%llx_%llx.bin",
                      static_cast<int>(pid),
                      static_cast<unsigned long long>(now),
                      static_cast<unsigned long long>(rnd));

        const auto fullPath = tempDir / filename;
        m_filePath = fullPath.string();

        m_file.open(m_filePath, std::ios::in | std::ios::out | std::ios::binary | std::ios::trunc);
        if (!m_file.is_open()) {
            // Tenta criar primeiro
            std::ofstream create(m_filePath, std::ios::binary | std::ios::trunc);
            create.close();
            m_file.open(m_filePath, std::ios::in | std::ios::out | std::ios::binary);
        }

        m_currentWriteOffset = 0;
        return m_file.is_open();
    } catch (...) {
        return false;
    }
}

uint64_t ScratchDiskManager::writeBlock(const uint8_t* data, size_t size) {
    if (!m_enabled || !data || size == 0) return 0;

    std::lock_guard<std::mutex> lock(m_mutex);
    if (!ensureFileOpen()) return 0;

    m_file.seekp(static_cast<std::streamoff>(m_currentWriteOffset));
    m_file.write(reinterpret_cast<const char*>(data), static_cast<std::streamsize>(size));
    m_file.flush();

    if (!m_file.good()) {
        m_file.clear();
        return 0;
    }

    const uint64_t writtenOffset = m_currentWriteOffset;
    m_currentWriteOffset += size;
    m_totalBytesPaged += size;
    ++m_pagedBlocksCount;

    return writtenOffset;
}

bool ScratchDiskManager::readBlock(uint64_t offset, size_t size, uint8_t* outData) {
    if (!m_enabled || !outData || size == 0) return false;

    std::lock_guard<std::mutex> lock(m_mutex);
    if (!ensureFileOpen()) return false;

    m_file.seekg(static_cast<std::streamoff>(offset));
    m_file.read(reinterpret_cast<char*>(outData), static_cast<std::streamsize>(size));

    if (!m_file.good() && !m_file.eof()) {
        m_file.clear();
        return false;
    }

    m_file.clear(); // Limpa eofbit se atingido
    return true;
}

bool ScratchDiskManager::readBlock(uint64_t offset, size_t size, std::vector<uint8_t>& outData) {
    outData.resize(size);
    return readBlock(offset, size, outData.data());
}

void ScratchDiskManager::purge() {
    std::lock_guard<std::mutex> lock(m_mutex);
    if (m_file.is_open()) {
        m_file.close();
    }
    if (!m_filePath.empty()) {
        std::remove(m_filePath.c_str());
        m_filePath.clear();
    }
    m_currentWriteOffset = 0;
    m_totalBytesPaged = 0;
    m_pagedBlocksCount = 0;
}

} // namespace aladyn::engine::canvas
