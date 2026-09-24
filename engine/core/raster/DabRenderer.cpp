#include "DabRenderer.hpp"
#include "SimdSpanBlender.hpp"
#include "LargeBrushOptimizer.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/MathUtils.hpp"
#include "../document/Layer.hpp"
#include "../color/LinearColorSpace.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::raster {

void DabRenderer::renderDab(
    const Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& canvasTexture,
    canvas::TileGrid& tileGrid,
    const PixelContext& ctx
) {
    if (dab.radius <= 0.5 || dab.color.a == 0 || dab.opacity < 0.005) return;

    const double r = dab.radius;
    
    // Achatamento elíptico (Aspect Ratio) com modulação de caneta/dab e perfil
    double aspect = std::clamp(dab.aspectRatio, 0.05, 1.0);
    if (profile.pressureToAspect > 0.0 && dab.aspectRatio >= 0.999) {
        aspect = std::clamp(profile.tip.aspectRatio - (dab.pressure * profile.pressureToAspect), 0.05, 1.0);
    }
    aspect = std::max(0.05, aspect);

    // Bounding Box considerando a rotação e o achatamento elíptico
    const double maxR = r / aspect + 2.0;
    const math::Rect2D bounds{
        dab.position.x - maxR,
        dab.position.y - maxR,
        maxR * 2.0,
        maxR * 2.0
    };

    const auto tileIndices = canvas::SpatialCuller::getIntersectingTiles(
        bounds,
        tileGrid.getWidth(),
        tileGrid.getHeight()
    );

    // ─── 1. CIRCLE-AABB CULLING: Descarte antecipado dos cantos do bounding box ───
    const double maxRSq = maxR * maxR;
    std::vector<canvas::Tile*> validTiles;
    validTiles.reserve(tileIndices.size());

    for (const auto& idx : tileIndices) {
        const double tileX0 = static_cast<double>(idx.x * canvas::Tile::TILE_SIZE);
        const double tileX1 = tileX0 + canvas::Tile::TILE_SIZE;
        const double tileY0 = static_cast<double>(idx.y * canvas::Tile::TILE_SIZE);
        const double tileY1 = tileY0 + canvas::Tile::TILE_SIZE;

        const double clampX = std::clamp(dab.position.x, tileX0, tileX1);
        const double clampY = std::clamp(dab.position.y, tileY0, tileY1);
        const double dX = dab.position.x - clampX;
        const double dY = dab.position.y - clampY;
        if (dX * dX + dY * dY > maxRSq) {
            continue; // Pula o tile completamente sem alocar buffer
        }

        canvas::Tile* tile = tileGrid.getOrCreateTile(idx.x, idx.y);
        if (tile) {
            validTiles.push_back(tile);
        }
    }

    if (validTiles.empty()) return;

    // ─── 2. PRÉ-CÁLCULOS ANALÍTICOS FORA DO LOOP ──────────────────────────────
    const auto shapeTex = profile.shapeTexture;
    const auto brushHeightTex = profile.brushHeightTexture;
    const auto canvasHeightTex = canvasTexture.canvasHeightTexture;

    const bool isCircular = (aspect >= 0.999) && (std::abs(dab.angle) < 0.001);
    const double radAngle = isCircular ? 0.0 : (-dab.angle * (3.14159265358979323846 / 180.0));
    const double cosA = isCircular ? 1.0 : std::cos(radAngle);
    const double sinA = isCircular ? 0.0 : std::sin(radAngle);
    const double invAspect = isCircular ? 1.0 : (1.0 / aspect);

    const double safeR = std::max(0.001, r);
    const double invTwoSafeR = 0.5 / safeR;
    const double maxRadius = r + 1.0;
    const double maxRadiusSq = maxRadius * maxRadius;
    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * safeR;
    const double hardSpanSq = hardSpan * hardSpan;
    const double invSoftSpan = 1.0 / std::max(0.001, safeR - hardSpan);
    const double outerSubpixelThresh = safeR - 0.5;
    const double outerSubpixelThreshSq = (outerSubpixelThresh > 0.0) ? (outerSubpixelThresh * outerSubpixelThresh) : 0.0;

    const double dabColorAlphaNorm = static_cast<double>(dab.color.a) / 255.0;
    const double dabBaseAlpha = dabColorAlphaNorm * dab.opacity;
    const double threshold = 1.0 - dab.pressure;
    constexpr double feather = 0.15;
    const double invBrushGrainContrast = (profile.brushGrainContrast != 1.0 && profile.brushGrainContrast > 0.0)
        ? (0.5 / profile.brushGrainContrast) : 0.0;
    const double canvasGrainFactor = 0.002 * canvasTexture.canvasGrainScale;

    // Fast-path de texturas: quando desligadas (padrão de desenho de alto desempenho),
    // o valor de depositedInk é puramente analítico e 100% constante para todo o dab.
    const bool hasTextures = (profile.brushGrainEnabled && brushHeightTex) || (canvasTexture.canvasGrainEnabled && canvasHeightTex);
    const double defaultDepositedInk = hasTextures ? 1.0 : math::MathUtils::smoothstep(threshold - feather, threshold + feather, 1.0);
    if (!hasTextures && defaultDepositedInk <= 0.0) {
        return; // Zero tinta depositada
    }
    const double dabEffectiveAlpha = dabBaseAlpha * defaultDepositedInk;
    if (dabEffectiveAlpha <= 0.0) return;

    const bool hasSelection = (ctx.selectionMask != nullptr && ctx.selectionMask->hasSelection());
    const bool hasClip = (ctx.clipBaseLayer != nullptr);


    // ─── 3. EXECUÇÃO PARALELA MULTI-CORE EM MICRO-TILES INDEPENDENTES ─────────
    const int numTiles = static_cast<int>(validTiles.size());
    #pragma omp parallel for schedule(static) if(numTiles >= 4)
    for (int t = 0; t < numTiles; ++t) {
        canvas::Tile* tile = validTiles[t];
        canvas::PixelBuffer& buffer = tile->getBuffer();
        const int tilePixelX = tile->getPixelX();
        const int tilePixelY = tile->getPixelY();

        const int minX = std::max(0, static_cast<int>(std::floor(bounds.getLeft())) - tilePixelX);
        const int maxX = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(bounds.getRight())) - tilePixelX);
        const int minY = std::max(0, static_cast<int>(std::floor(bounds.getTop())) - tilePixelY);
        const int maxY = std::min(canvas::Tile::TILE_SIZE - 1, static_cast<int>(std::ceil(bounds.getBottom())) - tilePixelY);

        if (minX > maxX || minY > maxY) continue;

        bool tileModified = false;
        ColorRGBA* tileBasePtr = reinterpret_cast<ColorRGBA*>(buffer.getData());

        for (int py = minY; py <= maxY; ++py) {
            const double globalY = static_cast<double>(tilePixelY + py) + 0.5;
            const double dy = globalY - dab.position.y;
            const double dySq = dy * dy;

            int rowMinX = minX;
            int rowMaxX = maxX;

            if (isCircular) {
                if (dySq > maxRadiusSq) continue;
                const double dxSpan = std::sqrt(maxRadiusSq - dySq);
                rowMinX = std::max(minX, static_cast<int>(std::floor(dab.position.x - dxSpan)) - tilePixelX);
                rowMaxX = std::min(maxX, static_cast<int>(std::ceil(dab.position.x + dxSpan)) - tilePixelX);
                if (rowMinX > rowMaxX) continue;
            }

            const double vCanvas = (hasTextures && canvasTexture.canvasGrainEnabled && canvasHeightTex) ? (globalY * canvasGrainFactor) : 0.0;
            ColorRGBA* dstRow = tileBasePtr + (py * canvas::Tile::TILE_SIZE);

            for (int px = rowMinX; px <= rowMaxX; ++px) {

                const double globalX = static_cast<double>(tilePixelX + px) + 0.5;
                const double dx = globalX - dab.position.x;

                double rotX, scaledY, distSq;
                if (isCircular) {
                    rotX = dx;
                    scaledY = dy;
                    distSq = dx * dx + dySq;
                } else {
                    rotX = dx * cosA - dy * sinA;
                    const double rotY = dx * sinA + dy * cosA;
                    scaledY = rotY * invAspect;
                    distSq = rotX * rotX + scaledY * scaledY;
                }

                if (distSq > maxRadiusSq) continue;

                // 1. FORMA DA PONTA (Shape Alpha com Suporte a Hardness e Subpixel Anti-aliasing)
                double shapeAlpha = 1.0;
                if (shapeTex) {
                    const double uDab = (rotX + safeR) * invTwoSafeR;
                    const double vDab = (scaledY + safeR) * invTwoSafeR;
                    shapeAlpha = shapeTex->sampleNormalized(uDab, vDab, texture::TextureWrapMode::Clamp);
                    if (distSq > outerSubpixelThreshSq) {
                        const double dist = std::sqrt(distSq);
                        if (dist > outerSubpixelThresh) {
                            shapeAlpha *= std::clamp((safeR - dist) * 2.0, 0.0, 1.0);
                        }
                    }
                } else {
                    // Fast-path: no miolo sólido (distSq <= hardSpanSq && distSq <= outerSubpixelThreshSq),
                    // dispensamos std::sqrt e divisões flutuantes!
                    if (distSq > hardSpanSq || distSq > outerSubpixelThreshSq) {
                        const double dist = std::sqrt(distSq);
                        if (dist > hardSpan) {
                            const double t = (safeR - dist) * invSoftSpan;
                            shapeAlpha = LargeBrushOptimizer::smoothHermite(t);
                        }
                        if (dist > outerSubpixelThresh) {
                            shapeAlpha *= std::clamp((safeR - dist) * 2.0, 0.0, 1.0);
                        }
                    }
                }

                if (shapeAlpha <= 0.0) continue;

                double curFinalAlpha;
                if (!hasTextures) {
                    curFinalAlpha = dabEffectiveAlpha * shapeAlpha;
                } else {
                    // 2. TEXTURA DO PINCEL (Brush Heightmap - Móvel no UV do Dab)
                    double brushHeight = 1.0;
                    if (profile.brushGrainEnabled && brushHeightTex) {
                        const double uDab = (rotX + safeR) * invTwoSafeR;
                        const double vDab = (scaledY + safeR) * invTwoSafeR;
                        const double uBrush = uDab * profile.brushGrainScale;
                        const double vBrush = vDab * profile.brushGrainScale;
                        brushHeight = brushHeightTex->sampleNormalized(uBrush, vBrush, texture::TextureWrapMode::Repeat);

                        if (profile.brushGrainInvert) {
                            brushHeight = 1.0 - brushHeight;
                        }

                        if (invBrushGrainContrast > 0.0) {
                            brushHeight = math::MathUtils::smoothstep(0.5 - invBrushGrainContrast, 0.5 + invBrushGrainContrast, brushHeight);
                        }

                        brushHeight = profile.brushTextureCurve.sample(brushHeight);
                    }

                    // 3. TEXTURA DA TELA / PAPEL (Canvas Heightmap - Estática no Canvas World)
                    double canvasHeight = 1.0;
                    if (canvasTexture.canvasGrainEnabled && canvasHeightTex) {
                        const double uCanvas = globalX * canvasGrainFactor;
                        const uint8_t rawVal = canvasHeightTex->sampleNormalizedFastByte(uCanvas, vCanvas);
                        canvasHeight = canvasTexture.sampleLUT(rawVal);
                    }

                    const double combinedHeight = brushHeight * canvasHeight;
                    const double depositedInk = math::MathUtils::smoothstep(threshold - feather, threshold + feather, combinedHeight);
                    curFinalAlpha = dabBaseAlpha * shapeAlpha * depositedInk;
                }

                if (curFinalAlpha <= 0.0) continue;

                if (hasSelection) {
                    const int gX = tilePixelX + px;
                    const int gY = tilePixelY + py;
                    const uint8_t sVal = ctx.selectionMask->getValue(gX, gY);
                    if (sVal == 0) continue;
                    if (sVal < 255) {
                        curFinalAlpha *= (static_cast<double>(sVal) / 255.0);
                    }
                }

                if (hasClip) {
                    const int gX = tilePixelX + px;
                    const int gY = tilePixelY + py;
                    const int bTx = gX / canvas::Tile::TILE_SIZE;
                    const int bTy = gY / canvas::Tile::TILE_SIZE;
                    const int bPx = gX % canvas::Tile::TILE_SIZE;
                    const int bPy = gY % canvas::Tile::TILE_SIZE;
                    const canvas::Tile* bTile = const_cast<canvas::TileGrid&>(ctx.clipBaseLayer->getTileGrid()).getTile(bTx, bTy);
                    if (!bTile) continue;
                    const double baseA = static_cast<double>(bTile->getBuffer().getPixel(bPx, bPy).a) / 255.0;
                    if (baseA <= 0.0) continue;
                    curFinalAlpha *= baseA;
                }

                if (curFinalAlpha <= 0.0) continue;

                ColorRGBA& dst = dstRow[px];

                if (ctx.alphaLocked) {
                    if (dst.a == 0) continue;
                    const uint8_t origA = dst.a;
                    dst = color::blendLinearNormal(dab.color, static_cast<float>(curFinalAlpha), dst);
                    dst.a = origA;
                    tileModified = true;
                    continue;
                }

                // ─── PROCESSAMENTO DE MODO DE MESCLAGEM (DAB BLEND MODES) ──────
                switch (dab.blendMode) {
                    case DabBlendMode::Normal: {
                        if (dst.a == 0) {
                            const uint8_t fa8 = static_cast<uint8_t>(std::clamp(curFinalAlpha * 255.0, 0.0, 255.0));
                            dst = ColorRGBA{dab.color.r, dab.color.g, dab.color.b, fa8};
                            tileModified = true;
                            break;
                        }

                        if (dst.a == 255) {
                            dst = color::blendLinearNormalOpaque(dab.color, static_cast<float>(curFinalAlpha), dst);
                            tileModified = true;
                            break;
                        }

                        dst = color::blendLinearNormal(dab.color, static_cast<float>(curFinalAlpha), dst);
                        tileModified = true;
                        break;
                    }
                    case DabBlendMode::Multiply: { // Modo Canetinha / Marker
                        const double srcA = curFinalAlpha;
                        const double dstR = static_cast<double>(dst.r) / 255.0;
                        const double dstG = static_cast<double>(dst.g) / 255.0;
                        const double dstB = static_cast<double>(dst.b) / 255.0;

                        const double srcR = static_cast<double>(dab.color.r) / 255.0;
                        const double srcG = static_cast<double>(dab.color.g) / 255.0;
                        const double srcB = static_cast<double>(dab.color.b) / 255.0;

                        const double multR = dstR * (1.0 - srcA * (1.0 - srcR));
                        const double multG = dstG * (1.0 - srcA * (1.0 - srcG));
                        const double multB = dstB * (1.0 - srcA * (1.0 - srcB));

                        dst = ColorRGBA{
                            static_cast<uint8_t>(std::clamp(multR * 255.0, 0.0, 255.0)),
                            static_cast<uint8_t>(std::clamp(multG * 255.0, 0.0, 255.0)),
                            static_cast<uint8_t>(std::clamp(multB * 255.0, 0.0, 255.0)),
                            dst.a
                        };
                        tileModified = true;
                        break;
                    }
                    case DabBlendMode::Additive: { // Modo Luz / Glow
                        const double srcA = curFinalAlpha;
                        const double dstR = static_cast<double>(dst.r);
                        const double dstG = static_cast<double>(dst.g);
                        const double dstB = static_cast<double>(dst.b);

                        const double addR = dstR + static_cast<double>(dab.color.r) * srcA;
                        const double addG = dstG + static_cast<double>(dab.color.g) * srcA;
                        const double addB = dstB + static_cast<double>(dab.color.b) * srcA;

                        dst = ColorRGBA{
                            static_cast<uint8_t>(std::clamp(addR, 0.0, 255.0)),
                            static_cast<uint8_t>(std::clamp(addG, 0.0, 255.0)),
                            static_cast<uint8_t>(std::clamp(addB, 0.0, 255.0)),
                            255
                        };
                        tileModified = true;
                        break;
                    }
                }
            }
        }

        if (tileModified) {
            tile->setDirty(true);
        }
    }
}

} // namespace aladyn::engine::raster
