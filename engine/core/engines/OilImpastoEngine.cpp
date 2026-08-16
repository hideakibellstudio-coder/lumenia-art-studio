#include "OilImpastoEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void OilImpastoEngine::renderDab(
    const raster::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const canvas::PixelBuffer* /*compositeBuffer*/,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double r = dab.radius;
    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const double maxR = r / aspect + 2.0;

    const double impastoDepth = std::clamp(profile.oilParams.impastoDepth, 0.0, 1.0);
    const double bristleGrooves = std::clamp(profile.oilParams.bristleGrooves, 0.0, 1.0);
    const double viscosity    = std::clamp(profile.oilParams.viscosity, 0.0, 1.0);
    const double specularBrill = std::clamp(profile.oilParams.specularBrilliance, 0.0, 1.0);

    const math::Rect2D bounds{
        dab.position.x - maxR, dab.position.y - maxR,
        maxR * 2.0, maxR * 2.0
    };

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
            const int globalY = tilePixelY + py;
            const double dy = static_cast<double>(globalY) + 0.5 - dab.position.y;

            for (int px = minX; px <= maxX; ++px) {
                const int globalX = tilePixelX + px;
                const double dx = static_cast<double>(globalX) + 0.5 - dab.position.x;

                const double rotX = dx * cosA - dy * sinA;
                const double rotY = dx * sinA + dy * cosA;
                const double scaledY = rotY / aspect;
                const double dist = std::sqrt(rotX * rotX + scaledY * scaledY);

                if (dist > r + 1.0) continue;

                const double normDist = dist / r;

                // 1. Dureza e Falloff da borda do dab
                double shapeAlpha = 1.0;
                const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
                if (dist > hardSpan) {
                    shapeAlpha = std::clamp((r - dist) / std::max(0.001, r - hardSpan), 0.0, 1.0);
                }
                if (shapeAlpha <= 0.0) continue;

                // 2. Ranhuras de Cerdas (Bristle Grooves) — Frequência transversal
                double bristleMod = 1.0;
                if (bristleGrooves > 0.0) {
                    const double wave = std::abs(std::sin(rotX * 0.45));
                    bristleMod = (1.0 - bristleGrooves * 0.6) + wave * bristleGrooves * 0.6;
                }

                // 3. Acúmulo de Crista de Impasto (Impasto Ridge) nas bordas
                double impastoFactor = 1.0;
                if (impastoDepth > 0.0 && normDist >= 0.65 && normDist <= 0.95) {
                    const double ridge = std::sin((normDist - 0.65) / 0.3 * 3.14159265358979323846);
                    impastoFactor += ridge * impastoDepth * 0.8;
                }

                // 4. Highlight Especular Úmido (Luster Gloss 3D)
                double specularAdd = 0.0;
                if (specularBrill > 0.0 && normDist <= 0.85) {
                    // Simulação de reflexo especular direcional (luz vindo do canto superior esquerdo)
                    const double normalX = rotX / r;
                    const double normalY = rotY / r;
                    const double lightX = -0.577;
                    const double lightY = -0.577;
                    const double dotL = std::max(0.0, -(normalX * lightX + normalY * lightY));
                    specularAdd = std::pow(dotL, 4.0) * specularBrill * 0.35 * bristleMod;
                }

                // 5. Deposição Viscosa da Tinta a Óleo
                const double effectiveOpacity = std::clamp(
                    dab.opacity * shapeAlpha * bristleMod * impastoFactor * (0.6 + viscosity * 0.4),
                    0.0, 1.0
                );
                double curEffectiveOpacity = effectiveOpacity;
                if (ctx.clipBaseLayer) {
                    const int bTx = (tilePixelX + px) / canvas::Tile::TILE_SIZE;
                    const int bTy = (tilePixelY + py) / canvas::Tile::TILE_SIZE;
                    const int bPx = (tilePixelX + px) % canvas::Tile::TILE_SIZE;
                    const int bPy = (tilePixelY + py) % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curEffectiveOpacity *= baseA;
                }

                if (curEffectiveOpacity <= 0.0) continue;

                const raster::ColorRGBA dst = buffer.getPixel(px, py);

                const double srcR = static_cast<double>(dab.color.r) / 255.0;
                const double srcG = static_cast<double>(dab.color.g) / 255.0;
                const double srcB = static_cast<double>(dab.color.b) / 255.0;
                const double srcA = (static_cast<double>(dab.color.a) / 255.0) * curEffectiveOpacity;

                const double dstR = static_cast<double>(dst.r) / 255.0;
                const double dstG = static_cast<double>(dst.g) / 255.0;
                const double dstB = static_cast<double>(dst.b) / 255.0;
                const double dstA = static_cast<double>(dst.a) / 255.0;

                if (ctx.alphaLocked) {
                    if (dst.a == 0) continue;
                    const double invSrcA = 1.0 - srcA;

                    double outR = (srcR * srcA + dstR * dstA * invSrcA) / (srcA + dstA * invSrcA) + specularAdd;
                    double outG = (srcG * srcA + dstG * dstA * invSrcA) / (srcA + dstA * invSrcA) + specularAdd;
                    double outB = (srcB * srcA + dstB * dstA * invSrcA) / (srcA + dstA * invSrcA) + specularAdd;

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB * 255.0, 0.0, 255.0)),
                        dst.a
                    });
                    tileModified = true;
                    continue;
                }

                // Compositing Normal Viscoso com Brilho Especular 3D
                const double outA = srcA + dstA * (1.0 - srcA);
                if (outA > 0.0) {
                    double outR = (srcR * srcA + dstR * dstA * (1.0 - srcA)) / outA + specularAdd;
                    double outG = (srcG * srcA + dstG * dstA * (1.0 - srcA)) / outA + specularAdd;
                    double outB = (srcB * srcA + dstB * dstA * (1.0 - srcA)) / outA + specularAdd;

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB * 255.0, 0.0, 255.0)),
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
