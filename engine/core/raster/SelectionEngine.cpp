#include "SelectionEngine.hpp"
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
    const ColorRGBA targetColor{
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

std::vector<uint8_t> SelectionEngine::generateRectMask(
    int width,
    int height,
    int x,
    int y,
    int w,
    int h,
    int featherPx,
    int cornerRadiusPx
) {
    if (width <= 0 || height <= 0) return {};
    std::vector<uint8_t> mask(static_cast<size_t>(width * height), 0);

    if (w < 0) { x += w; w = -w; }
    if (h < 0) { y += h; h = -h; }
    if (w == 0 || h == 0) return mask;

    int x1 = std::max(0, x);
    int y1 = std::max(0, y);
    int x2 = std::min(width - 1, x + w - 1);
    int y2 = std::min(height - 1, y + h - 1);

    if (x1 > x2 || y1 > y2) return mask;

    int cr = std::clamp(cornerRadiusPx, 0, std::min(w, h) / 2);

    for (int py = y1; py <= y2; ++py) {
        const size_t rowOff = static_cast<size_t>(py * width);
        for (int px = x1; px <= x2; ++px) {
            if (cr > 0) {
                int dx = 0, dy = 0;
                if (px < x + cr) dx = (x + cr) - px;
                else if (px > x + w - 1 - cr) dx = px - (x + w - 1 - cr);

                if (py < y + cr) dy = (y + cr) - py;
                else if (py > y + h - 1 - cr) dy = py - (y + h - 1 - cr);

                if (dx > 0 && dy > 0) {
                    if (dx * dx + dy * dy > cr * cr) continue;
                }
            }
            mask[rowOff + px] = 255;
        }
    }

    if (featherPx > 0) {
        applyFeather(mask, width, height, featherPx);
    }

    return mask;
}

std::vector<uint8_t> SelectionEngine::generateEllipseMask(
    int width,
    int height,
    int cx,
    int cy,
    int rx,
    int ry,
    bool antiAliasing,
    int featherPx
) {
    if (width <= 0 || height <= 0) return {};
    std::vector<uint8_t> mask(static_cast<size_t>(width * height), 0);

    rx = std::abs(rx);
    ry = std::abs(ry);
    if (rx <= 0 || ry <= 0) return mask;

    int x1 = std::max(0, cx - rx - 1);
    int y1 = std::max(0, cy - ry - 1);
    int x2 = std::min(width - 1, cx + rx + 1);
    int y2 = std::min(height - 1, cy + ry + 1);

    if (x1 > x2 || y1 > y2) return mask;

    const double invRx2 = 1.0 / (static_cast<double>(rx) * rx);
    const double invRy2 = 1.0 / (static_cast<double>(ry) * ry);

    for (int py = y1; py <= y2; ++py) {
        const size_t rowOff = static_cast<size_t>(py * width);
        double dy = (py - cy + 0.5);
        double dy2 = dy * dy * invRy2;

        for (int px = x1; px <= x2; ++px) {
            double dx = (px - cx + 0.5);
            double val = dx * dx * invRx2 + dy2;

            if (val <= 1.0) {
                if (antiAliasing && val > 0.0) {
                    double r_pixel = std::sqrt(dx * dx + dy * dy);
                    double r_edge = r_pixel / std::sqrt(val);
                    double dist_px = r_edge - r_pixel;
                    if (dist_px < 0.5) {
                        double cov = dist_px + 0.5;
                        mask[rowOff + px] = static_cast<uint8_t>(std::clamp(cov * 255.0, 0.0, 255.0));
                    } else {
                        mask[rowOff + px] = 255;
                    }
                } else {
                    mask[rowOff + px] = 255;
                }
            } else if (antiAliasing) {
                double r_pixel = std::sqrt(dx * dx + dy * dy);
                double r_edge = r_pixel / std::sqrt(val);
                double dist_px = r_edge - r_pixel;
                if (dist_px > -0.5) {
                    double cov = dist_px + 0.5;
                    mask[rowOff + px] = static_cast<uint8_t>(std::clamp(cov * 255.0, 0.0, 255.0));
                }
            }
        }
    }

    if (featherPx > 0) {
        applyFeather(mask, width, height, featherPx);
    }

    return mask;
}

std::vector<uint8_t> SelectionEngine::generatePolygonMask(
    int width,
    int height,
    const std::vector<std::pair<int, int>>& points,
    bool antiAliasing,
    int featherPx
) {
    if (width <= 0 || height <= 0 || points.size() < 3) return {};
    std::vector<uint8_t> mask(static_cast<size_t>(width * height), 0);

    int minY = height, maxY = 0;
    for (const auto& pt : points) {
        minY = std::min(minY, pt.second);
        maxY = std::max(maxY, pt.second);
    }
    minY = std::max(0, minY);
    maxY = std::min(height - 1, maxY);

    const size_t numPoints = points.size();
    std::vector<int> nodeX;
    nodeX.reserve(16);

    for (int y = minY; y <= maxY; ++y) {
        nodeX.clear();
        double scanY = y + 0.5;

        size_t j = numPoints - 1;
        for (size_t i = 0; i < numPoints; ++i) {
            double yI = points[i].second;
            double yJ = points[j].second;
            double xI = points[i].first;
            double xJ = points[j].first;

            if ((yI < scanY && yJ >= scanY) || (yJ < scanY && yI >= scanY)) {
                int intersectX = static_cast<int>(xI + (scanY - yI) / (yJ - yI) * (xJ - xI) + 0.5);
                nodeX.push_back(intersectX);
            }
            j = i;
        }

        std::sort(nodeX.begin(), nodeX.end());

        const size_t rowOff = static_cast<size_t>(y * width);
        for (size_t k = 0; k + 1 < nodeX.size(); k += 2) {
            int xStart = std::max(0, nodeX[k]);
            int xEnd = std::min(width - 1, nodeX[k + 1]);
            for (int x = xStart; x <= xEnd; ++x) {
                mask[rowOff + x] = 255;
            }
        }
    }

    if (featherPx > 0) {
        applyFeather(mask, width, height, featherPx);
    }

    return mask;
}

} // namespace aladyn::engine::raster
