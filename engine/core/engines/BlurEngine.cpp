#include "BlurEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>
#include <vector>

namespace aladyn::engine::engines {

// Helper de amostragem na grade de tiles da camada ativa
static raster::ColorRGBA sampleActiveLayer(int globalX, int globalY, const canvas::TileGrid& tileGrid) {
    const int tx  = globalX / canvas::Tile::TILE_SIZE;
    const int ty  = globalY / canvas::Tile::TILE_SIZE;
    const int lpx = globalX % canvas::Tile::TILE_SIZE;
    const int lpy = globalY % canvas::Tile::TILE_SIZE;

    if (tx >= 0 && tx < tileGrid.getTilesCountX() && ty >= 0 && ty < tileGrid.getTilesCountY()) {
        const canvas::Tile* t = const_cast<canvas::TileGrid&>(tileGrid).getTile(tx, ty);
        if (t) return t->getBuffer().getPixel(lpx, lpy);
    }
    return {0, 0, 0, 0};
}

void BlurEngine::renderDab(
    const raster::Dab& dab,
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

    const math::Rect2D bounds{
        dab.position.x - maxR, dab.position.y - maxR,
        maxR * 2.0, maxR * 2.0
    };

    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds, tileGrid.getWidth(), tileGrid.getHeight()
    );

    const int blurRadiusCfg = std::clamp(profile.blurParams.blurRadius, 1, 5);
    const double blurStr    = std::clamp(profile.blurParams.blurStrength, 0.0, 1.0);

    // Raio do kernel proporcional ao pincel e configuração (mínimo 2px, máximo 24px)
    const int kernelR = std::clamp(
        static_cast<int>(std::round(r * 0.25 * static_cast<double>(blurRadiusCfg))),
        2, 24
    );
    const double sigma = std::max(0.8, static_cast<double>(kernelR) * (0.35 + blurStr * 0.45));

    for (const auto& idx : tileIndices) {
        canvas::Tile* tile = tileGrid.getOrCreateTile(idx.x, idx.y);
        if (!tile) continue;

        canvas::PixelBuffer& buffer = tile->getBuffer();
        const int tilePixelX = tile->getPixelX();
        const int tilePixelY = tile->getPixelY();

        const int minX = std::max(0, static_cast<int>(std::floor(bounds.getLeft()))  - tilePixelX);
        const int maxX = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(bounds.getRight()))  - tilePixelX);
        const int minY = std::max(0, static_cast<int>(std::floor(bounds.getTop()))   - tilePixelY);
        const int maxY = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(bounds.getBottom())) - tilePixelY);

        const int snapshotW = maxX - minX + 1;
        const int snapshotH = maxY - minY + 1;
        if (snapshotW <= 0 || snapshotH <= 0) continue;

        // Snapshot isolado da região antes de qualquer escrita deste dab
        std::vector<raster::ColorRGBA> snapshot(static_cast<size_t>(snapshotW * snapshotH));
        for (int sy = 0; sy < snapshotH; ++sy) {
            for (int sx = 0; sx < snapshotW; ++sx) {
                snapshot[static_cast<size_t>(sy * snapshotW + sx)] =
                    buffer.getPixel(minX + sx, minY + sy);
            }
        }

        bool tileModified = false;

        for (int py = minY; py <= maxY; ++py) {
            const int globalY = tilePixelY + py;
            const double dy   = static_cast<double>(globalY) + 0.5 - dab.position.y;

            for (int px = minX; px <= maxX; ++px) {
                const int globalX = tilePixelX + px;
                const double dx   = static_cast<double>(globalX) + 0.5 - dab.position.x;

                const double dist = std::sqrt(dx * dx + dy * dy);
                if (dist > r + 1.0) continue;

                // Falloff suave do dab
                double shapeAlpha = 1.0;
                const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
                if (dist > hardSpan) {
                    const double span = std::max(0.001, r - hardSpan);
                    const double t    = std::clamp((r - dist) / span, 0.0, 1.0);
                    shapeAlpha = t * t * (3.0 - 2.0 * t);
                }
                if (shapeAlpha <= 0.0) continue;

                const double mixFactor = dab.opacity * shapeAlpha * blurStr;
                if (mixFactor <= 0.0) continue;

                // Estado original do pixel na camada ativa
                const int si = (py - minY) * snapshotW + (px - minX);
                const raster::ColorRGBA origPx = snapshot[static_cast<size_t>(si)];

                // Convolução Gaussiana sobre os pixels da CAMADA ATIVA
                double sumR = 0.0, sumG = 0.0, sumB = 0.0, sumA = 0.0;
                double totalWeight    = 0.0;
                double alphaWeightSum = 0.0;

                for (int ky = -kernelR; ky <= kernelR; ++ky) {
                    for (int kx = -kernelR; kx <= kernelR; ++kx) {
                        const double w = std::exp(-(kx * kx + ky * ky) / (2.0 * sigma * sigma));
                        const raster::ColorRGBA s = sampleActiveLayer(globalX + kx, globalY + ky, tileGrid);

                        const double aNorm = static_cast<double>(s.a) / 255.0;
                        if (s.a > 0) {
                            sumR += s.r * aNorm * w;
                            sumG += s.g * aNorm * w;
                            sumB += s.b * aNorm * w;
                            alphaWeightSum += aNorm * w;
                        }
                        sumA += s.a * w;
                        totalWeight += w;
                    }
                }

                // Se nem o pixel atual e nem nenhum vizinho tiver tinta na camada ativa, não faz nada (mantém transparente)
                if (origPx.a == 0 && alphaWeightSum <= 0.0) continue;

                if (ctx.alphaLocked && origPx.a == 0) continue;

                // Modulação de máscara de recorte (clipping mask)
                double curMixFactor = mixFactor;
                if (ctx.clipBaseLayer) {
                    const int bTx = globalX / canvas::Tile::TILE_SIZE;
                    const int bTy = globalY / canvas::Tile::TILE_SIZE;
                    const int bPx = globalX % canvas::Tile::TILE_SIZE;
                    const int bPy = globalY % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curMixFactor *= baseA;
                }
                if (curMixFactor <= 0.0) continue;

                // Cor cromática suavizada
                double targetR = static_cast<double>(origPx.r);
                double targetG = static_cast<double>(origPx.g);
                double targetB = static_cast<double>(origPx.b);
                if (alphaWeightSum > 0.0) {
                    targetR = sumR / alphaWeightSum;
                    targetG = sumG / alphaWeightSum;
                    targetB = sumB / alphaWeightSum;
                }

                const double outR = origPx.r * (1.0 - curMixFactor) + targetR * curMixFactor;
                const double outG = origPx.g * (1.0 - curMixFactor) + targetG * curMixFactor;
                const double outB = origPx.b * (1.0 - curMixFactor) + targetB * curMixFactor;

                // Suavização do canal Alpha
                double outA = static_cast<double>(origPx.a);
                if (!ctx.alphaLocked) {
                    const double smoothedA = (totalWeight > 0.0) ? (sumA / totalWeight) : static_cast<double>(origPx.a);
                    outA = origPx.a * (1.0 - curMixFactor) + smoothedA * curMixFactor;
                }

                buffer.setPixel(px, py, raster::ColorRGBA{
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
