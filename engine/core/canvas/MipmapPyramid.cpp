#include "MipmapPyramid.hpp"
#include <cstring>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace aladyn::engine::canvas {

MipmapPyramid::MipmapPyramid() {
    m_levels.reserve(MAX_LOD_LEVELS);
}

uint8_t* MipmapPyramid::getLODData(int level, const PixelBuffer& baseBuffer, int& outW, int& outH) noexcept {
    if (level <= 0) {
        outW = baseBuffer.getWidth();
        outH = baseBuffer.getHeight();
        return const_cast<uint8_t*>(baseBuffer.getData());
    }

    const int targetLevel = std::clamp(level, 1, MAX_LOD_LEVELS);

    // Refaz tudo se não se sabe o que mudou ou se o buffer base foi redimensionado;
    // se só uma região mudou, refaz só ela.
    if (m_rebuildAll || m_baseWidth != baseBuffer.getWidth() || m_baseHeight != baseBuffer.getHeight() || m_levels.size() < static_cast<size_t>(targetLevel)) {
        updatePyramid(baseBuffer);
    } else if (!m_damage.empty()) {
        updatePyramidRegion(baseBuffer);
    }

    const size_t idx = static_cast<size_t>(targetLevel - 1);
    if (idx < m_levels.size()) {
        outW = m_levels[idx].getWidth();
        outH = m_levels[idx].getHeight();
        return m_levels[idx].getData();
    }

    // Fallback de segurança para o buffer base
    outW = baseBuffer.getWidth();
    outH = baseBuffer.getHeight();
    return const_cast<uint8_t*>(baseBuffer.getData());
}

void MipmapPyramid::updatePyramid(const PixelBuffer& baseBuffer) {
    const int baseW = baseBuffer.getWidth();
    const int baseH = baseBuffer.getHeight();

    if (baseW <= 0 || baseH <= 0 || baseBuffer.getData() == nullptr) {
        m_rebuildAll = false;
        m_damage.clear();
        return;
    }

    m_baseWidth = baseW;
    m_baseHeight = baseH;

    if (m_levels.size() != static_cast<size_t>(MAX_LOD_LEVELS)) {
        m_levels.clear();
        for (int l = 1; l <= MAX_LOD_LEVELS; ++l) {
            int levelW = 0, levelH = 0;
            levelSize(l, baseW, baseH, levelW, levelH);
            m_levels.emplace_back(levelW, levelH);
        }
    } else {
        // Verifica se dimensões mudaram
        for (int l = 1; l <= MAX_LOD_LEVELS; ++l) {
            int levelW = 0, levelH = 0;
            levelSize(l, baseW, baseH, levelW, levelH);
            PixelBuffer& level = m_levels[static_cast<size_t>(l - 1)];
            if (level.getWidth() != levelW || level.getHeight() != levelH) level.resize(levelW, levelH);
        }
    }

    // Nível 1 é gerado do buffer base (Nível 0)
    downscale2x(baseBuffer.getData(), baseW, baseH,
                m_levels[0].getData(), m_levels[0].getWidth(), m_levels[0].getHeight(),
                0, 0, m_levels[0].getWidth(), m_levels[0].getHeight());

    // Níveis subsequentes são gerados a partir do nível anterior (alta performance)
    for (size_t l = 1; l < m_levels.size(); ++l) {
        downscale2x(m_levels[l - 1].getData(), m_levels[l - 1].getWidth(), m_levels[l - 1].getHeight(),
                    m_levels[l].getData(), m_levels[l].getWidth(), m_levels[l].getHeight(),
                    0, 0, m_levels[l].getWidth(), m_levels[l].getHeight());
    }

    m_rebuildAll = false;
    m_damage.clear();
}

void MipmapPyramid::updatePyramidRegion(const PixelBuffer& baseBuffer) {
    // A região que mudou, em pixels do buffer base, recortada ao buffer.
    int x0 = std::max(0, m_damage.x0());
    int y0 = std::max(0, m_damage.y0());
    int x1 = std::min(baseBuffer.getWidth(), m_damage.x1());
    int y1 = std::min(baseBuffer.getHeight(), m_damage.y1());
    m_damage.clear();
    if (x0 >= x1 || y0 >= y1) return;

    const uint8_t* src = baseBuffer.getData();
    int srcW = baseBuffer.getWidth();
    int srcH = baseBuffer.getHeight();
    for (PixelBuffer& level : m_levels) {
        // O pixel (x, y) do nível lê (2x, 2y) a (2x+1, 2y+1) do anterior: os pixels do
        // nível que mudam são os de floor(x0/2) até floor((x1-1)/2), e o mesmo em y.
        x0 /= 2;
        y0 /= 2;
        x1 = std::min(level.getWidth(), (x1 + 1) / 2);
        y1 = std::min(level.getHeight(), (y1 + 1) / 2);
        if (x0 >= x1 || y0 >= y1) return;
        downscale2x(src, srcW, srcH, level.getData(), level.getWidth(), level.getHeight(), x0, y0, x1, y1);
        src = level.getData();
        srcW = level.getWidth();
        srcH = level.getHeight();
    }
}

void MipmapPyramid::downscale2x(const uint8_t* src, int srcW, int srcH,
                               uint8_t* dst, int dstW, int dstH,
                               int x0, int y0, int x1, int y1) noexcept {
    if (!src || !dst || srcW <= 0 || srcH <= 0 || dstW <= 0 || dstH <= 0) return;
    x0 = std::max(0, x0);
    y0 = std::max(0, y0);
    x1 = std::min(dstW, x1);
    y1 = std::min(dstH, y1);

    #pragma omp parallel for schedule(static) if(y1 - y0 >= 64)
    for (int y = y0; y < y1; ++y) {
        const int sy0 = y * 2;
        const int sy1 = std::min(sy0 + 1, srcH - 1);

        const uint8_t* row0 = src + static_cast<size_t>(sy0 * srcW * 4);
        const uint8_t* row1 = src + static_cast<size_t>(sy1 * srcW * 4);
        uint8_t* dstRow     = dst + static_cast<size_t>(y * dstW * 4);

        for (int x = x0; x < x1; ++x) {
            const int sx0 = x * 2;
            const int sx1 = std::min(sx0 + 1, srcW - 1);

            const size_t off0 = static_cast<size_t>(sx0 * 4);
            const size_t off1 = static_cast<size_t>(sx1 * 4);

            const uint8_t* p00 = row0 + off0;
            const uint8_t* p10 = row0 + off1;
            const uint8_t* p01 = row1 + off0;
            const uint8_t* p11 = row1 + off1;

            uint8_t* outP = dstRow + static_cast<size_t>(x * 4);

            // Filtragem de caixa (Box Filter) com arredondamento exato (+2 >> 2)
            outP[0] = static_cast<uint8_t>((static_cast<uint32_t>(p00[0]) + p10[0] + p01[0] + p11[0] + 2) >> 2);
            outP[1] = static_cast<uint8_t>((static_cast<uint32_t>(p00[1]) + p10[1] + p01[1] + p11[1] + 2) >> 2);
            outP[2] = static_cast<uint8_t>((static_cast<uint32_t>(p00[2]) + p10[2] + p01[2] + p11[2] + 2) >> 2);
            outP[3] = static_cast<uint8_t>((static_cast<uint32_t>(p00[3]) + p10[3] + p01[3] + p11[3] + 2) >> 2);
        }
    }
}

} // namespace aladyn::engine::canvas
