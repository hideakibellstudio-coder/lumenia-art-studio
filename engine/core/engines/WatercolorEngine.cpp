#include "WatercolorEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void WatercolorEngine::renderDab(
    const raster::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& canvasTexture,
    canvas::TileGrid& tileGrid,
    const canvas::PixelBuffer* /*compositeBuffer*/,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double r = dab.radius;
    const double aspect = std::max(0.05, profile.tip.aspectRatio);

    // No modo Wet-on-Wet (sangramento alto), o raio de expansão cresce proporcionalmente a pigmentBleed
    const double bleedRatio = std::clamp(profile.watercolorParams.pigmentBleed, 0.0, 1.0);
    const double waterLevel = std::clamp(profile.watercolorParams.waterLevel, 0.0, 1.0);
    const double fringeInt  = std::clamp(profile.watercolorParams.fringeIntensity, 0.0, 1.0);
    const double granulate  = std::clamp(profile.watercolorParams.granulation, 0.0, 1.0);

    const double effectiveRadius = r * (1.0 + bleedRatio * waterLevel * 0.4);
    const double maxR = effectiveRadius / aspect + 2.0;

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

    const auto heightTex = canvasTexture.canvasHeightTexture;

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

                const double safeEffRadius = std::max(0.001, effectiveRadius);
                const double normDist = dist / safeEffRadius;

                // 1. Falloff procedural com miolo aquoso suave
                double shapeAlpha = 1.0;
                const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * safeEffRadius;
                if (dist > hardSpan) {
                    shapeAlpha = std::clamp((safeEffRadius - dist) / std::max(0.001, safeEffRadius - hardSpan), 0.0, 1.0);
                }
                if (shapeAlpha <= 0.0) continue;

                // 2. Coffee Ring Effect (Anel de Borda Escura de Secagem)
                double fringeFactor = 1.0;
                if (fringeInt > 0.0 && normDist >= 0.6) {
                    const double ringRatio = (normDist - 0.6) / 0.4;
                    // Curva de acúmulo no bordo capilar da mancha
                    fringeFactor += std::sin(ringRatio * 3.14159265358979323846) * fringeInt * 1.5;
                }

                // 3. Granulação no Papel (Deposição nos vales)
                double granFactor = 1.0;
                if (granulate > 0.0 && heightTex) {
                    const double paperH = heightTex->sampleNormalized(globalX * 0.02, globalY * 0.02);
                    // Vales (paperH < 0.5) acumulam mais pigmento; cristas (paperH > 0.5) retêm menos
                    const double valleyDepth = (1.0 - paperH) - 0.5;
                    granFactor = 1.0 + valleyDepth * granulate * 1.2;
                }

                // 4. Modulação da Opacidade Efetiva da Mancha de Aquarela
                const double effectiveOpacity = std::clamp(
                    dab.opacity * shapeAlpha * fringeFactor * granFactor * (0.4 + waterLevel * 0.6),
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

                // 5. Compositing Transparente Estilo Veladura (Glaze)
                const raster::ColorRGBA dst = buffer.getPixel(px, py);

                if (ctx.alphaLocked) {
                    if (dst.a == 0) continue;
                    const double srcR = static_cast<double>(dab.color.r) / 255.0;
                    const double srcG = static_cast<double>(dab.color.g) / 255.0;
                    const double srcB = static_cast<double>(dab.color.b) / 255.0;

                    const double dstR = static_cast<double>(dst.r) / 255.0;
                    const double dstG = static_cast<double>(dst.g) / 255.0;
                    const double dstB = static_cast<double>(dst.b) / 255.0;

                    const double glazeR = srcR * dstR;
                    const double glazeG = srcG * dstG;
                    const double glazeB = srcB * dstB;

                    const double mixR = dstR * (1.0 - curEffectiveOpacity) + glazeR * curEffectiveOpacity;
                    const double mixG = dstG * (1.0 - curEffectiveOpacity) + glazeG * curEffectiveOpacity;
                    const double mixB = dstB * (1.0 - curEffectiveOpacity) + glazeB * curEffectiveOpacity;

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(mixR * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(mixG * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(mixB * 255.0, 0.0, 255.0)),
                        dst.a
                    });
                    tileModified = true;
                    continue;
                }

                if (dst.a == 0) {
                    // Deposição em transparência pura
                    buffer.setPixel(px, py, raster::ColorRGBA{
                        dab.color.r,
                        dab.color.g,
                        dab.color.b,
                        static_cast<uint8_t>(std::clamp(curEffectiveOpacity * 255.0, 0.0, 255.0))
                    });
                } else {
                    // Glaze: Sobreposição transparente acumulativa (Multiply suave + Alpha Over)
                    const double srcR = static_cast<double>(dab.color.r) / 255.0;
                    const double srcG = static_cast<double>(dab.color.g) / 255.0;
                    const double srcB = static_cast<double>(dab.color.b) / 255.0;

                    const double dstR = static_cast<double>(dst.r) / 255.0;
                    const double dstG = static_cast<double>(dst.g) / 255.0;
                    const double dstB = static_cast<double>(dst.b) / 255.0;
                    const double dstA = static_cast<double>(dst.a) / 255.0;

                    // Blend de pigmentos aquosos (Multiply de sub-camadas)
                    const double glazeR = srcR * dstR;
                    const double glazeG = srcG * dstG;
                    const double glazeB = srcB * dstB;

                    const double mixR = dstR * (1.0 - curEffectiveOpacity) + glazeR * curEffectiveOpacity;
                    const double mixG = dstG * (1.0 - curEffectiveOpacity) + glazeG * curEffectiveOpacity;
                    const double mixB = dstB * (1.0 - curEffectiveOpacity) + glazeB * curEffectiveOpacity;

                    const double outA = std::max(dstA, curEffectiveOpacity);

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(mixR * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(mixG * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(mixB * 255.0, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
                    });
                }
                tileModified = true;
            }
        }
        if (tileModified) tile->setDirty(true);
    }
}

} // namespace aladyn::engine::engines
