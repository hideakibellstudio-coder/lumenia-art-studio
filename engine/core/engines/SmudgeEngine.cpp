#include "SmudgeEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void SmudgeEngine::renderDab(
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

    const int centerX = static_cast<int>(std::round(dab.position.x));
    const int centerY = static_cast<int>(std::round(dab.position.y));

    // Amostragem na camada ativa (tileGrid)
    const int tx = centerX / canvas::Tile::TILE_SIZE;
    const int ty = centerY / canvas::Tile::TILE_SIZE;
    const int lpx = centerX % canvas::Tile::TILE_SIZE;
    const int lpy = centerY % canvas::Tile::TILE_SIZE;

    raster::ColorRGBA sampledColor{0, 0, 0, 0};
    if (tx >= 0 && tx < tileGrid.getTilesCountX() && ty >= 0 && ty < tileGrid.getTilesCountY()) {
        const canvas::Tile* tile = tileGrid.getTile(tx, ty);
        if (tile) sampledColor = tile->getBuffer().getPixel(lpx, lpy);
    }

    const double pickup = std::clamp(profile.smudgeParams.colorPickup, 0.0, 1.0);
    const double mixRatio = std::clamp(profile.smudgeParams.mixRatio, 0.0, 1.0);
    const double stretch = std::clamp(profile.smudgeParams.smudgeStretch, 0.0, 1.0);

    // Lógica de Coleta e Arrasto sem fallback de tinta preta artificial
    if (!m_hasCarriedColor) {
        if (sampledColor.a > 0) {
            m_carriedColor = sampledColor;
        } else {
            m_carriedColor = raster::ColorRGBA{0, 0, 0, 0}; // Pincel limpo/transparente
        }
        m_hasCarriedColor = true;
    } else {
        if (sampledColor.a > 0) {
            if (m_carriedColor.a == 0) {
                // Ao cruzar uma área pintada com o pincel limpo, coleta a tinta da tela
                m_carriedColor = sampledColor;
            } else {
                // Mescla a tinta mantida com a nova cor encontrada na tela
                const double blendRatio = pickup * (1.0 - stretch * 0.7);
                m_carriedColor.r = static_cast<uint8_t>(m_carriedColor.r * (1.0 - blendRatio) + sampledColor.r * blendRatio);
                m_carriedColor.g = static_cast<uint8_t>(m_carriedColor.g * (1.0 - blendRatio) + sampledColor.g * blendRatio);
                m_carriedColor.b = static_cast<uint8_t>(m_carriedColor.b * (1.0 - blendRatio) + sampledColor.b * blendRatio);
                m_carriedColor.a = static_cast<uint8_t>(m_carriedColor.a * (1.0 - blendRatio) + sampledColor.a * blendRatio);
            }
        } else {
            // Em áreas transparentes, a tinta mantida decai (foca no arrasto e desbotamento)
            const double decay = 0.85 + stretch * 0.14; // stretch 1.0 = desbotamento suave, 0.0 = desbotamento rápido
            m_carriedColor.a = static_cast<uint8_t>(std::clamp(m_carriedColor.a * decay, 0.0, 255.0));
        }
    }

    // Se o pincel estiver limpo/transparente, nada é depositado na tela
    if (m_carriedColor.a == 0) return;

    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds, tileGrid.getWidth(), tileGrid.getHeight()
    );

    const double radAngle = -dab.angle * (3.14159265358979323846 / 180.0);
    const double cosA = std::cos(radAngle);
    const double sinA = std::sin(radAngle);

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
            const double dy = static_cast<double>(tilePixelY + py) + 0.5 - dab.position.y;

            for (int px = minX; px <= maxX; ++px) {
                const double dx = static_cast<double>(tilePixelX + px) + 0.5 - dab.position.x;

                const double rotX = dx * cosA - dy * sinA;
                const double rotY = dx * sinA + dy * cosA;
                const double scaledY = rotY / aspect;
                const double dist = std::sqrt(rotX * rotX + scaledY * scaledY);

                if (dist > r + 1.0) continue;

                double shapeAlpha = 1.0;
                const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
                if (dist > hardSpan) {
                    shapeAlpha = std::clamp((r - dist) / std::max(0.001, r - hardSpan), 0.0, 1.0);
                }
                const double depositFactor = dab.opacity * shapeAlpha * mixRatio;
                if (depositFactor <= 0.0) continue;

                double curDepositFactor = depositFactor;
                if (ctx.clipBaseLayer) {
                    const int bTx = (tilePixelX + px) / canvas::Tile::TILE_SIZE;
                    const int bTy = (tilePixelY + py) / canvas::Tile::TILE_SIZE;
                    const int bPx = (tilePixelX + px) % canvas::Tile::TILE_SIZE;
                    const int bPy = (tilePixelY + py) % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curDepositFactor *= baseA;
                }

                if (curDepositFactor <= 0.0) continue;

                const raster::ColorRGBA dst = buffer.getPixel(px, py);

                if (ctx.alphaLocked) {
                    if (dst.a == 0) continue;
                    const double srcA = (static_cast<double>(m_carriedColor.a) / 255.0) * curDepositFactor;
                    const double dstA = static_cast<double>(dst.a) / 255.0;
                    const double invSrcA = 1.0 - srcA;

                    const double outR = (m_carriedColor.r * srcA + dst.r * dstA * invSrcA) / (srcA + dstA * invSrcA);
                    const double outG = (m_carriedColor.g * srcA + dst.g * dstA * invSrcA) / (srcA + dstA * invSrcA);
                    const double outB = (m_carriedColor.b * srcA + dst.b * dstA * invSrcA) / (srcA + dstA * invSrcA);

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                        dst.a
                    });
                    tileModified = true;
                    continue;
                }

                const double srcA = (static_cast<double>(m_carriedColor.a) / 255.0) * curDepositFactor;
                const double dstA = static_cast<double>(dst.a) / 255.0;

                const double outA = srcA + dstA * (1.0 - srcA);
                if (outA > 0.0) {
                    const double outR = (m_carriedColor.r * srcA + dst.r * dstA * (1.0 - srcA)) / outA;
                    const double outG = (m_carriedColor.g * srcA + dst.g * dstA * (1.0 - srcA)) / outA;
                    const double outB = (m_carriedColor.b * srcA + dst.b * dstA * (1.0 - srcA)) / outA;

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
