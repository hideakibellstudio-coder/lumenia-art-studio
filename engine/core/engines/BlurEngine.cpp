#include "BlurEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../../utils/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>
#include <vector>

namespace aladyn::engine::engines {

// Amostra segura na TileGrid da camada ativa
static inline utils::ColorRGBA getTilePixel(const canvas::TileGrid& tileGrid, int globalX, int globalY) {
    if (globalX < 0 || globalX >= tileGrid.getWidth() || globalY < 0 || globalY >= tileGrid.getHeight()) {
        return {0, 0, 0, 0};
    }
    const int tx  = globalX / canvas::Tile::TILE_SIZE;
    const int ty  = globalY / canvas::Tile::TILE_SIZE;
    const int lpx = globalX % canvas::Tile::TILE_SIZE;
    const int lpy = globalY % canvas::Tile::TILE_SIZE;

    const canvas::Tile* t = const_cast<canvas::TileGrid&>(tileGrid).getTile(tx, ty);
    return t ? t->getBuffer().getPixel(lpx, lpy) : utils::ColorRGBA{0, 0, 0, 0};
}

void BlurEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const canvas::PixelBuffer* /*compositeBuffer*/,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r      = dab.radius;
    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const double maxR   = r / aspect + 2.0;

    const int blurRadiusCfg = std::clamp(profile.blurParams.blurRadius, 1, 5);
    const double blurStr    = std::clamp(profile.blurParams.blurStrength, 0.0, 1.0);

    // Raio do kernel proporcional ao dab (mínimo 2px, máximo 20px)
    const int kernelR = std::clamp(
        static_cast<int>(std::round(r * 0.20 * static_cast<double>(blurRadiusCfg))),
        2, 20
    );
    const double sigma = std::max(0.8, static_cast<double>(kernelR) * (0.35 + blurStr * 0.45));

    // Bounding Box do Dab expandida com margem de segurança do kernel
    const int roiMinX = std::max(0, static_cast<int>(std::floor(dab.position.x - maxR)));
    const int roiMaxX = std::min(tileGrid.getWidth() - 1, static_cast<int>(std::ceil(dab.position.x + maxR)));
    const int roiMinY = std::max(0, static_cast<int>(std::floor(dab.position.y - maxR)));
    const int roiMaxY = std::min(tileGrid.getHeight() - 1, static_cast<int>(std::ceil(dab.position.y + maxR)));

    const int roiW = roiMaxX - roiMinX + 1;
    const int roiH = roiMaxY - roiMinY + 1;
    if (roiW <= 0 || roiH <= 0) return;

    // Snapshot expandido contíguo em RAM (inclui a borda kernelR para amostragem ultrarrápida O(1))
    const int snapMinX = std::max(0, roiMinX - kernelR);
    const int snapMaxX = std::min(tileGrid.getWidth() - 1, roiMaxX + kernelR);
    const int snapMinY = std::max(0, roiMinY - kernelR);
    const int snapMaxY = std::min(tileGrid.getHeight() - 1, roiMaxY + kernelR);

    const int snapW = snapMaxX - snapMinX + 1;
    const int snapH = snapMaxY - snapMinY + 1;
    if (snapW <= 0 || snapH <= 0) return;

    std::vector<utils::ColorRGBA> srcBlock(static_cast<size_t>(snapW * snapH));
    for (int sy = 0; sy < snapH; ++sy) {
        const int gy = snapMinY + sy;
        for (int sx = 0; sx < snapW; ++sx) {
            const int gx = snapMinX + sx;
            srcBlock[static_cast<size_t>(sy * snapW + sx)] = getTilePixel(tileGrid, gx, gy);
        }
    }

    // ─── 1. PRÉ-CÁLCULO DOS PESOS GAUSSIANOS 1D (LUT) ─────────────────────────
    const int kernelSize = 2 * kernelR + 1;
    std::vector<float> kernelWeights(static_cast<size_t>(kernelSize));
    for (int k = -kernelR; k <= kernelR; ++k) {
        kernelWeights[static_cast<size_t>(k + kernelR)] =
            static_cast<float>(std::exp(-(k * k) / (2.0 * sigma * sigma)));
    }

    // ─── 2. CONVOLUÇÃO SEPARÁVEL EM 2 PASSES (HORIZONTAL + VERTICAL) ──────────
    // Reduz a complexidade de O(K^2) para O(2*K) — 12.5x mais rápido!

    // Buffer intermediário (resultado do passe horizontal)
    struct IntermediateSample {
        float r{0.0f}, g{0.0f}, b{0.0f}, a{0.0f};
        float alphaW{0.0f}, totalW{0.0f};
    };
    std::vector<IntermediateSample> tempBlock(static_cast<size_t>(snapW * snapH));

    // Passo Horizontal (1D)
    for (int sy = 0; sy < snapH; ++sy) {
        const int rowOffset = sy * snapW;
        for (int sx = 0; sx < snapW; ++sx) {
            float sumR = 0.0f, sumG = 0.0f, sumB = 0.0f, sumA = 0.0f;
            float aWSum = 0.0f, tWSum = 0.0f;

            for (int k = -kernelR; k <= kernelR; ++k) {
                const int kx = std::clamp(sx + k, 0, snapW - 1);
                const float w = kernelWeights[static_cast<size_t>(k + kernelR)];
                const utils::ColorRGBA px = srcBlock[static_cast<size_t>(rowOffset + kx)];

                const float aNorm = static_cast<float>(px.a) / 255.0f;
                if (px.a > 0) {
                    sumR += static_cast<float>(px.r) * aNorm * w;
                    sumG += static_cast<float>(px.g) * aNorm * w;
                    sumB += static_cast<float>(px.b) * aNorm * w;
                    aWSum += aNorm * w;
                }
                sumA += static_cast<float>(px.a) * w;
                tWSum += w;
            }

            tempBlock[static_cast<size_t>(rowOffset + sx)] = IntermediateSample{
                sumR, sumG, sumB, sumA, aWSum, tWSum
            };
        }
    }

    // Passo Vertical (1D) + Aplicação do Dab na TileGrid
    const utils::Rect2D bounds{
        dab.position.x - maxR, dab.position.y - maxR,
        maxR * 2.0, maxR * 2.0
    };
    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds, tileGrid.getWidth(), tileGrid.getHeight()
    );

    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
    const double spanInv  = 1.0 / std::max(0.001, r - hardSpan);

    for (const auto& idx : tileIndices) {
        canvas::Tile* tile = tileGrid.getOrCreateTile(idx.x, idx.y);
        if (!tile) continue;

        canvas::PixelBuffer& buffer = tile->getBuffer();
        const int tilePixelX = tile->getPixelX();
        const int tilePixelY = tile->getPixelY();

        const int minX = std::max(0, roiMinX - tilePixelX);
        const int maxX = std::min(canvas::Tile::TILE_SIZE - 1, roiMaxX - tilePixelX);
        const int minY = std::max(0, roiMinY - tilePixelY);
        const int maxY = std::min(canvas::Tile::TILE_SIZE - 1, roiMaxY - tilePixelY);

        bool tileModified = false;

        for (int py = minY; py <= maxY; ++py) {
            const int globalY = tilePixelY + py;
            const double dy   = static_cast<double>(globalY) + 0.5 - dab.position.y;
            const int snapY   = globalY - snapMinY;

            for (int px = minX; px <= maxX; ++px) {
                const int globalX = tilePixelX + px;
                const double dx   = static_cast<double>(globalX) + 0.5 - dab.position.x;
                const int snapX   = globalX - snapMinX;

                const double dist = std::sqrt(dx * dx + dy * dy);
                if (dist > r + 1.0) continue;

                // Falloff smoothstep
                double shapeAlpha = 1.0;
                if (dist > hardSpan) {
                    const double t = std::clamp((r - dist) * spanInv, 0.0, 1.0);
                    shapeAlpha = t * t * (3.0 - 2.0 * t);
                }
                if (shapeAlpha <= 0.0) continue;

                const double mixFactor = dab.opacity * shapeAlpha * blurStr;
                if (mixFactor <= 0.0) continue;

                const utils::ColorRGBA origPx = srcBlock[static_cast<size_t>(snapY * snapW + snapX)];

                // Acumulação vertical dos resultados intermediários
                float sumR = 0.0f, sumG = 0.0f, sumB = 0.0f, sumA = 0.0f;
                float aWSum = 0.0f, tWSum = 0.0f;

                for (int k = -kernelR; k <= kernelR; ++k) {
                    const int ky = std::clamp(snapY + k, 0, snapH - 1);
                    const float w = kernelWeights[static_cast<size_t>(k + kernelR)];
                    const IntermediateSample& sample = tempBlock[static_cast<size_t>(ky * snapW + snapX)];

                    sumR += sample.r * w;
                    sumG += sample.g * w;
                    sumB += sample.b * w;
                    sumA += sample.a * w;
                    aWSum += sample.alphaW * w;
                    tWSum += sample.totalW * w;
                }

                // Se não há tinta e o pixel é vazio, ignora
                if (origPx.a == 0 && aWSum <= 0.0f) continue;
                if (ctx.alphaLocked && origPx.a == 0) continue;

                double curMixFactor = mixFactor;
                if (ctx.selectionMask && ctx.selectionMask->hasSelection()) {
                    const uint8_t sVal = ctx.selectionMask->getValue(globalX, globalY);
                    if (sVal == 0) continue;
                    if (sVal < 255) {
                        curMixFactor *= (static_cast<double>(sVal) / 255.0);
                    }
                }

                if (ctx.clipBaseLayer) {
                    const int bTx = globalX / canvas::Tile::TILE_SIZE;
                    const int bTy = globalY / canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(
                        globalX % canvas::Tile::TILE_SIZE,
                        globalY % canvas::Tile::TILE_SIZE).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curMixFactor *= baseA;
                }
                if (curMixFactor <= 0.0) continue;

                float targetR = static_cast<float>(origPx.r);
                float targetG = static_cast<float>(origPx.g);
                float targetB = static_cast<float>(origPx.b);
                if (aWSum > 0.0f) {
                    targetR = sumR / aWSum;
                    targetG = sumG / aWSum;
                    targetB = sumB / aWSum;
                }

                const double outR = static_cast<double>(origPx.r) * (1.0 - curMixFactor) + static_cast<double>(targetR) * curMixFactor;
                const double outG = static_cast<double>(origPx.g) * (1.0 - curMixFactor) + static_cast<double>(targetG) * curMixFactor;
                const double outB = static_cast<double>(origPx.b) * (1.0 - curMixFactor) + static_cast<double>(targetB) * curMixFactor;

                double outA = static_cast<double>(origPx.a);
                if (!ctx.alphaLocked) {
                    const double smoothedA = (tWSum > 0.0f) ? static_cast<double>(sumA / tWSum) : static_cast<double>(origPx.a);
                    outA = static_cast<double>(origPx.a) * (1.0 - curMixFactor) + smoothedA * curMixFactor;
                }

                buffer.setPixel(px, py, utils::ColorRGBA{
                    static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                    static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                    static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                    static_cast<uint8_t>(std::clamp(outA, 0.0, 255.0))
                });
                tileModified = true;
            }
        }
        if (tileModified) tile->setDirty(true);
    }
}

} // namespace aladyn::engine::engines
