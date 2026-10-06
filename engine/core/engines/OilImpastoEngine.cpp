#include "OilImpastoEngine.hpp"
#include "OilLight.hpp"
#include "OilSurface.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/PixelPermission.hpp"
#include "../../utils/MathUtils.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

constexpr double kPi = 3.14159265358979323846;

// Os ritmos do feixe, por diâmetro do pincel percorrido (não por carimbo: o espaçamento não muda o traço).
constexpr double kDepletionRate = 0.7;  // com depleção 1, a carga média cai a 1/e em ~1,4 diâmetros
constexpr double kFeedRate = 2.5;       // a reserva repõe a carga da cerda
constexpr double kPickupRate = 3.2;     // a cerda pega a tinta da tela, com mistura 1

// O espaçamento em que o fluxo vale "por carimbo" (0,06 do diâmetro, o do Pincel de Cerda Pesada). Com outro
// espaçamento a cobertura de cada carimbo é reescalada: o quanto o traço cobre, e onde a tinta acaba, não mudam
// só porque o artista afastou ou aproximou os carimbos.
constexpr double kReferenceSpacing = 0.06;

// Cerdas lado a lado: de 18 num pincel de 24 px a 64 num pincel grande; a cerda fica mais larga com o pincel.
int bristleCount(double brushSize) {
    const double pitch = std::clamp(brushSize / 22.0, 1.3, 6.0);
    return std::clamp(static_cast<int>(std::lround(brushSize / pitch)), 10, 64);
}

// As cerdas de um traço dependem de onde ele começa: a pré-visualização e o traço final têm as mesmas.
uint32_t strokeSeed(const utils::Point2D& start) {
    return static_cast<uint32_t>(static_cast<int>(std::floor(start.x))) * 73856093u
         ^ static_cast<uint32_t>(static_cast<int>(std::floor(start.y))) * 19349663u;
}

PremultColor scaled(const PremultColor& color, float factor) {
    return {color.r * factor, color.g * factor, color.b * factor, color.a * factor};
}

// Compõe a tinta da cerda sobre um pixel e acende o relevo. A luz que o pixel já tinha é tirada antes e a nova
// posta depois, então o brilho de um pixel não depende de quantos carimbos passaram por ele.
bool paintPixel(utils::ColorRGBA& dst, raster::StrokeInkLedger<utils::ColorRGBA>::Cell& cell, const OilSurface::Sample& sample,
                float weight, bool alphaLocked, const OilSettings& oil, const DensityCurve& density) {
    // Cada carimbo cobre mais um pouco, até o teto da cerda: os riscos de uma cerda baixa não se apagam por mais
    // carimbos que passem.
    const float room = cell.coverage < sample.ceiling ? (sample.ceiling - cell.coverage) / (1.0f - cell.coverage) : 0.0f;
    const float deposit = static_cast<float>(density(static_cast<double>(weight * room * sample.paint.a)));
    if (!(deposit > 0.0f) || !(sample.paint.a > 0.0f)) return false;
    const float cover = deposit / sample.paint.a;  // a carga já está em `deposit`; a cor da cerda entra inteira
    if (cell.coverage <= 0.0f) cell.base = dst;  // o pixel como estava antes do traço: é dele que as cerdas pegam cor
    const float coverage = cell.coverage + deposit * (1.0f - cell.coverage);
    const float relief = std::min(1.0f, coverage * 1.5f);  // a tinta só mostra relevo onde cobre
    const float lambda = oil_light::shade(sample.slopeX * relief, sample.slopeY * relief,
                                          static_cast<float>(oil.impasto), static_cast<float>(oil.specular));

    const float alpha = static_cast<float>(dst.a) / 255.0f;
    const auto bare = [&](uint8_t channel) { return oil_light::unlit(static_cast<float>(channel) / 255.0f, cell.shade) * alpha; };
    const float keep = 1.0f - deposit;
    const float outA = deposit + keep * alpha;
    if (!(outA > 0.0f)) return false;

    const auto mixed = [&](float paint, float under) {
        const float straight = std::clamp((cover * paint + keep * under) / outA, 0.0f, 1.0f);
        return utils::MathUtils::roundToByte(static_cast<double>(std::clamp(oil_light::lit(straight, lambda), 0.0f, 1.0f)) * 255.0);
    };
    const utils::ColorRGBA next{
        mixed(sample.paint.r, bare(dst.r)), mixed(sample.paint.g, bare(dst.g)), mixed(sample.paint.b, bare(dst.b)),
        alphaLocked ? dst.a : utils::MathUtils::unitToByte(outA)
    };
    cell.coverage = coverage;
    cell.shade = lambda;
    if (next.r == dst.r && next.g == dst.g && next.b == dst.b && next.a == dst.a) return false;
    dst = next;
    return true;
}

bool paintPixel16(utils::ColorRGBA16& dst, raster::StrokeInkLedger<utils::ColorRGBA16>::Cell& cell, const OilSurface::Sample& sample,
                  float weight, bool alphaLocked, const OilSettings& oil, const DensityCurve& density) {
    const float room = cell.coverage < sample.ceiling ? (sample.ceiling - cell.coverage) / (1.0f - cell.coverage) : 0.0f;
    const float deposit = static_cast<float>(density(static_cast<double>(weight * room * sample.paint.a)));
    if (!(deposit > 0.0f) || !(sample.paint.a > 0.0f)) return false;
    const float cover = deposit / sample.paint.a;
    if (cell.coverage <= 0.0f) cell.base = dst;
    const float coverage = cell.coverage + deposit * (1.0f - cell.coverage);
    const float relief = std::min(1.0f, coverage * 1.5f);
    const float lambda = oil_light::shade(sample.slopeX * relief, sample.slopeY * relief,
                                          static_cast<float>(oil.impasto), static_cast<float>(oil.specular));

    const float alpha = static_cast<float>(dst.a) / 65535.0f;
    const auto bare = [&](uint16_t channel) { return oil_light::unlit(static_cast<float>(channel) / 65535.0f, cell.shade) * alpha; };
    const float keep = 1.0f - deposit;
    const float outA = deposit + keep * alpha;
    if (!(outA > 0.0f)) return false;

    const auto mixed = [&](float paint, float under) {
        const float straight = std::clamp((cover * paint + keep * under) / outA, 0.0f, 1.0f);
        return static_cast<uint16_t>(std::clamp(std::lround(static_cast<double>(std::clamp(oil_light::lit(straight, lambda), 0.0f, 1.0f)) * 65535.0), 0L, 65535L));
    };
    const uint16_t outAlpha = alphaLocked ? dst.a : static_cast<uint16_t>(std::clamp(std::lround(static_cast<double>(outA) * 65535.0), 0L, 65535L));
    const utils::ColorRGBA16 next{
        mixed(sample.paint.r, bare(dst.r)), mixed(sample.paint.g, bare(dst.g)), mixed(sample.paint.b, bare(dst.b)),
        outAlpha
    };
    cell.coverage = coverage;
    cell.shade = lambda;
    if (next.r == dst.r && next.g == dst.g && next.b == dst.b && next.a == dst.a) return false;
    dst = next;
    return true;
}

} // namespace

void OilImpastoEngine::resetStroke() noexcept {
    m_bristles.reset();
    m_ledger.clear();
    m_ledger16.clear();
    m_moved = 0.0;
    m_travel = 0.0;
    m_dirX = 1.0;
    m_dirY = 0.0;
    m_started = false;
    m_hasDirection = false;
}

// A direção do traço é a do movimento do pincel, suavizada ao longo de meio diâmetro. Num carimbo parado, ou
// no primeiro, vale o ângulo da ponta.
void OilImpastoEngine::follow(const utils::Dab& dab, double diameter) noexcept {
    if (!m_started) {
        const double angle = dab.angle * kPi / 180.0;
        m_dirX = std::cos(angle);
        m_dirY = std::sin(angle);
        m_moved = 0.0;
    } else {
        m_moved = std::hypot(dab.position.x - m_lastPosition.x, dab.position.y - m_lastPosition.y);
        if (m_moved > 0.2) {
            const double towardX = (dab.position.x - m_lastPosition.x) / m_moved;
            const double towardY = (dab.position.y - m_lastPosition.y) / m_moved;
            double x = towardX, y = towardY;
            if (m_hasDirection) {
                const double k = 1.0 - std::exp(-m_moved / (0.5 * diameter + 1.0));
                x = m_dirX + (towardX - m_dirX) * k;
                y = m_dirY + (towardY - m_dirY) * k;
            }
            const double length = std::hypot(x, y);
            m_dirX = length > 1e-6 ? x / length : towardX;
            m_dirY = length > 1e-6 ? y / length : towardY;
            m_hasDirection = true;
        }
    }
    m_lastPosition = dab.position;
    m_started = true;
}

// O pixel (x, y) como estava ANTES do traço: a cerda pega cor do que havia na tela, não da tinta que o próprio
// traço acabou de deixar ali (senão um traço de carimbos sobrepostos só encontraria a si mesmo e nunca
// misturaria nada). O ponto é limitado à área já preparada do livro-razão.
PremultColor OilImpastoEngine::beforeStroke(canvas::TileGrid& grid, double x, double y, const utils::Rect2D& area) {
    const int px = std::clamp(static_cast<int>(std::floor(std::clamp(x, area.getLeft(), std::max(area.getLeft(), area.getRight() - 0.01)))),
                              0, grid.getWidth() - 1);
    const int py = std::clamp(static_cast<int>(std::floor(std::clamp(y, area.getTop(), std::max(area.getTop(), area.getBottom() - 0.01)))),
                              0, grid.getHeight() - 1);
    constexpr int kSize = canvas::Tile::TILE_SIZE;
    if (grid.getFormat() == canvas::PixelFormat::RGBA16) {
        const raster::StrokeInkLedger<utils::ColorRGBA16>::Cell& cell = m_ledger16.at(px, py);
        if (cell.coverage > 0.0f) return PremultColor::from(cell.base);
        canvas::Tile* tile = grid.getTile(px / kSize, py / kSize);
        return tile ? PremultColor::from(tile->getBuffer().getPixel16(px % kSize, py % kSize)) : PremultColor{};
    } else {
        const raster::StrokeInkLedger<utils::ColorRGBA>::Cell& cell = m_ledger.at(px, py);
        if (cell.coverage > 0.0f) return PremultColor::from(cell.base);
        canvas::Tile* tile = grid.getTile(px / kSize, py / kSize);
        return tile ? PremultColor::from(tile->getBuffer().getPixel(px % kSize, py % kSize)) : PremultColor{};
    }
}

// Uma vez por carimbo, em série: cada cerda pega tinta da tela por onde passa, perde carga e é reposta pela
// reserva (que também se esgota). Sem mistura a cerda volta limpa a cada carimbo; com ela a cor fica no feixe.
void OilImpastoEngine::advanceBristles(const utils::Dab& dab, const brush::OilParams& params, double diameter,
                                       canvas::TileGrid& grid, const utils::Rect2D& area) {
    const OilSettings oil(params);
    const double steps = m_moved / diameter;
    m_travel += steps;
    m_bristles.sway(m_travel);
    const float pick = oil.wet > 0.0
        ? static_cast<float>(1.0 - std::exp(-steps * kPickupRate * oil.wet * (1.0 - 0.55 * oil.viscosity))) : 0.0f;
    const float feed = static_cast<float>(1.0 - std::exp(-steps * kFeedRate * (1.0 - 0.75 * oil.wet)));
    const PremultColor fresh = PremultColor::from(dab.color);

    const int count = m_bristles.count();
    for (int i = 0; i < count; ++i) {
        Bristle& bristle = m_bristles.at(i);
        const float reserve = static_cast<float>(std::exp(-kDepletionRate * oil.depletion * m_travel / bristle.capacity));
        const PremultColor supply = scaled(fresh, reserve);
        if (bristle.paint.a < 0.0f || !(oil.wet > 0.0)) {
            bristle.paint = supply;
            continue;
        }
        if (pick > 0.0f) {
            const double across = ((i + 0.5) / count * 2.0 - 1.0) * dab.radius;
            PremultColor under;
            for (const double along : {-0.35, 0.0, 0.35}) {
                const double reach = along * dab.radius;
                const PremultColor at = beforeStroke(grid, dab.position.x - m_dirY * across + m_dirX * reach,
                                                     dab.position.y + m_dirX * across + m_dirY * reach, area);
                under = {under.r + at.r / 3.0f, under.g + at.g / 3.0f, under.b + at.b / 3.0f, under.a + at.a / 3.0f};
            }
            bristle.paint = bristle.paint.towards(under, pick * under.a);
        }
        bristle.paint = bristle.paint.towards(supply, feed);
    }
}

void OilImpastoEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0 || dab.color.a == 0) return;

    const double aspect = raster::tipAspect(dab);
    const raster::DabFootprint footprint(dab, dab.radius, aspect, tileGrid);
    if (footprint.empty()) return;

    follow(dab, 2.0 * dab.radius);
    if (m_bristles.empty()) m_bristles.load(bristleCount(profile.brushSize), strokeSeed(dab.position));

    const OilSettings oil(profile.oilParams);
    const double spacing = m_moved / (2.0 * dab.radius);  // o espaçamento real deste carimbo, em diâmetros
    const double density = spacing > 0.0 ? std::clamp(spacing / kReferenceSpacing, 0.25, 4.0) : 1.0;
    const OilSurface surface(dab, profile, oil, m_bristles, m_dirX, m_dirY, density);
    const raster::PixelPermission permission(ctx);

    if (tileGrid.getFormat() == canvas::PixelFormat::RGBA16) {
        m_ledger16.prepare(footprint.bounds(), tileGrid);
        advanceBristles(dab, profile.oilParams, 2.0 * dab.radius, tileGrid, footprint.bounds());
        footprint.forEachPixel<utils::ColorRGBA16>(6, [&](utils::ColorRGBA16& dst, const raster::DabPixel& pixel) {
            OilSurface::Sample sample;
            if (!surface.sampleAt(pixel, sample)) return false;
            if (ctx.alphaLocked && dst.a == 0) return false;
            double weight = sample.weight;
            if (weight <= 0.0 || !permission.apply(pixel.gx, pixel.gy, weight) || weight <= 0.0) return false;
            return paintPixel16(dst, m_ledger16.at(pixel.gx, pixel.gy), sample, static_cast<float>(std::min(1.0, weight)),
                                ctx.alphaLocked, oil, surface.density());
        });
    } else {
        m_ledger.prepare(footprint.bounds(), tileGrid);
        advanceBristles(dab, profile.oilParams, 2.0 * dab.radius, tileGrid, footprint.bounds());
        footprint.forEachPixel<utils::ColorRGBA>(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
            OilSurface::Sample sample;
            if (!surface.sampleAt(pixel, sample)) return false;
            if (ctx.alphaLocked && dst.a == 0) return false;
            double weight = sample.weight;
            if (weight <= 0.0 || !permission.apply(pixel.gx, pixel.gy, weight) || weight <= 0.0) return false;
            return paintPixel(dst, m_ledger.at(pixel.gx, pixel.gy), sample, static_cast<float>(std::min(1.0, weight)),
                              ctx.alphaLocked, oil, surface.density());
        });
    }
}

} // namespace aladyn::engine::engines
