#ifndef ALADYN_ENGINE_MIPMAP_PYRAMID_HPP
#define ALADYN_ENGINE_MIPMAP_PYRAMID_HPP

#include "DamageRect.hpp"
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

    // Tudo mudou (ou não se sabe o quê): a próxima leitura refaz os três níveis.
    void markDirty() noexcept { m_rebuildAll = true; }
    // Só [x0, x1) x [y0, y1), em pixels do buffer base, mudou: a próxima leitura refaz
    // só essa parte de cada nível (D18). Quem escreve no buffer base avisa por aqui.
    void markDirtyRegion(int x0, int y0, int x1, int y1) noexcept { m_damage.add(x0, y0, x1, y1); }
    [[nodiscard]] bool isDirty() const noexcept { return m_rebuildAll || !m_damage.empty(); }

    // A parte de `baseBuffer` que a próxima leitura de `level` vai ler: o buffer inteiro se os
    // níveis precisam ser refeitos por completo (primeira leitura, tudo mudou, outro tamanho),
    // senão o retângulo que mudou. Quem mantém `baseBuffer` como cópia convertida do canvas
    // (o buffer de exibição com perfil de cor) converte só isso antes de ler.
    [[nodiscard]] DamageRect pendingRegion(int level, const PixelBuffer& baseBuffer) const noexcept {
        DamageRect region;
        const int targetLevel = std::clamp(level, 1, MAX_LOD_LEVELS);
        const bool everything = m_rebuildAll || m_baseWidth != baseBuffer.getWidth() ||
                                m_baseHeight != baseBuffer.getHeight() || m_levels.size() < static_cast<size_t>(targetLevel);
        if (everything) {
            region.add(0, 0, baseBuffer.getWidth(), baseBuffer.getHeight());
        } else if (!m_damage.empty()) {
            region.add(std::max(0, m_damage.x0()), std::max(0, m_damage.y0()),
                       std::min(baseBuffer.getWidth(), m_damage.x1()), std::min(baseBuffer.getHeight(), m_damage.y1()));
        }
        return region;
    }

    /**
     * @brief Tamanho do nível (1..3) para um buffer base de baseW x baseH: metade por nível,
     * nunca menos de 1. Única definição, usada pela reconstrução e por quem pergunta.
     */
    static void levelSize(int level, int baseW, int baseH, int& outW, int& outH) noexcept {
        outW = baseW;
        outH = baseH;
        for (int l = 0; l < level; ++l) {
            outW = std::max(1, outW / 2);
            outH = std::max(1, outH / 2);
        }
    }

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
    // Refaz [x0, x1) x [y0, y1) do destino (em pixels do destino) a partir de `src`.
    static void downscale2x(const uint8_t* src, int srcW, int srcH, uint8_t* dst, int dstW, int dstH,
                            int x0, int y0, int x1, int y1) noexcept;
    void updatePyramidRegion(const PixelBuffer& baseBuffer);

    std::vector<PixelBuffer> m_levels;
    bool m_rebuildAll{true};
    DamageRect m_damage;
    int m_baseWidth{0};
    int m_baseHeight{0};
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_MIPMAP_PYRAMID_HPP
