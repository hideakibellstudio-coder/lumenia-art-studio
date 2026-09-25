#include "SelectionEngine.hpp"
#include <deque>
#include <cmath>
#include <algorithm>
#include <cstring>

namespace aladyn::engine::selection {

struct Span {
    int x1;
    int x2;
    int y;
    int dy;
};

static std::vector<std::pair<int, int>> getCircularOffsets(int radius) {
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

std::vector<uint8_t> SelectionEngine::generateWandMask(
    const canvas::PixelBuffer& sourceBuffer,
    int seedX,
    int seedY,
    int tolerance,
    bool contiguous,
    int expandPx,
    bool antiAliasing
) {
    const int width = sourceBuffer.getWidth();
    const int height = sourceBuffer.getHeight();

    if (seedX < 0 || seedX >= width || seedY < 0 || seedY >= height || width <= 0 || height <= 0) {
        return {};
    }

    const uint8_t* srcRaw = sourceBuffer.getData();
    if (!srcRaw) return {};

    const size_t totalPixels = static_cast<size_t>(width * height);
    std::vector<uint8_t> mask(totalPixels, 0);

    const size_t targetOff = static_cast<size_t>(seedY * width + seedX) * 4;
    const utils::ColorRGBA targetColor{
        srcRaw[targetOff + 0],
        srcRaw[targetOff + 1],
        srcRaw[targetOff + 2],
        srcRaw[targetOff + 3]
    };

    const double tolNorm = (std::clamp(tolerance, 0, 100) / 100.0) * 441.67295593;
    const double tolSq = tolNorm * tolNorm;

    auto matchesTarget = [&](int x, int y) noexcept -> bool {
        const size_t off = static_cast<size_t>(y * width + x) * 4;
        const double dr = static_cast<double>(srcRaw[off + 0]) - static_cast<double>(targetColor.r);
        const double dg = static_cast<double>(srcRaw[off + 1]) - static_cast<double>(targetColor.g);
        const double db = static_cast<double>(srcRaw[off + 2]) - static_cast<double>(targetColor.b);
        const double da = static_cast<double>(srcRaw[off + 3]) - static_cast<double>(targetColor.a);
        const double distSq = dr * dr + dg * dg + db * db + da * da;
        return distSq <= tolSq;
    };

    if (!matchesTarget(seedX, seedY)) {
        return mask;
    }

    if (!contiguous) {
        // Seleção Global por Cor
        for (int y = 0; y < height; ++y) {
            const size_t rowOff = static_cast<size_t>(y * width);
            for (int x = 0; x < width; ++x) {
                if (matchesTarget(x, y)) {
                    mask[rowOff + x] = 255;
                }
            }
        }
    } else {
        // Scanline Span Flood Fill (Contíguo)
        std::deque<Span> spans;
        int l = seedX;
        while (l > 0 && matchesTarget(l - 1, seedY)) --l;
        int r = seedX;
        while (r < width - 1 && matchesTarget(r + 1, seedY)) ++r;

        for (int x = l; x <= r; ++x) {
            mask[static_cast<size_t>(seedY * width + x)] = 255;
        }

        if (seedY > 0) spans.push_back({l, r, seedY - 1, -1});
        if (seedY < height - 1) spans.push_back({l, r, seedY + 1, 1});

        while (!spans.empty()) {
            Span sp = spans.front();
            spans.pop_front();

            int y = sp.y;
            int prevX1 = sp.x1;
            int prevX2 = sp.x2;
            int dy = sp.dy;

            int x = prevX1;
            while (x <= prevX2) {
                if (matchesTarget(x, y) && mask[static_cast<size_t>(y * width + x)] == 0) {
                    int spanL = x;
                    while (spanL > 0 && matchesTarget(spanL - 1, y) && mask[static_cast<size_t>(y * width + (spanL - 1))] == 0) {
                        --spanL;
                    }

                    int spanR = x;
                    while (spanR < width - 1 && matchesTarget(spanR + 1, y) && mask[static_cast<size_t>(y * width + (spanR + 1))] == 0) {
                        ++spanR;
                    }

                    for (int fillX = spanL; fillX <= spanR; ++fillX) {
                        mask[static_cast<size_t>(y * width + fillX)] = 255;
                    }

                    if (y + dy >= 0 && y + dy < height) {
                        spans.push_back({spanL, spanR, y + dy, dy});
                    }

                    if (spanL < prevX1 - 1 && (y - dy >= 0 && y - dy < height)) {
                        spans.push_back({spanL, prevX1 - 1, y - dy, -dy});
                    }
                    if (spanR > prevX2 + 1 && (y - dy >= 0 && y - dy < height)) {
                        spans.push_back({prevX2 + 1, spanR, y - dy, -dy});
                    }

                    x = spanR + 1;
                } else {
                    ++x;
                }
            }
        }
    }

    // Expansão / Contração Morfológica
    if (expandPx != 0) {
        std::vector<uint8_t> expandedMask = mask;
        int absExp = std::min(10, std::abs(expandPx));
        auto offsets = getCircularOffsets(absExp);

        if (expandPx > 0) {
            // Dilatação
            for (int y = 0; y < height; ++y) {
                for (int x = 0; x < width; ++x) {
                    if (mask[static_cast<size_t>(y * width + x)] == 255) {
                        for (const auto& [dx, dy] : offsets) {
                            int nx = x + dx;
                            int ny = y + dy;
                            if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                                expandedMask[static_cast<size_t>(ny * width + nx)] = 255;
                            }
                        }
                    }
                }
            }
        } else {
            // Erosão
            for (int y = 0; y < height; ++y) {
                for (int x = 0; x < width; ++x) {
                    if (mask[static_cast<size_t>(y * width + x)] == 255) {
                        bool keep = true;
                        for (const auto& [dx, dy] : offsets) {
                            int nx = x + dx;
                            int ny = y + dy;
                            if (nx < 0 || nx >= width || ny < 0 || ny >= height || mask[static_cast<size_t>(ny * width + nx)] == 0) {
                                keep = false;
                                break;
                            }
                        }
                        if (!keep) {
                            expandedMask[static_cast<size_t>(y * width + x)] = 0;
                        }
                    }
                }
            }
        }
        mask = std::move(expandedMask);
    }

    // Suavização Anti-Aliasing nas Bordas
    if (antiAliasing) {
        std::vector<uint8_t> aaMask = mask;
        for (int y = 1; y < height - 1; ++y) {
            for (int x = 1; x < width - 1; ++x) {
                const size_t idx = static_cast<size_t>(y * width + x);
                if (mask[idx] == 0) {
                    int neighborSum = 0;
                    neighborSum += (mask[idx - 1] > 0);
                    neighborSum += (mask[idx + 1] > 0);
                    neighborSum += (mask[idx - width] > 0);
                    neighborSum += (mask[idx + width] > 0);
                    if (neighborSum >= 3) {
                        aaMask[idx] = 160;
                    } else if (neighborSum == 2) {
                        aaMask[idx] = 90;
                    }
                } else if (mask[idx] == 255) {
                    int zeroNeighbors = 0;
                    zeroNeighbors += (mask[idx - 1] == 0);
                    zeroNeighbors += (mask[idx + 1] == 0);
                    zeroNeighbors += (mask[idx - width] == 0);
                    zeroNeighbors += (mask[idx + width] == 0);
                    if (zeroNeighbors >= 2) {
                        aaMask[idx] = 200;
                    }
                }
            }
        }
        mask = std::move(aaMask);
    }

    return mask;
}

void SelectionEngine::applyFeather(std::vector<uint8_t>& mask, int width, int height, int featherPx) {
    if (featherPx <= 0 || mask.empty() || width <= 0 || height <= 0) return;
    int r = std::min(featherPx, 50);

    std::vector<uint8_t> temp(mask.size(), 0);

    // Passagem 1: Horizontal Box Blur
    for (int y = 0; y < height; ++y) {
        const size_t rowOff = static_cast<size_t>(y * width);
        int sum = 0;
        int windowSize = 0;

        for (int k = -r; k <= r; ++k) {
            int px = std::clamp(k, 0, width - 1);
            sum += mask[rowOff + px];
            windowSize++;
        }

        for (int x = 0; x < width; ++x) {
            temp[rowOff + x] = static_cast<uint8_t>(sum / windowSize);

            int leftOut = std::clamp(x - r, 0, width - 1);
            int rightIn = std::clamp(x + r + 1, 0, width - 1);
            sum += mask[rowOff + rightIn] - mask[rowOff + leftOut];
        }
    }

    // Passagem 2: Vertical Box Blur
    for (int x = 0; x < width; ++x) {
        int sum = 0;
        int windowSize = 0;

        for (int k = -r; k <= r; ++k) {
            int py = std::clamp(k, 0, height - 1);
            sum += temp[static_cast<size_t>(py * width + x)];
            windowSize++;
        }

        for (int y = 0; y < height; ++y) {
            mask[static_cast<size_t>(y * width + x)] = static_cast<uint8_t>(sum / windowSize);

            int topOut = std::clamp(y - r, 0, height - 1);
            int bottomIn = std::clamp(y + r + 1, 0, height - 1);
            sum += temp[static_cast<size_t>(bottomIn * width + x)] - temp[static_cast<size_t>(topOut * width + x)];
        }
    }
}

// generateRectMask / generateEllipseMask / generatePolygonMask vivem em
// SelectionShapeMasks.cpp (divisão de 2026-09-22: 454 linhas, teto ARCcC 450).


} // namespace aladyn::engine::selection
