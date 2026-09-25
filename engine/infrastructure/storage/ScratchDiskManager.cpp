#include "ScratchDiskManager.hpp"
#include <filesystem>
#include <chrono>
#include <cstdio>
#include <random>
#include <cstring>
#include <limits>

#ifdef _WIN32
#include <process.h>
#define GETPID _getpid
#else
#include <unistd.h>
#define GETPID getpid
#endif

namespace aladyn::engine::storage {

namespace {
uint64_t checksum(const uint8_t* data, size_t size) {
    uint64_t hash = 14695981039346656037ULL;
    for (size_t i = 0; i < size; ++i) hash = (hash ^ data[i]) * 1099511628211ULL;
    return hash;
}
}

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
    // Disable future paging, but retain records still referenced by undo/redo.
}

bool ScratchDiskManager::ensureFileOpen() {
    if (!m_enabled) return false;
    if (m_file.is_open()) return true;

    try {
        const auto tempDir = std::filesystem::temp_directory_path();
        const auto pid = GETPID();
        const auto now = std::chrono::high_resolution_clock::now().time_since_epoch().count();
        
        thread_local std::mt19937_64 rng(static_cast<uint64_t>(now));
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

std::optional<uint64_t> ScratchDiskManager::writeBlock(const uint8_t* data, size_t size) {
    if (!data || size == 0) return std::nullopt;

    std::lock_guard<std::mutex> lock(m_mutex);
    if (!m_enabled || !ensureFileOpen()) return std::nullopt;
    const auto limit = static_cast<uint64_t>(std::numeric_limits<std::streamoff>::max());
    if (size > limit || m_currentWriteOffset > limit - size) return std::nullopt;
    std::error_code ec;
    if (!std::filesystem::exists(m_filePath, ec)) return std::nullopt;

    m_file.clear();
    m_file.seekp(static_cast<std::streamoff>(m_currentWriteOffset));
    m_file.write(reinterpret_cast<const char*>(data), static_cast<std::streamsize>(size));
    m_file.flush();

    if (!m_file.good()) {
        m_file.clear();
        return std::nullopt;
    }

    const uint64_t writtenOffset = m_currentWriteOffset;
    m_records.emplace(writtenOffset, Record{size, checksum(data, size)});
    m_currentWriteOffset += size;
    m_totalBytesPaged += size;
    ++m_pagedBlocksCount;

    return writtenOffset;
}

bool ScratchDiskManager::readBlock(uint64_t offset, size_t size, uint8_t* outData) {
    if (!outData) return false;
    std::vector<uint8_t> verified;
    if (!readBlock(offset, size, verified)) return false;
    std::memcpy(outData, verified.data(), size);
    return true;
}

bool ScratchDiskManager::readBlock(uint64_t offset, size_t size, std::vector<uint8_t>& outData) {
    std::lock_guard<std::mutex> lock(m_mutex);
    const auto record = m_records.find(offset);
    std::error_code ec;
    if (record == m_records.end() || size != record->second.size ||
        !m_file.is_open() || !std::filesystem::exists(m_filePath, ec)) return false;

    // Reject truncated/corrupt records before touching the caller buffer.
    // The stream's eofbit alone is insufficient because a short read can
    // otherwise be reported as success when EOF is reached exactly.
    m_file.clear();
    m_file.seekg(0, std::ios::end);
    const auto fileSize = m_file.tellg();
    if (fileSize < 0 || offset > static_cast<uint64_t>(fileSize) ||
        size > static_cast<uint64_t>(fileSize) - offset) {
        m_file.clear();
        return false;
    }

    m_file.clear();
    m_file.seekg(static_cast<std::streamoff>(offset));
    std::vector<uint8_t> verified(size);
    m_file.read(reinterpret_cast<char*>(verified.data()), static_cast<std::streamsize>(size));

    if (m_file.gcount() != static_cast<std::streamsize>(size)) {
        m_file.clear();
        return false;
    }

    m_file.clear(); // Limpa eofbit se atingido
    if (checksum(verified.data(), verified.size()) != record->second.checksum) return false;
    outData.swap(verified);
    return true;
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
    m_records.clear();
}

} // namespace aladyn::engine::storage
