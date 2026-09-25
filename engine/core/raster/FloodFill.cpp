#include "FloodFill.hpp"
#include <deque>
#include <cmath>
#include <algorithm>
#include <cstring>

namespace aladyn::engine::raster {

struct Span {
    int x1;
    int x2;
    int y;
    int dy;
};

// Gera offsets circulares para dilatação/erosão
static std::vector<std::pair<int, int>> getCircularKernelOffsets(int radius) {
    std::vector<std::pair<int, int>> offsets;
    int r2 = radius * radius;
    for (int dy = -radius; dy <= radius; ++dy) {
        for (int dx = -radius; dx <= radius; ++dx) {
            if (dx * dx + dy * dy <= r2) {
                offsets.emplace_back(dx, dy);
            }
        }
    }
    return offsets;
}

bool FloodFill::execute(
    const canvas::PixelBuffer& sourceBuffer,
    int seedX,
    int seedY,
    const utils::ColorRGBA& fillColor,
    int tolerance,
    bool contiguous,
    int expandPx,
    // Sem efeito (achado em 2026-09-25 pelos avisos do compilador): nenhuma tela
    // oferece fechar lacunas nem suavizar o balde; o valor só atravessa as
    // camadas. Remover ou implementar: pendências da base, item 6.
    [[maybe_unused]] int gapClosingPx,
    [[maybe_unused]] bool antiAliasing,
    canvas::TileGrid& targetGrid,
    history::TileUndoManager& undoManager,
    int activeLayerIndex,
    const PixelContext& pCtx,
    utils::Rect2D& outAffectedBounds
) {
    const int width = sourceBuffer.getWidth();
    const int height = sourceBuffer.getHeight();

    if (seedX < 0 || seedX >= width || seedY < 0 || seedY >= height) {
        return false;
    }

    if (pCtx.selectionMask && pCtx.selectionMask->hasSelection()) {
        if (pCtx.selectionMask->getValue(seedX, seedY) == 0) {
            return false;
        }
    }

    const uint8_t* srcRaw = sourceBuffer.getData();
    if (!srcRaw) return false;

    auto getSrcPixel = [&](int x, int y) noexcept -> utils::ColorRGBA {
        size_t off = static_cast<size_t>(y * width + x) * 4;
        return utils::ColorRGBA{srcRaw[off + 0], srcRaw[off + 1], srcRaw[off + 2], srcRaw[off + 3]};
    };

    const utils::ColorRGBA targetColor = getSrcPixel(seedX, seedY);

    // Tolerância Euclidiana máxima em RGB
    const double tolNorm = std::clamp(tolerance, 0, 100) / 100.0;
    const double maxDist = tolNorm * 441.67295593;
    const int maxDistSq = static_cast<int>(std::round(maxDist * maxDist));

    auto matchesTarget = [&](int x, int y) noexcept -> bool {
        const utils::ColorRGBA c = getSrcPixel(x, y);
        int dr = static_cast<int>(c.r) - static_cast<int>(targetColor.r);
        int dg = static_cast<int>(c.g) - static_cast<int>(targetColor.g);
        int db = static_cast<int>(c.b) - static_cast<int>(targetColor.b);
        int da = static_cast<int>(c.a) - static_cast<int>(targetColor.a);
        return (dr * dr + dg * dg + db * db + (da * da) / 2) <= maxDistSq;
    };

    if (!matchesTarget(seedX, seedY)) {
        return false;
    }

    // ── FASE 1: Máscara de Preenchimento Inicial ─────────────────────────────
    std::vector<uint8_t> mask(static_cast<size_t>(width * height), 0);

    if (!contiguous) {
        // Modo Global: todos os pixels similares no canvas
        for (int y = 0; y < height; ++y) {
            int rowOff = y * width;
            for (int x = 0; x < width; ++x) {
                if (matchesTarget(x, y)) {
                    mask[rowOff + x] = 255;
                }
            }
        }
    } else {
        // Modo Contíguo: Scanline Flood Fill com fila de spans
        std::deque<Span> queue;

        int lx = seedX;
        while (lx > 0 && matchesTarget(lx - 1, seedY)) lx--;
        int rx = seedX;
        while (rx < width - 1 && matchesTarget(rx + 1, seedY)) rx++;

        for (int x = lx; x <= rx; ++x) {
            mask[seedY * width + x] = 255;
        }

        queue.push_back({lx, rx, seedY, 1});
        queue.push_back({lx, rx, seedY, -1});

        while (!queue.empty()) {
            Span sp = queue.front();
            queue.pop_front();

            int ny = sp.y + sp.dy;
            if (ny < 0 || ny >= height) continue;

            int x = sp.x1;
            while (x <= sp.x2) {
                if (matchesTarget(x, ny) && mask[ny * width + x] == 0) {
                    int l = x;
                    while (l > 0 && matchesTarget(l - 1, ny) && mask[ny * width + (l - 1)] == 0) l--;
                    int r = x;
                    while (r < width - 1 && matchesTarget(r + 1, ny) && mask[ny * width + (r + 1)] == 0) r++;

                    for (int i = l; i <= r; ++i) {
                        mask[ny * width + i] = 255;
                    }

                    queue.push_back({l, r, ny, sp.dy});
                    if (l < sp.x1 || r > sp.x2) {
                        queue.push_back({l, r, ny, -sp.dy});
                    }
                    x = r + 1;
                } else {
                    x++;
                }
            }
        }
    }

    // ── FASE 2: Expansão / Sangria sob o Lineart ─────────────────────────────
    if (expandPx != 0) {
        int radius = std::abs(expandPx);
        auto offsets = getCircularKernelOffsets(radius);
        std::vector<uint8_t> expandedMask = mask;

        if (expandPx > 0) {
            // Dilatação
            for (int y = 0; y < height; ++y) {
                for (int x = 0; x < width; ++x) {
                    if (mask[y * width + x] > 0) {
                        for (const auto& off : offsets) {
                            int nx = x + off.first;
                            int ny = y + off.second;
                            if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                                expandedMask[ny * width + nx] = 255;
                            }
                        }
                    }
                }
            }
        } else {
            // Erosão
            for (int y = 0; y < height; ++y) {
                for (int x = 0; x < width; ++x) {
                    if (mask[y * width + x] > 0) {
                        bool keep = true;
                        for (const auto& off : offsets) {
                            int nx = x + off.first;
                            int ny = y + off.second;
                            if (nx < 0 || nx >= width || ny < 0 || ny >= height || mask[ny * width + nx] == 0) {
                                keep = false;
                                break;
                            }
                        }
                        expandedMask[y * width + x] = keep ? 255 : 0;
                    }
                }
            }
        }
        mask = std::move(expandedMask);
    }

    // ── FASE 3: Gravação Direta nos Tiles da Camada Ativa ────────────────────
    int minX = width, maxX = 0, minY = height, maxY = 0;
    bool anyFilled = false;

    // Localiza bounds afetados
    for (int y = 0; y < height; ++y) {
        int rowOff = y * width;
        for (int x = 0; x < width; ++x) {
            if (mask[rowOff + x] > 0) {
                anyFilled = true;
                if (x < minX) minX = x;
                if (x > maxX) maxX = x;
                if (y < minY) minY = y;
                if (y > maxY) maxY = y;
            }
        }
    }

    if (!anyFilled) return false;

    outAffectedBounds = utils::Rect2D{
        static_cast<double>(minX),
        static_cast<double>(minY),
        static_cast<double>(maxX - minX + 1),
        static_cast<double>(maxY - minY + 1)
    };

    const int startTileX = minX / canvas::Tile::TILE_SIZE;
    const int endTileX   = maxX / canvas::Tile::TILE_SIZE;
    const int startTileY = minY / canvas::Tile::TILE_SIZE;
    const int endTileY   = maxY / canvas::Tile::TILE_SIZE;

    // Registra o estado 'before' dos tiles no UndoManager
    for (int ty = startTileY; ty <= endTileY; ++ty) {
        for (int tx = startTileX; tx <= endTileX; ++tx) {
            canvas::Tile* tile = targetGrid.getTile(tx, ty);
            if (tile) {
                const auto& buf = tile->getBuffer();
                undoManager.recordTileBefore(activeLayerIndex, tx, ty, buf.getData(), buf.getSizeInBytes());
            } else {
                canvas::PixelBuffer emptyBuf(canvas::Tile::TILE_SIZE, canvas::Tile::TILE_SIZE, {0, 0, 0, 0});
                undoManager.recordTileBefore(activeLayerIndex, tx, ty, emptyBuf.getData(), emptyBuf.getSizeInBytes());
            }
        }
    }

    // Escreve os pixels de preenchimento nos tiles
    for (int ty = startTileY; ty <= endTileY; ++ty) {
        for (int tx = startTileX; tx <= endTileX; ++tx) {
            canvas::Tile* tile = targetGrid.getOrCreateTile(tx, ty);
            uint8_t* tileRaw = tile->getBuffer().getData();
            int tilePixX = tile->getPixelX();
            int tilePixY = tile->getPixelY();

            for (int ly = 0; ly < canvas::Tile::TILE_SIZE; ++ly) {
                int gy = tilePixY + ly;
                if (gy >= height) break;

                int rowMask = gy * width;
                int rowTile = ly * canvas::Tile::TILE_SIZE;

                for (int lx = 0; lx < canvas::Tile::TILE_SIZE; ++lx) {
                    int gx = tilePixX + lx;
                    if (gx >= width) break;

                    uint8_t m = mask[rowMask + gx];
                    if (pCtx.selectionMask && pCtx.selectionMask->hasSelection()) {
                        uint8_t selVal = pCtx.selectionMask->getValue(gx, gy);
                        if (selVal == 0) continue;
                        m = static_cast<uint8_t>((static_cast<int>(m) * selVal) / 255);
                    }

                    if (m > 0) {
                        size_t off = static_cast<size_t>(rowTile + lx) * 4;
                        double srcA = (fillColor.a / 255.0) * (m / 255.0);

                        if (pCtx.alphaLocked) {
                            if (tileRaw[off + 3] > 0) {
                                tileRaw[off + 0] = static_cast<uint8_t>(tileRaw[off + 0] * (1.0 - srcA) + fillColor.r * srcA);
                                tileRaw[off + 1] = static_cast<uint8_t>(tileRaw[off + 1] * (1.0 - srcA) + fillColor.g * srcA);
                                tileRaw[off + 2] = static_cast<uint8_t>(tileRaw[off + 2] * (1.0 - srcA) + fillColor.b * srcA);
                            }
                        } else {
                            if (m == 255 && fillColor.a == 255) {
                                tileRaw[off + 0] = fillColor.r;
                                tileRaw[off + 1] = fillColor.g;
                                tileRaw[off + 2] = fillColor.b;
                                tileRaw[off + 3] = 255;
                            } else {
                                double dstA = tileRaw[off + 3] / 255.0;
                                double outA = srcA + dstA * (1.0 - srcA);
                                if (outA > 0.001) {
                                    tileRaw[off + 0] = static_cast<uint8_t>(std::clamp((fillColor.r * srcA + tileRaw[off + 0] * dstA * (1.0 - srcA)) / outA, 0.0, 255.0));
                                    tileRaw[off + 1] = static_cast<uint8_t>(std::clamp((fillColor.g * srcA + tileRaw[off + 1] * dstA * (1.0 - srcA)) / outA, 0.0, 255.0));
                                    tileRaw[off + 2] = static_cast<uint8_t>(std::clamp((fillColor.b * srcA + tileRaw[off + 2] * dstA * (1.0 - srcA)) / outA, 0.0, 255.0));
                                    tileRaw[off + 3] = static_cast<uint8_t>(std::clamp(outA * 255.0, 0.0, 255.0));
                                }
                            }
                        }
                    }
                }
            }
            tile->setDirty(true);
        }
    }

    return true;
}

} // namespace aladyn::engine::raster
