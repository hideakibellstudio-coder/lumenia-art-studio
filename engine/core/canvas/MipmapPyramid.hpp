#ifndef ALADYN_ENGINE_MIPMAP_PYRAMID_HPP
#define ALADYN_ENGINE_MIPMAP_PYRAMID_HPP

#include "PixelBuffer.hpp"
#include <vector>
#include <cstdint>
#include <algorithm>

namespace aladyn::engine::canvas {

/**
 * @brief Gerenciador nativo de Pirâmide de Resolução (LOD / Mipmapping) para o Canvas.
 * 
 * Mantém níveis reduzidos por filtragem de caixa (Box Filter 2x2 / Area-Averaging)
 * para eliminar serrilhados e aliasing durante visualização afastada (zoom out).
 */
class MipmapPyramid {
public:
    static constexpr int MAX_LOD_LEVELS = 3; // Níveis 1, 2, 3 (1/2, 1/4, 1/8)

    MipmapPyramid();
    ~MipmapPyramid() = default;

    void markDirty() noexcept { m_isDirty = true; }
    [[nodiscard]] bool isDirty() const noexcept { return m_isDirty; }

    /**
     * @brief Retorna o ponteiro para o buffer no nível de detalhe (LOD) requisitado.
     * Nível 0 = buffer 1:1 original (baseBuffer).
     * Níveis 1..3 = buffers reduzidos pré-filtrados (1/2, 1/4, 1/8).
     */
    uint8_t* getLODData(int level, const PixelBuffer& baseBuffer, int& outW, int& outH) noexcept;

    /**
     * @brief Calcula o melhor nível de LOD para um dado zoom de visualização.
     */
    [[nodiscard]] static int getBestLODLevel(double zoom) noexcept {
        if (zoom >= 0.75) return 0;
        if (zoom >= 0.375) return 1;
        if (zoom >= 0.1875) return 2;
        return 3;
    }

    /**
     * @brief Retorna o fator de escala do nível (1.0, 0.5, 0.25, 0.125).
     */
    [[nodiscard]] static double getLODScale(int level) noexcept {
        switch (level) {
            case 1: return 0.5;
            case 2: return 0.25;
            case 3: return 0.125;
            default: return 1.0;
        }
    }

    /**
     * @brief Força a reconstrução de todos os níveis de LOD a partir do buffer base.
     */
    void updatePyramid(const PixelBuffer& baseBuffer);

private:
    static void downscale2x(const uint8_t* src, int srcW, int srcH, uint8_t* dst, int dstW, int dstH) noexcept;

    std::vector<PixelBuffer> m_levels;
    bool m_isDirty{true};
    int m_baseWidth{0};
    int m_baseHeight{0};
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_MIPMAP_PYRAMID_HPP
