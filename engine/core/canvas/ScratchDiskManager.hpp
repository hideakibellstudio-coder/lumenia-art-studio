#ifndef ALADYN_ENGINE_SCRATCH_DISK_MANAGER_HPP
#define ALADYN_ENGINE_SCRATCH_DISK_MANAGER_HPP

#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
#include <fstream>
#include <mutex>

namespace aladyn::engine::canvas {

/**
 * @brief Gerenciador atômico de paginação em disco (Scratch Disk) para o histórico de Undo.
 * 
 * Permite descarregar passos antigos comprimidos para arquivos temporários no disco
 * quando a memória RAM física ultrapassa o limite pré-configurado, viabilizando
 * histórico praticamente infinito em telas de 600 DPI / 70 Megapixels.
 */
class ScratchDiskManager {
public:
    explicit ScratchDiskManager(bool enabled = true);
    ~ScratchDiskManager();

    // Desabilita cópia/movimentação acidental que invalidaria o arquivo
    ScratchDiskManager(const ScratchDiskManager&) = delete;
    ScratchDiskManager& operator=(const ScratchDiskManager&) = delete;

    [[nodiscard]] bool isEnabled() const noexcept { return m_enabled; }
    void setEnabled(bool enabled) noexcept;

    /// Grava um bloco de bytes no arquivo scratch e retorna seu offset
    uint64_t writeBlock(const uint8_t* data, size_t size);
    uint64_t writeBlock(const std::vector<uint8_t>& data) {
        return writeBlock(data.data(), data.size());
    }

    /// Lê um bloco de bytes previamente gravado a partir do offset
    bool readBlock(uint64_t offset, size_t size, uint8_t* outData);
    bool readBlock(uint64_t offset, size_t size, std::vector<uint8_t>& outData);

    /// Métricas de auditoria
    [[nodiscard]] uint64_t getTotalBytesPaged() const noexcept { return m_totalBytesPaged; }
    [[nodiscard]] size_t getPagedBlocksCount() const noexcept { return m_pagedBlocksCount; }
    [[nodiscard]] const std::string& getFilePath() const noexcept { return m_filePath; }

    /// Fecha e apaga o arquivo temporário
    void purge();

private:
    bool ensureFileOpen();

    bool m_enabled{true};
    std::string m_filePath;
    std::fstream m_file;
    std::mutex m_mutex;
    uint64_t m_currentWriteOffset{0};
    uint64_t m_totalBytesPaged{0};
    size_t m_pagedBlocksCount{0};
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_SCRATCH_DISK_MANAGER_HPP
