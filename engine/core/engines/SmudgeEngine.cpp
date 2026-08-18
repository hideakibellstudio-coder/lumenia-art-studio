
#include "SmudgeEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

// ─── HELPER: Amostragem Gaussiana de uma área circular no compositeBuffer.
// Retorna a cor média ponderada de toda a impressão do dab, não apenas 1 pixel.
// Resolve problema #1 (amostragem de 1 pixel) e #2 (leitura da camada errada).
static raster::ColorRGBA sampleDabArea(
    double cx, double cy, double radius,
    const canvas::PixelBuffer* compositeBuffer,
    const canvas::TileGrid& tileGrid
) {
    const int iR = static_cast<int>(std::ceil(radius));
    const int x0 = static_cast<int>(std::floor(cx)) - iR;
    const int y0 = static_cast<int>(std::floor(cy)) - iR;
    const int x1 = static_cast<int>(std::ceil(cx))  + iR;
    const int y1 = static_cast<int>(std::ceil(cy))  + iR;

    double sumR = 0.0, sumG = 0.0, sumB = 0.0, sumA = 0.0;
    double totalWeight    = 0.0;
    double alphaWeightSum = 0.0;
    const double sigma    = std::max(1.0, radius * 0.4);

    for (int sy = y0; sy <= y1; ++sy) {
        const double dy = static_cast<double>(sy) + 0.5 - cy;
        for (int sx = x0; sx <= x1; ++sx) {
            const double dx   = static_cast<double>(sx) + 0.5 - cx;
            const double dist = std::sqrt(dx * dx + dy * dy);
            if (dist > radius + 1.0) continue;

            // Peso gaussiano caindo suavemente até o raio
            const double w     = std::exp(-(dist * dist) / (2.0 * sigma * sigma));
            raster::ColorRGBA s{0, 0, 0, 0};

            if (compositeBuffer) {
                s = compositeBuffer->getPixel(sx, sy);
            } else {
                const int tx  = sx / canvas::Tile::TILE_SIZE;
                const int ty  = sy / canvas::Tile::TILE_SIZE;
                const int lpx = sx % canvas::Tile::TILE_SIZE;
                const int lpy = sy % canvas::Tile::TILE_SIZE;
                if (tx >= 0 && tx < tileGrid.getTilesCountX() && ty >= 0 && ty < tileGrid.getTilesCountY()) {
                    const canvas::Tile* t = const_cast<canvas::TileGrid&>(tileGrid).getTile(tx, ty);
                    if (t) s = t->getBuffer().getPixel(lpx, lpy);
                }
            }

            const double aNorm = static_cast<double>(s.a) / 255.0;
            sumR += s.r * aNorm * w;
            sumG += s.g * aNorm * w;
            sumB += s.b * aNorm * w;
            sumA += aNorm * w;

            totalWeight    += w;
            alphaWeightSum += aNorm * w;
        }
    }

    if (alphaWeightSum <= 0.0) return {0, 0, 0, 0};

    return raster::ColorRGBA{
        static_cast<uint8_t>(std::clamp(sumR / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(sumG / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(sumB / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp((sumA / totalWeight) * 255.0, 0.0, 255.0))
    };
}

void SmudgeEngine::renderDab(
    const raster::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const canvas::PixelBuffer* compositeBuffer,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r       = dab.radius;
    const double aspect  = std::max(0.05, profile.tip.aspectRatio);
    const double maxR    = r / aspect + 2.0;

    const double pickup  = std::clamp(profile.smudgeParams.colorPickup, 0.0, 1.0);
    const double mixRate = std::clamp(profile.smudgeParams.mixRatio, 0.0, 1.0);
    const double stretch = std::clamp(profile.smudgeParams.smudgeStretch, 0.0, 1.0);

    // ─── CORREÇÃO #1 & #2: Amostragem média ponderada de toda a área do dab
    // do compositeBuffer (o que o artista VÊ), não apenas 1 pixel da camada ativa.
    const raster::ColorRGBA sampledColor = sampleDabArea(
        dab.position.x, dab.position.y, r,
        compositeBuffer, tileGrid
    );

    // ─── Lógica de Coleta e Arrasto com acumulação progressiva
    if (!m_hasCarriedColor) {
        // Primeiro dab do traço: carrega a "impressão digital" completa do que está abaixo
        m_carriedColor    = sampledColor;
        m_lastPosition    = dab.position;
        m_hasCarriedColor = true;
    } else {
        // Dabs subsequentes: mistura progressiva da tinta mantida com a nova amostra
        if (sampledColor.a > 0) {
            if (m_carriedColor.a == 0) {
                // Ao cruzar área pintada com pincel limpo: coleta imediatamente
                m_carriedColor = sampledColor;
            } else {
                // Blending bidirecional: pickup controla quanto da tela entra na tinta mantida
                // stretch controla a resistência ao escoamento (quanto a tinta se mantém fiel)
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
            // Área transparente: tinta decai gradualmente (fim do arrasto)
            const double decay  = 0.88 + stretch * 0.11;
            m_carriedColor.a    = static_cast<uint8_t>(
                std::clamp(static_cast<double>(m_carriedColor.a) * decay, 0.0, 255.0));
        }
    }

    // Sem tinta para depositar → nada a desenhar
    if (m_carriedColor.a == 0) {
        m_lastPosition = dab.position;
        return;
    }

    // ─── CORREÇÃO #3: Offset direcional de smear
    // O "arrasto" verdadeiro ocorre depositando a cor mantida na posição ATUAL
    // enquanto lê da posição ANTERIOR — criando o efeito de mover tinta pela tela.
    // O vetor de movimento é usado para deslocar o ponto de leitura no sentido oposto ao traço.
    const double moveDX   = dab.position.x - m_lastPosition.x;
    const double moveDY   = dab.position.y - m_lastPosition.y;
    const double moveDist = std::sqrt(moveDX * moveDX + moveDY * moveDY);
    const double smearOffsetX = (moveDist > 0.01) ? (-moveDX / moveDist * r * stretch * 0.5) : 0.0;
    const double smearOffsetY = (moveDist > 0.01) ? (-moveDY / moveDist * r * stretch * 0.5) : 0.0;
    m_lastPosition = dab.position;

    // ─── Depositação com forma do dab na camada ativa
    const math::Rect2D bounds{
        dab.position.x - maxR, dab.position.y - maxR,
        maxR * 2.0, maxR * 2.0
    };
    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds, tileGrid.getWidth(), tileGrid.getHeight()
    );

    const double radAngle = -dab.angle * (3.14159265358979323846 / 180.0);
    const double cosA     = std::cos(radAngle);
    const double sinA     = std::sin(radAngle);

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
            const double dy = static_cast<double>(tilePixelY + py) + 0.5 - dab.position.y;
            for (int px = minX; px <= maxX; ++px) {
                const double dx = static_cast<double>(tilePixelX + px) + 0.5 - dab.position.x;

                const double rotX   = dx * cosA - dy * sinA;
                const double rotY   = dx * sinA + dy * cosA;
                const double scaledY = rotY / aspect;
                const double dist   = std::sqrt(rotX * rotX + scaledY * scaledY);

                if (dist > r + 1.0) continue;

                // Falloff smoothstep
                double shapeAlpha = 1.0;
                const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
                if (dist > hardSpan) {
                    const double span = std::max(0.001, r - hardSpan);
                    const double t    = std::clamp((r - dist) / span, 0.0, 1.0);
                    shapeAlpha = t * t * (3.0 - 2.0 * t);
                }

                const double depositFactor = dab.opacity * shapeAlpha * mixRate;
                if (depositFactor <= 0.0) continue;

                double curDepositFactor = depositFactor;
                if (ctx.clipBaseLayer) {
                    const int globalX = tilePixelX + px;
                    const int globalY = tilePixelY + py;
                    const int bTx = globalX / canvas::Tile::TILE_SIZE;
                    const int bTy = globalY / canvas::Tile::TILE_SIZE;
                    const int bPx = globalX % canvas::Tile::TILE_SIZE;
                    const int bPy = globalY % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curDepositFactor *= baseA;
                }
                if (curDepositFactor <= 0.0) continue;

                // ─── CORREÇÃO #3: Lê a cor da posição de "trás" (offset direcional)
                // para criar o efeito real de arrastar tinta na direção do movimento.
                // A tinta da posição anterior é depositada na posição atual.
                raster::ColorRGBA sourceColorForSmear = m_carriedColor;
                if (moveDist > 0.5 && stretch > 0.05) {
                    const int sampleX = static_cast<int>(std::round(
                        static_cast<double>(tilePixelX + px) + smearOffsetX));
                    const int sampleY = static_cast<int>(std::round(
                        static_cast<double>(tilePixelY + py) + smearOffsetY));
                    const raster::ColorRGBA trailSample = (compositeBuffer)
                        ? compositeBuffer->getPixel(sampleX, sampleY)
                        : sampleDabArea(sampleX, sampleY, 1.0, compositeBuffer, tileGrid);

                    if (trailSample.a > 0) {
                        const double trailMix = stretch * 0.5;
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

                const raster::ColorRGBA dst = buffer.getPixel(px, py);

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

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                        dst.a
                    });
                    tileModified = true;
                    continue;
                }

                // Composição "over" normal: deposita tinta arrastada sobre a camada ativa
                const double srcA = (static_cast<double>(sourceColorForSmear.a) / 255.0) * curDepositFactor;
                const double dstA = static_cast<double>(dst.a) / 255.0;
                const double outA = srcA + dstA * (1.0 - srcA);

                if (outA > 0.0) {
                    const double outR = (sourceColorForSmear.r * srcA + dst.r * dstA * (1.0 - srcA)) / outA;
                    const double outG = (sourceColorForSmear.g * srcA + dst.g * dstA * (1.0 - srcA)) / outA;
                    const double outB = (sourceColorForSmear.b * srcA + dst.b * dstA * (1.0 - srcA)) / outA;

                    buffer.setPixel(px, py, raster::ColorRGBA{
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
