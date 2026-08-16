#include "PencilEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../math/MathUtils.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::engines {

void PencilEngine::renderDab(
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

    const double maxR = r / aspect + 2.0;
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

    // graphiteHardness modula o limiar de contato:
    // 0.0 (6B mole) → threshold baixo = deposita facilmente
    // 1.0 (2H duro) → threshold alto = requer pressão para penetrar
    const double hardnessOffset = (profile.pencilParams.graphiteHardness - 0.5) * 0.4;

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
            const double globalY = static_cast<double>(tilePixelY + py) + 0.5;
            const double dy = globalY - dab.position.y;

            for (int px = minX; px <= maxX; ++px) {
                const double globalX = static_cast<double>(tilePixelX + px) + 0.5;
                const double dx = globalX - dab.position.x;

                const double rotX = dx * cosA - dy * sinA;
                const double rotY = dx * sinA + dy * cosA;
                const double scaledY = rotY / aspect;
                const double dist = std::sqrt(rotX * rotX + scaledY * scaledY);

                if (dist > r + 1.0) continue;

                const double uDab = std::clamp((rotX + r) / (2.0 * r), 0.0, 1.0);
                const double vDab = std::clamp((scaledY + r) / (2.0 * r), 0.0, 1.0);

                // 1. FORMA (Shape Alpha com Hardness)
                double shapeAlpha = 1.0;
                if (profile.shapeTexture) {
                    shapeAlpha = profile.shapeTexture->sampleNormalized(uDab, vDab,
                        texture::TextureWrapMode::Clamp);
                } else {
                    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
                    if (dist > hardSpan) {
                        shapeAlpha = std::clamp((r - dist) / std::max(0.001, r - hardSpan), 0.0, 1.0);
                    }
                }
                if (shapeAlpha <= 0.0) continue;

                // 2. BRUSH HEIGHTMAP (textura do grafite)
                double brushHeight = 1.0;
                if (profile.brushGrainEnabled && profile.brushHeightTexture) {
                    const double uB = uDab * profile.brushGrainScale;
                    const double vB = vDab * profile.brushGrainScale;
                    brushHeight = profile.brushHeightTexture->sampleNormalized(uB, vB,
                        texture::TextureWrapMode::Repeat);
                    if (profile.brushGrainInvert) brushHeight = 1.0 - brushHeight;
                    if (profile.brushGrainContrast != 1.0 && profile.brushGrainContrast > 0.0) {
                        const double hs = 0.5 / profile.brushGrainContrast;
                        brushHeight = math::MathUtils::smoothstep(0.5 - hs, 0.5 + hs, brushHeight);
                    }
                    brushHeight = profile.brushTextureCurve.sample(brushHeight);
                }

                // 3. CANVAS HEIGHTMAP (papel — central no lápis)
                double canvasHeight = 1.0;
                if (canvasTexture.canvasGrainEnabled && canvasTexture.canvasHeightTexture) {
                    const double uC = globalX * 0.002 * canvasTexture.canvasGrainScale;
                    const double vC = globalY * 0.002 * canvasTexture.canvasGrainScale;
                    canvasHeight = canvasTexture.canvasHeightTexture->sampleNormalized(uC, vC,
                        texture::TextureWrapMode::Repeat);
                    if (canvasTexture.canvasGrainInvert) canvasHeight = 1.0 - canvasHeight;
                    if (canvasTexture.canvasGrainContrast != 1.0 && canvasTexture.canvasGrainContrast > 0.0) {
                        const double hs = 0.5 / canvasTexture.canvasGrainContrast;
                        canvasHeight = math::MathUtils::smoothstep(0.5 - hs, 0.5 + hs, canvasHeight);
                    }
                    canvasHeight = canvasTexture.canvasTextureCurve.sample(canvasHeight);
                }

                // 4. EQUAÇÃO 3D CONTACT — GRAFITE MODULADO POR DUREZA
                // O lápis enfatiza muito o relevo do papel (canvasHeight elevado ao quadrado)
                const double combinedHeight = brushHeight * (canvasHeight * canvasHeight);
                const double threshold = (1.0 - dab.pressure) + hardnessOffset;
                const double depositedInk = math::MathUtils::smoothstep(
                    threshold - 0.12, threshold + 0.12, combinedHeight
                );

                const double finalAlpha = (static_cast<double>(dab.color.a) / 255.0)
                    * dab.opacity * shapeAlpha * depositedInk;
                if (finalAlpha <= 0.0) continue;

                double curFinalAlpha = finalAlpha;
                if (ctx.clipBaseLayer) {
                    const int bTx = (tilePixelX + px) / canvas::Tile::TILE_SIZE;
                    const int bTy = (tilePixelY + py) / canvas::Tile::TILE_SIZE;
                    const int bPx = (tilePixelX + px) % canvas::Tile::TILE_SIZE;
                    const int bPy = (tilePixelY + py) % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curFinalAlpha *= baseA;
                }

                if (curFinalAlpha <= 0.0) continue;

                // 5. COMPOSIÇÃO — Normal Alpha Over & Alpha Lock
                const raster::ColorRGBA dst = buffer.getPixel(px, py);

                if (ctx.alphaLocked) {
                    if (dst.a == 0) continue;
                    const double srcA = curFinalAlpha;
                    const double dstA = static_cast<double>(dst.a) / 255.0;
                    const double invSrcA = 1.0 - srcA;

                    const double outR = (dab.color.r * srcA + dst.r * dstA * invSrcA) / (srcA + dstA * invSrcA);
                    const double outG = (dab.color.g * srcA + dst.g * dstA * invSrcA) / (srcA + dstA * invSrcA);
                    const double outB = (dab.color.b * srcA + dst.b * dstA * invSrcA) / (srcA + dstA * invSrcA);

                    buffer.setPixel(px, py, raster::ColorRGBA{
                        static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                        static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                        dst.a
                    });
                    tileModified = true;
                    continue;
                }

                const double srcA = curFinalAlpha;
                const double dstA = static_cast<double>(dst.a) / 255.0;
                const double outA = srcA + dstA * (1.0 - srcA);

                if (outA > 0.0) {
                    const double outR = (dab.color.r * srcA + dst.r * dstA * (1.0 - srcA)) / outA;
                    const double outG = (dab.color.g * srcA + dst.g * dstA * (1.0 - srcA)) / outA;
                    const double outB = (dab.color.b * srcA + dst.b * dstA * (1.0 - srcA)) / outA;

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
