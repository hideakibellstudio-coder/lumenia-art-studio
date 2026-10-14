#ifndef ALADYN_ENGINE_BLURRED_REGION_HPP
#define ALADYN_ENGINE_BLURRED_REGION_HPP

#include "BlurScratch.hpp"
#include "../canvas/PixelFormat.hpp"
#include "../canvas/Tile.hpp"
#include "../canvas/TileGrid.hpp"
#include <algorithm>
#include <cmath>
#include <cstddef>

namespace aladyn::engine::engines {

// Um retângulo de pixels, bordas incluídas.
struct BlurBox {
    int minX, maxX, minY, maxY;
    [[nodiscard]] int width() const { return maxX - minX + 1; }
    [[nodiscard]] int height() const { return maxY - minY + 1; }
    [[nodiscard]] bool empty() const { return width() <= 0 || height() <= 0; }
    [[nodiscard]] bool contains(int x, int y) const { return x >= minX && x <= maxX && y >= minY && y <= maxY; }
};

// ─── O DESFOQUE GAUSSIANO DE UMA REGIÃO ─────────────────────────────────────
//
// Copia a área da camada (com a borda do kernel) em cinco planos de ponto flutuante, faz o passe horizontal e o
// vertical de uma vez para a região toda, e `blurredAt` só lê o resultado. Lê apenas da cópia: o resultado de um
// pixel não depende de os vizinhos já terem sido pintados.
//
// Os planos são a soma ponderada de (cor × alfa), do alfa normalizado e do alfa bruto: a divisão do
// pré-multiplicado (a cor média só dos pixels que têm cor) é do chamador. A soma de cada pixel percorre as
// tomadas do kernel na mesma ordem de sempre (de -raio a +raio), então o resultado é o mesmo, bit a bit, do laço
// por pixel que isto substituiu; o que mudou é que o laço de dentro corre pelos pixels vizinhos (o compilador o
// vetoriza) e que as linhas rodam em paralelo.
template <class Pixel>
class BlurredRegion {
public:
    struct Blurred {
        float r, g, b, a;
        float alphaWeight, totalWeight;
    };

    BlurredRegion(BlurScratch& scratch, canvas::TileGrid& grid, const BlurBox& roi, int kernelRadius, double sigma)
        : m_scratch(scratch),
          m_radius(kernelRadius),
          m_roi(roi),
          m_snap{std::max(0, roi.minX - kernelRadius), std::min(grid.getWidth() - 1, roi.maxX + kernelRadius),
                 std::max(0, roi.minY - kernelRadius), std::min(grid.getHeight() - 1, roi.maxY + kernelRadius)} {
        if (m_snap.empty() || m_roi.empty()) return;
        m_snapWidth = m_snap.width();
        m_snapHeight = m_snap.height();
        m_roiWidth = m_roi.width();

        buildWeights(sigma);
        loadPlanes(grid);
        blurRows();
        blurColumns();
    }

    [[nodiscard]] bool empty() const { return m_snap.empty() || m_roi.empty(); }

    // O resultado no pixel `(globalX, globalY)`, que tem de estar dentro da região pedida.
    [[nodiscard]] Blurred blurredAt(int globalX, int globalY) const {
        const std::size_t plane = static_cast<std::size_t>(m_roiWidth) * static_cast<std::size_t>(m_roi.height());
        const std::size_t i = static_cast<std::size_t>(globalY - m_roi.minY) * static_cast<std::size_t>(m_roiWidth) +
                              static_cast<std::size_t>(globalX - m_roi.minX);
        const float* planes = m_scratch.blurred.data();
        return Blurred{planes[kRed * plane + i], planes[kGreen * plane + i], planes[kBlue * plane + i],
                       planes[kAlpha * plane + i], planes[kAlphaWeight * plane + i], m_totalWeight};
    }

private:
    // Os planos: a cor pré-multiplicada, o alfa bruto (soma `a`) e o alfa normalizado (peso do alfa).
    enum BlurPlane : int { kRed, kGreen, kBlue, kAlpha, kAlphaWeight, kPlaneCount };

    static constexpr int kBlock = 128;                        // saídas somadas de uma vez, num vetor que cabe no L1
    static constexpr std::size_t kParallelPixels = 16384;     // abaixo disso a fila de threads custa mais que a conta

    // Pesos gaussianos 1D (LUT) e o peso total, que não depende da posição: toda tomada soma o seu peso, mesmo
    // quando a coordenada é limitada à borda.
    void buildWeights(double sigma) {
        m_weights.resize(static_cast<std::size_t>(2 * m_radius + 1));
        for (int k = -m_radius; k <= m_radius; ++k) {
            m_weights[static_cast<std::size_t>(k + m_radius)] = static_cast<float>(std::exp(-(k * k) / (2.0 * sigma * sigma)));
        }
        float horizontalTotal = 0.0f;
        for (const float w : m_weights) horizontalTotal += w;
        m_totalWeight = 0.0f;
        for (const float w : m_weights) m_totalWeight += horizontalTotal * w;
    }

    // A área da camada nos cinco planos; o que não tem tile é transparente.
    void loadPlanes(canvas::TileGrid& grid) {
        constexpr int kTile = canvas::Tile::TILE_SIZE;
        constexpr float kMaxAlpha = static_cast<float>(canvas::PixelTraits<Pixel>::kMax);
        const std::size_t plane = static_cast<std::size_t>(m_snapWidth) * static_cast<std::size_t>(m_snapHeight);
        m_scratch.source.resize(plane * kPlaneCount);

        for (int sy = 0; sy < m_snapHeight; ++sy) {
            const int gy = m_snap.minY + sy;
            const std::size_t rowStart = static_cast<std::size_t>(sy) * static_cast<std::size_t>(m_snapWidth);
            for (int sx = 0; sx < m_snapWidth;) {
                const int gx = m_snap.minX + sx;
                const int run = std::min(m_snapWidth - sx, (gx / kTile + 1) * kTile - gx);
                canvas::Tile* tile = grid.getTile(gx / kTile, gy / kTile);
                const Pixel* source =
                    tile ? tile->getBuffer().template pixels<Pixel>() + (gy % kTile) * kTile + (gx % kTile) : nullptr;
                float* out = m_scratch.source.data() + rowStart + static_cast<std::size_t>(sx);
                for (int i = 0; i < run; ++i) {
                    const float a = source ? static_cast<float>(source[i].a) : 0.0f;
                    const float alpha = a / kMaxAlpha;
                    const float r = source ? static_cast<float>(source[i].r) : 0.0f;
                    const float g = source ? static_cast<float>(source[i].g) : 0.0f;
                    const float b = source ? static_cast<float>(source[i].b) : 0.0f;
                    out[kRed * plane + i] = r * alpha;
                    out[kGreen * plane + i] = g * alpha;
                    out[kBlue * plane + i] = b * alpha;
                    out[kAlpha * plane + i] = a;
                    out[kAlphaWeight * plane + i] = alpha;
                }
                sx += run;
            }
        }
    }

    // Passe horizontal: cada linha é independente.
    void blurRows() {
        const std::size_t plane = static_cast<std::size_t>(m_snapWidth) * static_cast<std::size_t>(m_snapHeight);
        m_scratch.horizontal.resize(plane * kPlaneCount);
        const int rows = m_snapHeight;
        const float* source = m_scratch.source.data();
        float* horizontal = m_scratch.horizontal.data();
        #pragma omp parallel for schedule(static) if(plane >= kParallelPixels)
        for (int y = 0; y < rows; ++y) {
            for (int c = 0; c < kPlaneCount; ++c) {
                const std::size_t offset = c * plane + static_cast<std::size_t>(y) * static_cast<std::size_t>(m_snapWidth);
                convolveRow(source + offset, horizontal + offset);
            }
        }
    }

    // Passe vertical, só na região pedida: cada linha de saída soma as linhas do passe horizontal que o kernel alcança.
    void blurColumns() {
        const int rows = m_roi.height();
        const std::size_t snapPlane = static_cast<std::size_t>(m_snapWidth) * static_cast<std::size_t>(m_snapHeight);
        const std::size_t roiPlane = static_cast<std::size_t>(m_roiWidth) * static_cast<std::size_t>(rows);
        m_scratch.blurred.resize(roiPlane * kPlaneCount);
        const int xOffset = m_roi.minX - m_snap.minX;
        const int yOffset = m_roi.minY - m_snap.minY;
        const float* horizontal = m_scratch.horizontal.data();
        float* blurred = m_scratch.blurred.data();
        #pragma omp parallel for schedule(static) if(roiPlane >= kParallelPixels)
        for (int y = 0; y < rows; ++y) {
            for (int c = 0; c < kPlaneCount; ++c) {
                float* out = blurred + c * roiPlane + static_cast<std::size_t>(y) * static_cast<std::size_t>(m_roiWidth);
                for (int x0 = 0; x0 < m_roiWidth; x0 += kBlock) {
                    const int n = std::min(kBlock, m_roiWidth - x0);
                    float sum[kBlock] = {};
                    for (int k = -m_radius; k <= m_radius; ++k) {
                        const int sourceRow = std::clamp(y + yOffset + k, 0, m_snapHeight - 1);
                        const float w = m_weights[static_cast<std::size_t>(k + m_radius)];
                        const float* in = horizontal + c * snapPlane + static_cast<std::size_t>(sourceRow) * static_cast<std::size_t>(m_snapWidth) + xOffset + x0;
                        for (int i = 0; i < n; ++i) sum[i] += in[i] * w;
                    }
                    for (int i = 0; i < n; ++i) out[x0 + i] = sum[i];
                }
            }
        }
    }

    // A convolução de uma linha de um plano. Dentro, onde nenhuma tomada passa da borda, a conta corre por blocos de
    // pixels vizinhos; nas bordas, a coordenada é limitada ao primeiro ou ao último pixel.
    void convolveRow(const float* in, float* out) const {
        const int width = m_snapWidth;
        const int first = m_radius;
        const int last = width - m_radius;  // exclusivo
        const int borderEnd = std::min(first, width);
        for (int x = 0; x < borderEnd; ++x) out[x] = clampedTaps(in, x);
        for (int x = std::max(last, borderEnd); x < width; ++x) out[x] = clampedTaps(in, x);

        for (int x0 = first; x0 < last; x0 += kBlock) {
            const int n = std::min(kBlock, last - x0);
            float sum[kBlock] = {};
            for (int k = -m_radius; k <= m_radius; ++k) {
                const float w = m_weights[static_cast<std::size_t>(k + m_radius)];
                const float* src = in + x0 + k;
                for (int i = 0; i < n; ++i) sum[i] += src[i] * w;
            }
            for (int i = 0; i < n; ++i) out[x0 + i] = sum[i];
        }
    }

    [[nodiscard]] float clampedTaps(const float* in, int x) const {
        float sum = 0.0f;
        for (int k = -m_radius; k <= m_radius; ++k) {
            sum += in[std::clamp(x + k, 0, m_snapWidth - 1)] * m_weights[static_cast<std::size_t>(k + m_radius)];
        }
        return sum;
    }

    BlurScratch& m_scratch;
    int m_radius;
    BlurBox m_roi;
    BlurBox m_snap;
    int m_snapWidth{0};
    int m_snapHeight{0};
    int m_roiWidth{0};
    float m_totalWeight{0.0f};
    std::vector<float> m_weights;
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_BLURRED_REGION_HPP
