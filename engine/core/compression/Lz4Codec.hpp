#ifndef ALADYN_ENGINE_LZ4_CODEC_HPP
#define ALADYN_ENGINE_LZ4_CODEC_HPP

#include <cstdint>
#include <cstddef>
#include <vector>

namespace aladyn::engine::compression {

/**
 * @brief Codec de compressão e descompressão ultra-rápida sem perdas LZ4.
 * 
 * Implementação atômica em conformidade com ARCcC, operando a taxas de GB/s
 * para compressão de tiles em RAM e páginas de histórico de undo/redo.
 */
class Lz4Codec {
public:
    /// Retorna a capacidade máxima de buffer de destino para acomodar a pior compressão
    static constexpr size_t maxCompressedSize(size_t srcSize) noexcept {
        return srcSize + (srcSize / 255) + 32;
    }

    /// Comprime um bloco de memória para o buffer de destino fornecido.
    /// Retorna o número de bytes comprimidos gerados, ou 0 se a compressão falhar.
    static size_t compressBlock(
        const uint8_t* src,
        size_t srcSize,
        uint8_t* dst,
        size_t dstCapacity
    ) noexcept;

    /// Descomprime um bloco LZ4 para o buffer de destino uncompressed.
    /// Retorna true se descomprimido com sucesso e tamanho bater com dstCapacity.
    static bool decompressBlock(
        const uint8_t* src,
        size_t srcSize,
        uint8_t* dst,
        size_t dstCapacity
    ) noexcept;

    /// Métodos utilitários convenientes com std::vector
    static std::vector<uint8_t> compress(const uint8_t* src, size_t srcSize);
    static bool decompress(const std::vector<uint8_t>& compressed, std::vector<uint8_t>& dst);
};

} // namespace aladyn::engine::compression

#endif // ALADYN_ENGINE_LZ4_CODEC_HPP
