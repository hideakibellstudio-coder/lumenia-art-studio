#include "BlurEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void BlurEngine::renderDab(
    const raster::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const canvas::PixelBuffer* /*compositeBuffer*/,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r = dab.radius;
    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const double maxR = r / aspect + 2.0;

    const math::Rect2D bounds{
        dab.position.x - maxR, dab.position.y - maxR,
        maxR * 2.0, maxR * 2.0
    };

    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds, tileGrid.getWidth(), tileGrid.getHeight()
    );

    const int blurR = std::clamp(profile.blurParams.blurRadius, 1, 5);
    const double blurStr = std::clamp(profile.blurParams.blurStrength, 0.0, 1.0);

    for (const auto& idx : tileIndices) {
        canvas::Tile* tile = tileGrid.getOrCreateTile(idx.x, idx.y);
        if (!tile) continue;

        canvas::PixelBuffer& buffer = tile->getBuffer();
        const int tilePixelX = tile->getPixelX();
        const int tilePixelY = tile->getPixelY();

        const int minX = std::max(0, static_cast<int>(std::floor(bounds.getLeft())) - tilePixelX);
        const int maxX = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(bounds.getRight())) - tilePixelX);
        const int minY = std::max(0, static_cast<int>(std::floor(bounds.getTop())) - tilePixelY);
        const int maxY = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(bounds.getBottom())) - tilePixelY);

        bool tileModified = false;

        for (int py = minY; py <= maxY; ++py) {
            const int globalY = tilePixelY + py;
            const double dy = static_cast<double>(globalY) + 0.5 - dab.position.y;

            for (int px = minX; px <= maxX; ++px) {
                const int globalX = tilePixelX + px;
                const double dx = static_cast<double>(globalX) + 0.5 - dab.position.x;

                const double dist = std::sqrt(dx * dx + dy * dy);
                if (dist > r + 1.0) continue;

                // Opacidade do desfoque por falloff
                double shapeAlpha = 1.0;
                const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
                if (dist > hardSpan) {
                    shapeAlpha = std::clamp((r - dist) / std::max(0.001, r - hardSpan), 0.0, 1.0);
                }
                if (shapeAlpha <= 0.0) continue;

                const double mixFactor = dab.opacity * shapeAlpha * blurStr;
                if (mixFactor <= 0.0) continue;

                // Amostragem Alpha-Premultiplied na camada ativa (transparência pura)
                double sumR = 0.0, sumG = 0.0, sumB = 0.0, sumA = 0.0;
                double totalWeight = 0.0;
                double alphaWeightSum = 0.0;

                for (int ky = -blurR; ky <= blurR; ++ky) {
                    const int sampleY = globalY + ky;
                    for (int kx = -blurR; kx <= blurR; ++kx) {
                        const int sampleX = globalX + kx;

                        // Amostragem na grade de tiles da camada ativa (tileGrid)
                        const int tx = sampleX / canvas::Tile::TILE_SIZE;
                        const int ty = sampleY / canvas::Tile::TILE_SIZE;
                        const int lpx = sampleX % canvas::Tile::TILE_SIZE;
                        const int lpy = sampleY % canvas::Tile::TILE_SIZE;

                        raster::ColorRGBA pxColor{0, 0, 0, 0};
                        if (tx >= 0 && tx < tileGrid.getTilesCountX() && ty >= 0 && ty < tileGrid.getTilesCountY()) {
                            const canvas::Tile* sTile = tileGrid.getTile(tx, ty);
                            if (sTile) pxColor = sTile->getBuffer().getPixel(lpx, lpy);
                        }

                        // Peso gaussiano aproximado
                        const double w = std::exp(-(kx * kx + ky * ky) / (2.0 * blurR * blurR));
                        const double aNorm = static_cast<double>(pxColor.a) / 255.0;

                        sumR += pxColor.r * aNorm * w;
                        sumG += pxColor.g * aNorm * w;
                        sumB += pxColor.b * aNorm * w;
                        sumA += pxColor.a * w;

                        totalWeight += w;
                        alphaWeightSum += aNorm * w;
                    }
                }

                double curMixFactor = mixFactor;
                if (ctx.clipBaseLayer) {
                    const int bTx = (tilePixelX + px) / canvas::Tile::TILE_SIZE;
                    const int bTy = (tilePixelY + py) / canvas::Tile::TILE_SIZE;
                    const int bPx = (tilePixelX + px) % canvas::Tile::TILE_SIZE;
                    const int bPy = (tilePixelY + py) % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curMixFactor *= baseA;
                }

                if (curMixFactor <= 0.0) continue;

                const raster::ColorRGBA origPx = buffer.getPixel(px, py);
                if (ctx.alphaLocked && origPx.a == 0) continue;

                // Se o pixel atual e todos os vizinhos forem vazios, não há o que desfocar
                if (origPx.a == 0 && alphaWeightSum <= 0.0) continue;

                // 1. Cor alvo calculada sobre os pixels vizinhos que realmente contêm pigmento
                double targetR = origPx.r;
                double targetG = origPx.g;
                double targetB = origPx.b;

                if (alphaWeightSum > 0.0) {
                    targetR = sumR / alphaWeightSum;
                    targetG = sumG / alphaWeightSum;
                    targetB = sumB / alphaWeightSum;
                }

                // 2. Suavização das cores cromáticas RGB
                const double outR = origPx.r * (1.0 - curMixFactor) + targetR * curMixFactor;
                const double outG = origPx.g * (1.0 - curMixFactor) + targetG * curMixFactor;
                const double outB = origPx.b * (1.0 - curMixFactor) + targetB * curMixFactor;

                // 3. Preservação estrita do Alpha (impede erosão/apagamento tipo borracha)
                double outA = static_cast<double>(origPx.a);
                if (!ctx.alphaLocked) {
                    if (origPx.a > 0) {
                        // Pixel com tinta: seu alpha NUNCA é diminuído por vizinhos vazios
                        const double smoothedA = sumA / totalWeight;
                        outA = std::max(static_cast<double>(origPx.a), smoothedA);
                    } else if (alphaWeightSum > 0.0) {
                        // Pixel vazio vizinho: recebe uma leve dispersão suave da borda
                        const double spreadA = (sumA / totalWeight) * curMixFactor * 0.4;
                        outA = spreadA;
                    }
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
