#include "SmudgeEngine.hpp"
#include "../canvas/GridSnapshot.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/LargeBrushOptimizer.hpp"
#include "../raster/PixelPermission.hpp"
#include "../raster/StraightOver.hpp"
#include <cmath>
#include <algorithm>
#include <vector>

namespace aladyn::engine::engines {

// Amostra segura direta no TileGrid
static inline utils::ColorRGBA getTilePixel(const canvas::TileGrid& tileGrid, int globalX, int globalY) {
    if (globalX < 0 || globalX >= tileGrid.getWidth() || globalY < 0 || globalY >= tileGrid.getHeight()) {
        return {0, 0, 0, 0};
    }
    const int tx  = globalX / canvas::Tile::TILE_SIZE;
    const int ty  = globalY / canvas::Tile::TILE_SIZE;
    const int lpx = globalX % canvas::Tile::TILE_SIZE;
    const int lpy = globalY % canvas::Tile::TILE_SIZE;

    const canvas::Tile* t = const_cast<canvas::TileGrid&>(tileGrid).getTile(tx, ty);
    return t ? t->getBuffer().getPixel(lpx, lpy) : utils::ColorRGBA{0, 0, 0, 0};
}

// Amostragem Gaussiana ponderada otimizada da área do dab na CAMADA ATIVA
static utils::ColorRGBA sampleDabArea(
    double cx, double cy, double radius,
    const canvas::TileGrid& tileGrid
) {
    const int iR = static_cast<int>(std::ceil(radius));
    const int step = std::max(1, iR / 12); // Subamostragem inteligente em pincéis gigantes

    const int x0 = static_cast<int>(std::floor(cx)) - iR;
    const int y0 = static_cast<int>(std::floor(cy)) - iR;
    const int x1 = static_cast<int>(std::ceil(cx))  + iR;
    const int y1 = static_cast<int>(std::ceil(cy))  + iR;

    double sumR = 0.0, sumG = 0.0, sumB = 0.0, sumA = 0.0;
    double totalWeight    = 0.0;
    double alphaWeightSum = 0.0;
    const double sigma    = std::max(1.0, radius * 0.45);
    const double sigmaFactor = 1.0 / (2.0 * sigma * sigma);

    for (int sy = y0; sy <= y1; sy += step) {
        const double dy = static_cast<double>(sy) + 0.5 - cy;
        for (int sx = x0; sx <= x1; sx += step) {
            const double dx   = static_cast<double>(sx) + 0.5 - cx;
            const double distSq = dx * dx + dy * dy;
            if (distSq > (radius + 1.0) * (radius + 1.0)) continue;

            const double w = std::exp(-distSq * sigmaFactor);
            const utils::ColorRGBA s = getTilePixel(tileGrid, sx, sy);

            if (s.a > 0) {
                const double aNorm = static_cast<double>(s.a) / 255.0;
                sumR += s.r * aNorm * w;
                sumG += s.g * aNorm * w;
                sumB += s.b * aNorm * w;
                alphaWeightSum += aNorm * w;
            }
            sumA += s.a * w;
            totalWeight += w;
        }
    }

    if (alphaWeightSum <= 0.0) return {0, 0, 0, 0};

    return utils::ColorRGBA{
        static_cast<uint8_t>(std::clamp(sumR / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(sumG / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(sumB / alphaWeightSum, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(sumA / totalWeight, 0.0, 255.0))
    };
}

namespace {

uint8_t mixChannel(uint8_t kept, uint8_t incoming, double rate) {
    return static_cast<uint8_t>(kept * (1.0 - rate) + incoming * rate);
}

utils::ColorRGBA mixColors(utils::ColorRGBA kept, utils::ColorRGBA incoming, double rate) {
    return utils::ColorRGBA{
        mixChannel(kept.r, incoming.r, rate), mixChannel(kept.g, incoming.g, rate),
        mixChannel(kept.b, incoming.b, rate), mixChannel(kept.a, incoming.a, rate)};
}

// O rastro direcional: a cor que o pincel carrega, puxada para o que estava atrás do dab. Lê de
// uma foto da camada tirada antes de o dab pintar (D15), para o resultado não depender da ordem
// em que os pixels são visitados.
struct SmearTrail {
    bool active;
    double offsetX;
    double offsetY;
    double mix;
    const canvas::GridSnapshot* source;

    utils::ColorRGBA colorAt(utils::ColorRGBA carried, int globalX, int globalY) const {
        if (!active) return carried;
        const int sampleX = static_cast<int>(std::round(static_cast<double>(globalX) + offsetX));
        const int sampleY = static_cast<int>(std::round(static_cast<double>(globalY) + offsetY));
        const utils::ColorRGBA behind = source->at(sampleX, sampleY);
        return behind.a > 0 ? mixColors(carried, behind, mix) : carried;
    }
};

} // namespace

void SmudgeEngine::carryColor(const utils::ColorRGBA& sampled, double pickup, double stretch) noexcept {
    if (!m_hasCarriedColor) {
        m_carriedColor = sampled;
        m_hasCarriedColor = true;
        return;
    }
    if (sampled.a == 0) {
        const double decay = 0.92 + stretch * 0.07;
        m_carriedColor.a = static_cast<uint8_t>(std::clamp(static_cast<double>(m_carriedColor.a) * decay, 0.0, 255.0));
    } else if (m_carriedColor.a == 0) {
        m_carriedColor = sampled;
    } else {
        m_carriedColor = mixColors(m_carriedColor, sampled, pickup * (1.0 - stretch * 0.6) * 0.4);
    }
}

void SmudgeEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r       = dab.radius;
    const double pickup  = std::clamp(profile.smudgeParams.colorPickup, 0.0, 1.0);
    const double mixRate = std::clamp(profile.smudgeParams.mixRatio, 0.0, 1.0);
    const double stretch = std::clamp(profile.smudgeParams.smudgeStretch, 0.0, 1.0);

    // Lógica de coleta e arrasto: a cor sob o primeiro dab do traço, misturada à do caminho
    const bool firstDab = !m_hasCarriedColor;
    carryColor(sampleDabArea(dab.position.x, dab.position.y, r, tileGrid), pickup, stretch);
    if (firstDab) m_lastPosition = dab.position;
    if (m_carriedColor.a == 0) {
        m_lastPosition = dab.position;
        return;
    }

    const double moveDX   = dab.position.x - m_lastPosition.x;
    const double moveDY   = dab.position.y - m_lastPosition.y;
    const double moveDist = std::sqrt(moveDX * moveDX + moveDY * moveDY);
    const bool moving = moveDist > 0.01;
    const double smearOffsetX = moving ? (-moveDX / moveDist * r * stretch * 0.5) : 0.0;
    const double smearOffsetY = moving ? (-moveDY / moveDist * r * stretch * 0.5) : 0.0;
    m_lastPosition = dab.position;

    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const raster::DabFootprint footprint(dab, r, aspect, tileGrid);
    if (footprint.empty()) return;

    // O rastro lê o que estava sob o dab ANTES de ele pintar. Lendo a grade viva, o pixel já escrito
    // entra na amostra do vizinho e o resultado passa a depender de por onde os tiles e as linhas
    // são varridos (achado D15, 2026-10-01).
    const bool smearsTrail = moveDist > 0.5 && stretch > 0.05;
    if (smearsTrail) {
        const utils::Rect2D& box = footprint.bounds();
        const int reach = static_cast<int>(std::ceil(std::max(std::abs(smearOffsetX), std::abs(smearOffsetY)))) + 1;
        m_trailSource.capture(
            tileGrid,
            static_cast<int>(std::floor(box.getLeft())) - reach,
            static_cast<int>(std::floor(box.getTop())) - reach,
            static_cast<int>(std::ceil(box.getRight())) + reach,
            static_cast<int>(std::ceil(box.getBottom())) + reach);
    }
    const SmearTrail trail{smearsTrail, smearOffsetX, smearOffsetY, stretch * 0.4, &m_trailSource};

    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
    const double spanInv  = 1.0 / std::max(0.001, r - hardSpan);
    const raster::PixelPermission permission(ctx);
    footprint.forEachPixel(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
        const double dist = std::sqrt(pixel.distSq);
        const double shape = dist > hardSpan ? raster::LargeBrushOptimizer::smoothHermite((r - dist) * spanInv) : 1.0;

        double deposit = dab.opacity * shape * mixRate;
        if (deposit <= 0.0 || !permission.apply(pixel.gx, pixel.gy, deposit) || deposit <= 0.0) return false;

        const utils::ColorRGBA source = trail.colorAt(m_carriedColor, pixel.gx, pixel.gy);
        return raster::straightOver(dst, source, (static_cast<double>(source.a) / 255.0) * deposit, ctx.alphaLocked);
    });
}

} // namespace aladyn::engine::engines
