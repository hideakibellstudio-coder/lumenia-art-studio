#include "SmudgeEngine.hpp"
#include "../canvas/GridSnapshot.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../../utils/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>
#include <vector>

namespace aladyn::engine::engines {

// Amostra segura direta no TileGrid
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

// Amostragem Gaussiana ponderada otimizada da área do dab na CAMADA ATIVA
static utils::ColorRGBA sampleDabArea(
    double cx, double cy, double radius,
    const canvas::TileGrid& tileGrid
) {
    const int iR = static_cast<int>(std::ceil(radius));
    const int step = std::max(1, iR / 12); // Subamostragem inteligente em pincéis gigantes

    const int x0 = static_cast<int>(std::floor(cx)) - iR;
    const int y0 = static_cast<int>(std::floor(cy)) - iR;
    const int x1 = static_cast<int>(std::ceil(cx))  + iR;
    const int y1 = static_cast<int>(std::ceil(cy))  + iR;

    double sumR = 0.0, sumG = 0.0, sumB = 0.0, sumA = 0.0;
    double totalWeight    = 0.0;
    double alphaWeightSum = 0.0;
    const double sigma    = std::max(1.0, radius * 0.45);
    const double sigmaFactor = 1.0 / (2.0 * sigma * sigma);

    for (int sy = y0; sy <= y1; sy += step) {
        const double dy = static_cast<double>(sy) + 0.5 - cy;
        for (int sx = x0; sx <= x1; sx += step) {
            const double dx   = static_cast<double>(sx) + 0.5 - cx;
            const double distSq = dx * dx + dy * dy;
            if (distSq > (radius + 1.0) * (radius + 1.0)) continue;

            const double w = std::exp(-distSq * sigmaFactor);
            const utils::ColorRGBA s = getTilePixel(tileGrid, sx, sy);

            if (s.a > 0) {
                const double aNorm = static_cast<double>(s.a) / 255.0;
                sumR += s.r * aNorm * w;
                sumG += s.g * aNorm * w;
                sumB += s.b * aNorm * w;
                alphaWeightSum += aNorm * w;
            }
            sumA += s.a * w;
            totalWeight += w;
        }
    }

    if (alphaWeightSum <= 0.0) return {0, 0, 0, 0};

    return utils::ColorRGBA{
        static_cast<uint8_t>(std::clamp(sumR / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(sumG / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(sumB / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(sumA / totalWeight, 0.0, 255.0))
    };
}

void SmudgeEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r       = dab.radius;
    const double aspect  = std::max(0.05, profile.tip.aspectRatio);
    const double maxR    = r / aspect + 2.0;

    const double pickup  = std::clamp(profile.smudgeParams.colorPickup, 0.0, 1.0);
    const double mixRate = std::clamp(profile.smudgeParams.mixRatio, 0.0, 1.0);
    const double stretch = std::clamp(profile.smudgeParams.smudgeStretch, 0.0, 1.0);

    // Amostragem da camada ativa
    const utils::ColorRGBA sampledColor = sampleDabArea(dab.position.x, dab.position.y, r, tileGrid);

    // Lógica de Coleta e Arrasto
    if (!m_hasCarriedColor) {
        m_carriedColor    = sampledColor;
        m_lastPosition    = dab.position;
        m_hasCarriedColor = true;
    } else {
        if (sampledColor.a > 0) {
            if (m_carriedColor.a == 0) {
                m_carriedColor = sampledColor;
            } else {
                const double blendRate = pickup * (1.0 - stretch * 0.6) * 0.4;
                m_carriedColor.r = static_cast<uint8_t>(
                    m_carriedColor.r * (1.0 - blendRate) + sampledColor.r * blendRate);
                m_carriedColor.g = static_cast<uint8_t>(
                    m_carriedColor.g * (1.0 - blendRate) + sampledColor.g * blendRate);
                m_carriedColor.b = static_cast<uint8_t>(
                    m_carriedColor.b * (1.0 - blendRate) + sampledColor.b * blendRate);
                m_carriedColor.a = static_cast<uint8_t>(
                    m_carriedColor.a * (1.0 - blendRate) + sampledColor.a * blendRate);
            }
        } else {
            const double decay = 0.92 + stretch * 0.07;
            m_carriedColor.a   = static_cast<uint8_t>(
                std::clamp(static_cast<double>(m_carriedColor.a) * decay, 0.0, 255.0));
        }
    }

    if (m_carriedColor.a == 0) {
        m_lastPosition = dab.position;
        return;
    }

    const double moveDX   = dab.position.x - m_lastPosition.x;
    const double moveDY   = dab.position.y - m_lastPosition.y;
    const double moveDist = std::sqrt(moveDX * moveDX + moveDY * moveDY);
    const double smearOffsetX = (moveDist > 0.01) ? (-moveDX / moveDist * r * stretch * 0.5) : 0.0;
    const double smearOffsetY = (moveDist > 0.01) ? (-moveDY / moveDist * r * stretch * 0.5) : 0.0;
    m_lastPosition = dab.position;

    const utils::Rect2D bounds{
        dab.position.x - maxR, dab.position.y - maxR,
        maxR * 2.0, maxR * 2.0
    };
    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds, tileGrid.getWidth(), tileGrid.getHeight()
    );

    // O rastro lê o que estava sob o dab ANTES de ele pintar. Lendo a grade viva,
    // o pixel já escrito entra na amostra do vizinho e o resultado passa a depender
    // de por onde os tiles e as linhas são varridos (achado D15, 2026-10-01).
    const bool smearsTrail = moveDist > 0.5 && stretch > 0.05;
    if (smearsTrail) {
        const int reach = static_cast<int>(std::ceil(std::max(std::abs(smearOffsetX), std::abs(smearOffsetY)))) + 1;
        m_trailSource.capture(
            tileGrid,
            static_cast<int>(std::floor(bounds.getLeft())) - reach,
            static_cast<int>(std::floor(bounds.getTop())) - reach,
            static_cast<int>(std::ceil(bounds.getRight())) + reach,
            static_cast<int>(std::ceil(bounds.getBottom())) + reach);
    }

    const double radAngle = -dab.angle * (3.14159265358979323846 / 180.0);
    const double cosA     = std::cos(radAngle);
    const double sinA     = std::sin(radAngle);

    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
    const double spanInv  = 1.0 / std::max(0.001, r - hardSpan);

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

        bool tileModified = false;

        for (int py = minY; py <= maxY; ++py) {
            const int globalY = tilePixelY + py;
            const double dy   = static_cast<double>(globalY) + 0.5 - dab.position.y;

            for (int px = minX; px <= maxX; ++px) {
                const int globalX = tilePixelX + px;
                const double dx   = static_cast<double>(globalX) + 0.5 - dab.position.x;

                const double rotX   = dx * cosA - dy * sinA;
                const double rotY   = dx * sinA + dy * cosA;
                const double scaledY = rotY / aspect;
                const double distSq = rotX * rotX + scaledY * scaledY;

                if (distSq > (r + 1.0) * (r + 1.0)) continue;
                const double dist = std::sqrt(distSq);

                double shapeAlpha = 1.0;
                if (dist > hardSpan) {
                    const double t = std::clamp((r - dist) * spanInv, 0.0, 1.0);
                    shapeAlpha = t * t * (3.0 - 2.0 * t);
                }

                const double depositFactor = dab.opacity * shapeAlpha * mixRate;
                if (depositFactor <= 0.0) continue;

                double curDepositFactor = depositFactor;
                if (ctx.selectionMask && ctx.selectionMask->hasSelection()) {
                    const uint8_t sVal = ctx.selectionMask->getValue(globalX, globalY);
                    if (sVal == 0) continue;
                    if (sVal < 255) {
                        curDepositFactor *= (static_cast<double>(sVal) / 255.0);
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
                    curDepositFactor *= baseA;
                }
                if (curDepositFactor <= 0.0) continue;

                // Lookup O(1) do rastro direcional, na foto tirada antes do dab
                utils::ColorRGBA sourceColorForSmear = m_carriedColor;
                if (smearsTrail) {
                    const int sampleX = static_cast<int>(std::round(static_cast<double>(globalX) + smearOffsetX));
                    const int sampleY = static_cast<int>(std::round(static_cast<double>(globalY) + smearOffsetY));
                    const utils::ColorRGBA trailSample = m_trailSource.at(sampleX, sampleY);

                    if (trailSample.a > 0) {
                        const double trailMix = stretch * 0.4;
                        sourceColorForSmear.r = static_cast<uint8_t>(
                            m_carriedColor.r * (1.0 - trailMix) + trailSample.r * trailMix);
                        sourceColorForSmear.g = static_cast<uint8_t>(
                            m_carriedColor.g * (1.0 - trailMix) + trailSample.g * trailMix);
                        sourceColorForSmear.b = static_cast<uint8_t>(
                            m_carriedColor.b * (1.0 - trailMix) + trailSample.b * trailMix);
                        sourceColorForSmear.a = static_cast<uint8_t>(
                            m_carriedColor.a * (1.0 - trailMix) + trailSample.a * trailMix);
                    }
                }

                const utils::ColorRGBA dst = buffer.getPixel(px, py);

                if (ctx.alphaLocked) {
                    if (dst.a == 0) continue;
                    const double srcA    = (static_cast<double>(sourceColorForSmear.a) / 255.0) * curDepositFactor;
                    const double dstA    = static_cast<double>(dst.a) / 255.0;
                    const double invSrcA = 1.0 - srcA;
                    const double denom   = srcA + dstA * invSrcA;
                    if (denom <= 0.0) continue;

                    const double outR = (sourceColorForSmear.r * srcA + dst.r * dstA * invSrcA) / denom;
                    const double outG = (sourceColorForSmear.g * srcA + dst.g * dstA * invSrcA) / denom;
                    const double outB = (sourceColorForSmear.b * srcA + dst.b * dstA * invSrcA) / denom;

                    buffer.setPixel(px, py, utils::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                        dst.a
                    });
                    tileModified = true;
                    continue;
                }

                const double srcA = (static_cast<double>(sourceColorForSmear.a) / 255.0) * curDepositFactor;
                const double dstA = static_cast<double>(dst.a) / 255.0;
                const double outA = srcA + dstA * (1.0 - srcA);

                if (outA > 0.0) {
                    const double outR = (sourceColorForSmear.r * srcA + dst.r * dstA * (1.0 - srcA)) / outA;
                    const double outG = (sourceColorForSmear.g * srcA + dst.g * dstA * (1.0 - srcA)) / outA;
                    const double outB = (sourceColorForSmear.b * srcA + dst.b * dstA * (1.0 - srcA)) / outA;

                    buffer.setPixel(px, py, utils::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
                    });
                    tileModified = true;
                }
            }
        }
        if (tileModified) tile->setDirty(true);
    }
}

} // namespace aladyn::engine::engines
