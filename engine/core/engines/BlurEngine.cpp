
#include "BlurEngine.hpp"
#include "../canvas/SpatialCuller.hpp"
#include "../math/Rect2D.hpp"
#include "../document/Layer.hpp"
#include "../raster/PixelContext.hpp"
#include <cmath>
#include <algorithm>
#include <vector>

namespace aladyn::engine::engines {

// ─── HELPER: Amostra um pixel do compositeBuffer (visão de todas as camadas)
// ou, como fallback, do próprio tile grid da camada ativa.
// Isso resolve o problema #1: o blur deve ler o que o artista VÊ, não só a camada ativa.
static raster::ColorRGBA sampleSource(
    int globalX, int globalY,
    const canvas::PixelBuffer* compositeBuffer,
    const canvas::TileGrid& tileGrid
) {
    // Preferência: ler do compositeBuffer (saída do compositor = visão achatada de tudo)
    if (compositeBuffer) {
        return compositeBuffer->getPixel(globalX, globalY);
    }
    // Fallback: lê do próprio tile da camada ativa
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
    const canvas::PixelBuffer* compositeBuffer,
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

    // ─── CORREÇÃO #3 & #4: Raio do kernel gaussiano escala com o pincel.
    // blurRadius (1–5) é um multiplicador de cobertura relativo ao raio do dab.
    // blurStrength (0–1) controla o sigma — quanto mais alto, mais suave e difuso.
    const int   blurRadiusCfg = std::clamp(profile.blurParams.blurRadius, 1, 5);
    const double blurStr      = std::clamp(profile.blurParams.blurStrength, 0.0, 1.0);

    // Kernel radius em pixels: escala com o diâmetro do dab
    const int kernelR = static_cast<int>(std::clamp(
        r * 0.15 * static_cast<double>(blurRadiusCfg),
        1.0, 16.0
    ));
    // Sigma gaussiano: blurStrength controla a suavidade real do kernel
    const double sigma = std::max(0.5, static_cast<double>(kernelR) * (0.3 + blurStr * 0.7));

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

        // ─── CORREÇÃO #2: Buffer de snapshot do tile ANTES de qualquer escrita.
        // Impede que pixels já escritos neste dab contaminem a amostragem dos vizinhos.
        // O blur lê sempre do estado "antes do dab começar" — não do estado parcialmente modificado.
        const int snapshotW = maxX - minX + 1;
        const int snapshotH = maxY - minY + 1;
        if (snapshotW <= 0 || snapshotH <= 0) continue;

        // Snapshot da camada ativa nessa região (para alpha/origPx)
        std::vector<raster::ColorRGBA> snapshot(
            static_cast<size_t>(snapshotW * snapshotH)
        );
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

                // Falloff do pincel com smoothstep
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

                // ─── CORREÇÃO #1 & #2: Kernel gaussiano lê do compositeBuffer (fonte correta).
                // Usamos a mesma função helper para amostragem uniforme.
                double sumR = 0.0, sumG = 0.0, sumB = 0.0, sumA = 0.0;
                double totalWeight    = 0.0;
                double alphaWeightSum = 0.0;

                for (int ky = -kernelR; ky <= kernelR; ++ky) {
                    for (int kx = -kernelR; kx <= kernelR; ++kx) {
                        // Peso gaussiano normalizado com sigma escalado
                        const double w = std::exp(-(kx * kx + ky * ky) / (2.0 * sigma * sigma));

                        // ← Lê do compositeBuffer (visão achatada de todas as camadas)
                        const raster::ColorRGBA s = sampleSource(
                            globalX + kx, globalY + ky, compositeBuffer, tileGrid
                        );
                        const double aNorm = static_cast<double>(s.a) / 255.0;

                        sumR += s.r * aNorm * w;
                        sumG += s.g * aNorm * w;
                        sumB += s.b * aNorm * w;
                        sumA += s.a * w;

                        totalWeight    += w;
                        alphaWeightSum += aNorm * w;
                    }
                }

                // Clip mask check
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

                // Lê o estado original da camada ativa (do snapshot, não do buffer já modificado)
                const int si = (py - minY) * snapshotW + (px - minX);
                const raster::ColorRGBA origPx = snapshot[static_cast<size_t>(si)];

                if (ctx.alphaLocked && origPx.a == 0) continue;
                if (origPx.a == 0 && alphaWeightSum <= 0.0) continue;

                // Cor suavizada (RGB do compositeBuffer desfocado)
                double targetR = static_cast<double>(origPx.r);
                double targetG = static_cast<double>(origPx.g);
                double targetB = static_cast<double>(origPx.b);
                if (alphaWeightSum > 0.0) {
                    targetR = sumR / alphaWeightSum;
                    targetG = sumG / alphaWeightSum;
                    targetB = sumB / alphaWeightSum;
                }

                // Mistura com a cor original da camada ativa pelo mixFactor
                const double outR = origPx.r * (1.0 - curMixFactor) + targetR * curMixFactor;
                const double outG = origPx.g * (1.0 - curMixFactor) + targetG * curMixFactor;
                const double outB = origPx.b * (1.0 - curMixFactor) + targetB * curMixFactor;

                // Alpha: preserva estritamente. Só espalha suavemente nas bordas.
                double outA = static_cast<double>(origPx.a);
                if (!ctx.alphaLocked) {
                    if (origPx.a > 0) {
                        const double smoothedA = sumA / totalWeight;
                        outA = std::max(static_cast<double>(origPx.a), smoothedA);
                    } else if (alphaWeightSum > 0.0) {
                        // Borda: leve dispersão suave para suavizar contornos duros
                        outA = (sumA / totalWeight) * curMixFactor * 0.35;
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
