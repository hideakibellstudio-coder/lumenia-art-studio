// Máscaras geométricas do SelectionEngine (retângulo, elipse, polígono) --
// separadas de SelectionEngine.cpp em 2026-09-22 (teto ARCcC de 450 linhas).
// O polígono (laço) ganhou suavização de verdade em 2026-09-25.
#include "SelectionEngine.hpp"
#include <deque>
#include <cmath>
#include <algorithm>
#include <cstdint>
#include <cstring>

namespace aladyn::engine::selection {

namespace {

// Cobertura horizontal exata de [x0, x1) somada em `coverage` com peso `weight`.
void addSpanCoverage(std::vector<double>& coverage, double x0, double x1, double weight) {
    const double width = static_cast<double>(coverage.size());
    x0 = std::clamp(x0, 0.0, width);
    x1 = std::clamp(x1, 0.0, width);
    if (x1 <= x0) return;
    const int first = static_cast<int>(x0);
    const int last = std::min(static_cast<int>(x1), static_cast<int>(coverage.size()) - 1);
    if (first == last) {
        coverage[first] += (x1 - x0) * weight;
        return;
    }
    coverage[first] += (first + 1 - x0) * weight;
    for (int x = first + 1; x < last; ++x) coverage[x] += weight;
    coverage[last] += (x1 - last) * weight;
}

// Interseções da linha horizontal `scanY` com as arestas do polígono, em ordem.
void scanlineCrossings(const std::vector<std::pair<int, int>>& points, double scanY, std::vector<double>& out) {
    out.clear();
    size_t j = points.size() - 1;
    for (size_t i = 0; i < points.size(); ++i) {
        const double yI = points[i].second;
        const double yJ = points[j].second;
        if ((yI < scanY && yJ >= scanY) || (yJ < scanY && yI >= scanY)) {
            const double xI = points[i].first;
            const double xJ = points[j].first;
            out.push_back(xI + (scanY - yI) / (yJ - yI) * (xJ - xI));
        }
        j = i;
    }
    std::sort(out.begin(), out.end());
}

} // namespace

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
    std::vector<uint8_t> mask(static_cast<size_t>(width) * static_cast<size_t>(height), 0);

    // 64 bits: x + w, -w e o quadrado do raio estouram `int` com coordenadas extremas
    // (select_rect(INT_MAX, 0, 1, 1) derrubava o processo ate 2026-10-01).
    int64_t left = x, top = y, span = w, rise = h;
    if (span < 0) { left += span; span = -span; }
    if (rise < 0) { top += rise; rise = -rise; }
    if (span == 0 || rise == 0) return mask;

    const int64_t x1 = std::max<int64_t>(0, left);
    const int64_t y1 = std::max<int64_t>(0, top);
    const int64_t x2 = std::min<int64_t>(width - 1, left + span - 1);
    const int64_t y2 = std::min<int64_t>(height - 1, top + rise - 1);

    if (x1 > x2 || y1 > y2) return mask;

    const int64_t cr = std::clamp<int64_t>(cornerRadiusPx, 0, std::min(span, rise) / 2);

    for (int64_t py = y1; py <= y2; ++py) {
        const size_t rowOff = static_cast<size_t>(py) * static_cast<size_t>(width);
        for (int64_t px = x1; px <= x2; ++px) {
            if (cr > 0) {
                int64_t dx = 0, dy = 0;
                if (px < left + cr) dx = (left + cr) - px;
                else if (px > left + span - 1 - cr) dx = px - (left + span - 1 - cr);

                if (py < top + cr) dy = (top + cr) - py;
                else if (py > top + rise - 1 - cr) dy = py - (top + rise - 1 - cr);

                if (dx > 0 && dy > 0) {
                    if (dx * dx + dy * dy > cr * cr) continue;
                }
            }
            mask[rowOff + static_cast<size_t>(px)] = 255;
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
    std::vector<uint8_t> mask(static_cast<size_t>(width) * static_cast<size_t>(height), 0);

    // 64 bits: |INT_MIN|, cx - rx - 1 e px - cx estouram `int` com coordenadas extremas.
    const int64_t radiusX = std::llabs(static_cast<int64_t>(rx));
    const int64_t radiusY = std::llabs(static_cast<int64_t>(ry));
    if (radiusX <= 0 || radiusY <= 0) return mask;

    const int x1 = static_cast<int>(std::max<int64_t>(0, static_cast<int64_t>(cx) - radiusX - 1));
    const int y1 = static_cast<int>(std::max<int64_t>(0, static_cast<int64_t>(cy) - radiusY - 1));
    const int x2 = static_cast<int>(std::min<int64_t>(width - 1, static_cast<int64_t>(cx) + radiusX + 1));
    const int y2 = static_cast<int>(std::min<int64_t>(height - 1, static_cast<int64_t>(cy) + radiusY + 1));

    if (x1 > x2 || y1 > y2) return mask;

    const double invRx2 = 1.0 / (static_cast<double>(radiusX) * static_cast<double>(radiusX));
    const double invRy2 = 1.0 / (static_cast<double>(radiusY) * static_cast<double>(radiusY));

    for (int py = y1; py <= y2; ++py) {
        const size_t rowOff = static_cast<size_t>(py) * static_cast<size_t>(width);
        double dy = (static_cast<double>(py) - cy + 0.5);
        double dy2 = dy * dy * invRy2;

        for (int px = x1; px <= x2; ++px) {
            double dx = (static_cast<double>(px) - cx + 0.5);
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
    std::vector<uint8_t> mask(static_cast<size_t>(width) * static_cast<size_t>(height), 0);

    int minY = height, maxY = 0;
    for (const auto& pt : points) {
        minY = std::min(minY, pt.second);
        maxY = std::max(maxY, pt.second);
    }
    minY = std::max(0, minY);
    maxY = std::min(height - 1, maxY);

    if (antiAliasing) {
        // Até 2026-09-25 este parâmetro era ignorado e o botão Anti-Alias da
        // barra não mudava nada no laço. Cobertura de área: SUBROWS linhas de
        // varredura por pixel, com a parte horizontal exata.
        constexpr int SUBROWS = 4;
        std::vector<double> coverage(static_cast<size_t>(width));
        std::vector<double> crossings;
        for (int y = minY; y <= maxY; ++y) {
            std::fill(coverage.begin(), coverage.end(), 0.0);
            for (int s = 0; s < SUBROWS; ++s) {
                scanlineCrossings(points, y + (s + 0.5) / SUBROWS, crossings);
                for (size_t k = 0; k + 1 < crossings.size(); k += 2) {
                    addSpanCoverage(coverage, crossings[k], crossings[k + 1], 1.0 / SUBROWS);
                }
            }
            const size_t rowOff = static_cast<size_t>(y) * static_cast<size_t>(width);
            for (int x = 0; x < width; ++x) {
                mask[rowOff + x] = static_cast<uint8_t>(std::lround(std::clamp(coverage[x], 0.0, 1.0) * 255.0));
            }
        }
        if (featherPx > 0) {
            applyFeather(mask, width, height, featherPx);
        }
        return mask;
    }

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
                // O corte pode cair muito fora do canvas (pontos extremos): convertido para `int` so
                // depois de preso ao canvas, que e' o que importa; a conversao direta e' indefinida.
                const double crossing = xI + (scanY - yI) / (yJ - yI) * (xJ - xI) + 0.5;
                nodeX.push_back(static_cast<int>(std::clamp(crossing, -1.0, static_cast<double>(width) + 1.0)));
            }
            j = i;
        }

        std::sort(nodeX.begin(), nodeX.end());

        const size_t rowOff = static_cast<size_t>(y) * static_cast<size_t>(width);
        for (size_t k = 0; k + 1 < nodeX.size(); k += 2) {
            // Centro do pixel dentro do contorno: [início, fim). Até 2026-09-25 o
            // fim era inclusivo e o laço ganhava uma coluna à direita.
            int xStart = std::max(0, nodeX[k]);
            int xEnd = std::min(width, nodeX[k + 1]);
            for (int x = xStart; x < xEnd; ++x) {
                mask[rowOff + x] = 255;
            }
        }
    }

    if (featherPx > 0) {
        applyFeather(mask, width, height, featherPx);
    }

    return mask;
}

} // namespace aladyn::engine::selection
