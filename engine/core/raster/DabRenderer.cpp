#include "DabRenderer.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/MathUtils.hpp"
#include "../document/Layer.hpp"
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
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double r = dab.radius;
    
    // Achatamento elíptico (Aspect Ratio) com modulação por pressão
    double aspect = profile.tip.aspectRatio;
    if (profile.pressureToAspect > 0.0) {
        aspect = std::clamp(aspect - (dab.pressure * profile.pressureToAspect), 0.05, 1.0);
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

    const auto shapeTex = profile.shapeTexture;
    const auto brushHeightTex = profile.brushHeightTexture;
    const auto canvasHeightTex = canvasTexture.canvasHeightTexture;

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
            const double globalY = static_cast<double>(tilePixelY + py) + 0.5;
            const double dy = globalY - dab.position.y;

            for (int px = minX; px <= maxX; ++px) {
                const double globalX = static_cast<double>(tilePixelX + px) + 0.5;
                const double dx = globalX - dab.position.x;

                // Rotação da Ponta
                const double rotX = dx * cosA - dy * sinA;
                const double rotY = dx * sinA + dy * cosA;

                // Achatamento Elíptico (Aspect Ratio)
                const double scaledY = rotY / aspect;
                const double distSq = rotX * rotX + scaledY * scaledY;
                const double maxR = r + 1.0;

                if (distSq <= maxR * maxR) {
                    const double dist = std::sqrt(distSq);
                    const double safeR = std::max(0.001, r);
                    const double uDab = (rotX + safeR) / (2.0 * safeR);
                    const double vDab = (scaledY + safeR) / (2.0 * safeR);

                    // 1. FORMA DA PONTA (Shape Alpha com Suporte a Hardness e Subpixel Anti-aliasing)
                    double shapeAlpha = 1.0;
                    if (shapeTex) {
                        shapeAlpha = shapeTex->sampleNormalized(uDab, vDab, texture::TextureWrapMode::Clamp);
                    } else {
                        const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * safeR;
                        if (dist > hardSpan) {
                            shapeAlpha = std::clamp((safeR - dist) / std::max(0.001, safeR - hardSpan), 0.0, 1.0);
                        }
                    }

                    // Suavização subpixel de 0.5px na borda externa circular
                    if (dist > safeR - 0.5) {
                        shapeAlpha *= std::clamp((safeR - dist) / 0.5, 0.0, 1.0);
                    }

                    if (shapeAlpha <= 0.0) continue;

                    // 2. TEXTURA DO PINCEL (Brush Heightmap - Móvel no UV do Dab)
                    double brushHeight = 1.0;
                    if (profile.brushGrainEnabled && brushHeightTex) {
                        const double uBrush = uDab * profile.brushGrainScale;
                        const double vBrush = vDab * profile.brushGrainScale;
                        brushHeight = brushHeightTex->sampleNormalized(uBrush, vBrush, texture::TextureWrapMode::Repeat);

                        if (profile.brushGrainInvert) {
                            brushHeight = 1.0 - brushHeight;
                        }

                        if (profile.brushGrainContrast != 1.0 && profile.brushGrainContrast > 0.0) {
                            const double halfSpan = 0.5 / profile.brushGrainContrast;
                            brushHeight = math::MathUtils::smoothstep(0.5 - halfSpan, 0.5 + halfSpan, brushHeight);
                        }

                        brushHeight = profile.brushTextureCurve.sample(brushHeight);
                    }

                    // 3. TEXTURA DA TELA / PAPEL (Canvas Heightmap - Estática no Canvas World)
                    double canvasHeight = 1.0;
                    if (canvasTexture.canvasGrainEnabled && canvasHeightTex) {
                        const double uCanvas = globalX * 0.002 * canvasTexture.canvasGrainScale;
                        const double vCanvas = globalY * 0.002 * canvasTexture.canvasGrainScale;
                        const uint8_t rawVal = canvasHeightTex->sampleNormalizedFastByte(uCanvas, vCanvas);
                        canvasHeight = canvasTexture.sampleLUT(rawVal);
                    }

                    // --- EQUAÇÃO DE CONJUNTO E CONTATO TRIDIMENSIONAL ---
                    const double combinedHeight = brushHeight * canvasHeight;
                    const double threshold = 1.0 - dab.pressure;
                    const double feather = 0.15;
                    const double depositedInk = math::MathUtils::smoothstep(threshold - feather, threshold + feather, combinedHeight);

                    const double finalAlpha = (static_cast<double>(dab.color.a) / 255.0) * dab.opacity * shapeAlpha * depositedInk;
                    if (finalAlpha <= 0.0) continue;

                    double curFinalAlpha = finalAlpha;
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
                        curFinalAlpha *= baseA;
                    }

                    if (curFinalAlpha <= 0.0) continue;

                    ColorRGBA dst = buffer.getPixel(px, py);

                    if (ctx.alphaLocked) {
                        if (dst.a == 0) continue;
                        const uint32_t sA = static_cast<uint32_t>(std::clamp(curFinalAlpha * 255.0, 0.0, 255.0));
                        const uint32_t invA = 255 - sA;
                        const ColorRGBA newColor{
                            static_cast<uint8_t>((dab.color.r * sA + dst.r * invA) / 255),
                            static_cast<uint8_t>((dab.color.g * sA + dst.g * invA) / 255),
                            static_cast<uint8_t>((dab.color.b * sA + dst.b * invA) / 255),
                            dst.a
                        };
                        buffer.setPixel(px, py, newColor);
                        tileModified = true;
                        continue;
                    }

                    // ─── PROCESSAMENTO DE MODO DE MESCLAGEM (DAB BLEND MODES) ──────
                    switch (dab.blendMode) {
                        case DabBlendMode::Normal: {
                            if (dst.a == 0) {
                                const uint8_t fa8 = static_cast<uint8_t>(std::clamp(curFinalAlpha * 255.0, 0.0, 255.0));
                                buffer.setPixel(px, py, ColorRGBA{dab.color.r, dab.color.g, dab.color.b, fa8});
                                tileModified = true;
                                break;
                            }

                            if (dst.a == 255) {
                                const uint32_t sA = static_cast<uint32_t>(std::clamp(curFinalAlpha * 255.0, 0.0, 255.0));
                                const uint32_t invA = 255 - sA;
                                const ColorRGBA newColor{
                                    static_cast<uint8_t>((dab.color.r * sA + dst.r * invA) / 255),
                                    static_cast<uint8_t>((dab.color.g * sA + dst.g * invA) / 255),
                                    static_cast<uint8_t>((dab.color.b * sA + dst.b * invA) / 255),
                                    255
                                };
                                buffer.setPixel(px, py, newColor);
                                tileModified = true;
                                break;
                            }

                            const double srcA = finalAlpha;
                            const double dstA = static_cast<double>(dst.a) / 255.0;
                            const double outA = srcA + dstA * (1.0 - srcA);

                            if (outA > 0.0) {
                                const double srcR = static_cast<double>(dab.color.r);
                                const double srcG = static_cast<double>(dab.color.g);
                                const double srcB = static_cast<double>(dab.color.b);

                                const double dstR = static_cast<double>(dst.r);
                                const double dstG = static_cast<double>(dst.g);
                                const double dstB = static_cast<double>(dst.b);

                                const double outR = (srcR * srcA + dstR * dstA * (1.0 - srcA)) / outA;
                                const double outG = (srcG * srcA + dstG * dstA * (1.0 - srcA)) / outA;
                                const double outB = (srcB * srcA + dstB * dstA * (1.0 - srcA)) / outA;

                                const ColorRGBA newColor{
                                    static_cast<uint8_t>(std::clamp(outR, 0.0, 255.0)),
                                    static_cast<uint8_t>(std::clamp(outG, 0.0, 255.0)),
                                    static_cast<uint8_t>(std::clamp(outB, 0.0, 255.0)),
                                    static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0))
                                };
                                buffer.setPixel(px, py, newColor);
                                tileModified = true;
                            }
                            break;
                        }
                        case DabBlendMode::Multiply: { // Modo Canetinha / Marker
                            const double srcA = finalAlpha;
                            const double dstR = static_cast<double>(dst.r) / 255.0;
                            const double dstG = static_cast<double>(dst.g) / 255.0;
                            const double dstB = static_cast<double>(dst.b) / 255.0;

                            const double srcR = static_cast<double>(dab.color.r) / 255.0;
                            const double srcG = static_cast<double>(dab.color.g) / 255.0;
                            const double srcB = static_cast<double>(dab.color.b) / 255.0;

                            const double multR = dstR * (1.0 - srcA * (1.0 - srcR));
                            const double multG = dstG * (1.0 - srcA * (1.0 - srcG));
                            const double multB = dstB * (1.0 - srcA * (1.0 - srcB));

                            ColorRGBA newColor{
                                static_cast<uint8_t>(std::clamp(multR * 255.0, 0.0, 255.0)),
                                static_cast<uint8_t>(std::clamp(multG * 255.0, 0.0, 255.0)),
                                static_cast<uint8_t>(std::clamp(multB * 255.0, 0.0, 255.0)),
                                dst.a
                            };
                            buffer.setPixel(px, py, newColor);
                            tileModified = true;
                            break;
                        }
                        case DabBlendMode::Additive: { // Modo Luz / Glow
                            const double srcA = finalAlpha;
                            const double dstR = static_cast<double>(dst.r);
                            const double dstG = static_cast<double>(dst.g);
                            const double dstB = static_cast<double>(dst.b);

                            const double addR = dstR + static_cast<double>(dab.color.r) * srcA;
                            const double addG = dstG + static_cast<double>(dab.color.g) * srcA;
                            const double addB = dstB + static_cast<double>(dab.color.b) * srcA;

                            ColorRGBA newColor{
                                static_cast<uint8_t>(std::clamp(addR, 0.0, 255.0)),
                                static_cast<uint8_t>(std::clamp(addG, 0.0, 255.0)),
                                static_cast<uint8_t>(std::clamp(addB, 0.0, 255.0)),
                                255
                            };
                            buffer.setPixel(px, py, newColor);
                            tileModified = true;
                            break;
                        }
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
