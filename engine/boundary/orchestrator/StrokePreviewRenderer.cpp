#include "StrokePreviewRenderer.hpp"
#include "BrushEngineFactory.hpp"
#include "../../core/canvas/CanvasTexture.hpp"
#include "../../core/canvas/TileGrid.hpp"
#include "../../core/canvas/Tile.hpp"
#include "../../core/raster/DabInterpolator.hpp"
#include "../../core/raster/DabRenderer.hpp"
#include "../../core/raster/LargeBrushOptimizer.hpp"
#include <algorithm>
#include <cmath>
#include <memory>

namespace aladyn::engine::boundary::orchestrator {

namespace {

constexpr double kPi = 3.141592653589793;
constexpr int kMaxPreviewSide = 4096;  // o painel usa ~260x52; teto defensivo de memória

// Motores que ALTERAM pixels existentes (borracha, desfoque, borrar) precisam de
// uma base pintada para que o efeito apareça na prévia.
void paintDemoBase(int width, int height, const canvas::CanvasTexture& tex, canvas::TileGrid& grid) {
    brush::BrushProfile base;
    base.brushSize = static_cast<double>(height) * 0.7;
    base.opacity = 1.0;
    base.hardness = 0.9;
    base.baseColor = {70, 130, 240, 255};
    for (int x = 20; x < width - 20; x += 15) {
        utils::Dab dab;
        dab.position = {static_cast<double>(x), static_cast<double>(height) / 2.0};
        dab.radius = base.brushSize / 2.0;
        dab.pressure = 1.0;
        raster::DabRenderer::renderDab(dab, base, tex, grid);
    }
}

void copyGridToRgba(canvas::TileGrid& grid, int width, int height, std::vector<uint8_t>& out) {
    for (int ty = 0; ty < grid.getTilesCountY(); ++ty) {
        for (int tx = 0; tx < grid.getTilesCountX(); ++tx) {
            const canvas::Tile* tile = grid.getTile(tx, ty);
            if (!tile) continue;
            const canvas::PixelBuffer& buf = tile->getBuffer();
            const int startX = tx * canvas::Tile::TILE_SIZE;
            const int startY = ty * canvas::Tile::TILE_SIZE;
            for (int py = 0; py < canvas::Tile::TILE_SIZE; ++py) {
                const int gy = startY + py;
                if (gy >= height) break;
                for (int px = 0; px < canvas::Tile::TILE_SIZE; ++px) {
                    const int gx = startX + px;
                    if (gx >= width) break;
                    const utils::ColorRGBA pixel = buf.getPixel(px, py);
                    if (pixel.a == 0) continue;
                    const size_t idx = (static_cast<size_t>(gy) * static_cast<size_t>(width) + static_cast<size_t>(gx)) * 4u;
                    out[idx + 0] = pixel.r;
                    out[idx + 1] = pixel.g;
                    out[idx + 2] = pixel.b;
                    out[idx + 3] = pixel.a;
                }
            }
        }
    }
}

} // namespace

std::vector<uint8_t> renderStrokePreview(const brush::BrushProfile& profile, int width, int height) {
    if (width <= 0 || height <= 0 || width > kMaxPreviewSide || height > kMaxPreviewSide) return {};

    std::vector<uint8_t> output(static_cast<size_t>(width) * static_cast<size_t>(height) * 4u, 0);
    canvas::TileGrid grid(width, height);
    canvas::CanvasTexture canvasTex;

    std::unique_ptr<engines::IBrushEngine> engine = BrushEngineFactory::create(profile.engineType);
    if (engine) engine->onActivate(profile);

    if (profile.engineType == brush::EngineType::Eraser ||
        profile.engineType == brush::EngineType::Blur ||
        profile.engineType == brush::EngineType::Smudge) {
        paintDemoBase(width, height, canvasTex, grid);
    }

    const double margin = 14.0;
    const double utilW = static_cast<double>(width) - 2.0 * margin;
    const double amp = (static_cast<double>(height) / 2.0 - 8.0) * 0.7;
    const double midY = static_cast<double>(height) / 2.0;
    const double targetMaxRadius = std::clamp(profile.brushSize * 0.4, 2.0, std::max(2.0, static_cast<double>(height) / 2.0 - 4.0));

    auto renderSingleDab = [&](const utils::Dab& d) {
        if (engine) engine->renderDab(d, profile, canvasTex, grid, nullptr, {});
        else raster::DabRenderer::renderDab(d, profile, canvasTex, grid);
    };

    constexpr int numSteps = 80;
    double carryover = 0.0;
    utils::Dab prevDab;
    bool hasPrev = false;
    for (int i = 0; i <= numSteps; ++i) {
        const double t = static_cast<double>(i) / numSteps;
        const double x = margin + t * utilW;
        const double y = midY + std::sin(t * 2.0 * kPi) * amp;
        const double pressure = 0.2 + 0.8 * std::sin(t * kPi);

        double angle = 0.0;
        if (i < numSteps) {
            const double nt = static_cast<double>(i + 1) / numSteps;
            const double nx = margin + nt * utilW;
            const double ny = midY + std::sin(nt * 2.0 * kPi) * amp;
            angle = std::atan2(ny - y, nx - x) * (180.0 / kPi);
        }

        utils::Dab currDab;
        currDab.position = {x, y};
        currDab.radius = std::max(0.5, targetMaxRadius * pressure);
        currDab.pressure = pressure;
        currDab.angle = angle;

        const utils::Dab& from = hasPrev ? prevDab : currDab;
        for (const auto& d : raster::DabInterpolator::interpolate(from, currDab, profile.spacingFactor, carryover)) {
            renderSingleDab(d);
        }
        prevDab = currDab;
        hasPrev = true;
    }

    copyGridToRgba(grid, width, height, output);
    return output;
}

std::vector<uint8_t> renderRoundTipMask(double hardness) {
    constexpr int sz = kRoundTipPreviewSize;
    const double center = sz / 2.0;
    const double maxDist = center - 2.0;
    const double hardSpan = std::clamp(hardness, 0.0, 0.99) * maxDist;
    const double invSoftSpan = 1.0 / std::max(0.001, maxDist - hardSpan);
    std::vector<uint8_t> mask(static_cast<size_t>(sz * sz), 0);
    for (int y = 0; y < sz; ++y) {
        const double dy = static_cast<double>(y) + 0.5 - center;
        for (int x = 0; x < sz; ++x) {
            const double dx = static_cast<double>(x) + 0.5 - center;
            const double dist = std::sqrt(dx * dx + dy * dy);
            if (dist > maxDist) continue;
            double a = 1.0;
            if (dist > hardSpan) {
                a = raster::LargeBrushOptimizer::smoothHermite((maxDist - dist) * invSoftSpan);
            }
            mask[static_cast<size_t>(y * sz + x)] = static_cast<uint8_t>(std::clamp(a * 255.0, 0.0, 255.0));
        }
    }
    return mask;
}

} // namespace aladyn::engine::boundary::orchestrator
