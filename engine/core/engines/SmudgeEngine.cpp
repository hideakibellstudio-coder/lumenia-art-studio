#include "SmudgeEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/LargeBrushOptimizer.hpp"
#include "../raster/PixelPermission.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::engines {

namespace {

// Quantos diâmetros do pincel o que ele carrega dura antes de se misturar de vez com o que ele pisa
// (comprimento de 1/e). O alongamento prolonga o arrasto; a coleta da tela o encurta um pouco. Os presets de
// fábrica caem em torno de 1,5 diâmetro: o ouro puxa o azul por uns três raios e a cor some aos poucos.
double carryDiameters(double pickup, double stretch) {
    return 0.4 + 2.2 * stretch * (1.1 - 0.5 * pickup);
}

// O espaçamento em que a força do pincel vale "por carimbo" (0,08 do diâmetro, o dos presets de fábrica):
// com outro espaçamento a força é reescalada, e o arrasto não muda de tamanho só porque o artista afastou
// ou aproximou os carimbos.
constexpr double kReferenceSpacing = 0.08;

// Quanto do carregado é trocado pelo que está sob o pincel depois de andar `moved` px: por distância e não
// por carimbo, para o comprimento do arrasto não mudar com o espaçamento nem com o tamanho.
double refillAfter(double moved, double diameter, double pickup, double stretch) {
    return 1.0 - std::exp(-moved / std::max(1e-6, carryDiameters(pickup, stretch) * diameter));
}

} // namespace

void SmudgeEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r        = dab.radius;
    const double pickup   = std::clamp(profile.smudgeParams.colorPickup, 0.0, 1.0);
    const double strength = std::clamp(profile.smudgeParams.mixRatio, 0.0, 1.0);
    const double stretch  = std::clamp(profile.smudgeParams.smudgeStretch, 0.0, 1.0);

    const double moved = m_hasStarted
        ? std::hypot(dab.position.x - m_lastPosition.x, dab.position.y - m_lastPosition.y)
        : 0.0;
    m_lastPosition = dab.position;
    m_hasStarted = true;
    const float refill = static_cast<float>(refillAfter(moved, 2.0 * r, pickup, stretch));
    const double referenceSteps = moved / (kReferenceSpacing * 2.0 * r);

    const double aspect = raster::tipAspect(dab);
    const raster::DabFootprint footprint(dab, r, aspect, tileGrid);
    if (footprint.empty()) return;

    m_patch.fit(r);
    const int anchorX = static_cast<int>(std::lround(dab.position.x));
    const int anchorY = static_cast<int>(std::lround(dab.position.y));
    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
    const double spanInv  = 1.0 / std::max(0.001, r - hardSpan);
    const raster::PixelPermission permission(ctx);

    // Cada pixel só olha para si e para a sua célula do pedaço carregado: o resultado não depende da ordem
    // em que os tiles e as linhas são visitados (D15), sem precisar de foto da grade.
    if (tileGrid.getFormat() == canvas::PixelFormat::RGBA16) {
        footprint.forEachPixel<utils::ColorRGBA16>(6, [&](utils::ColorRGBA16& dst, const raster::DabPixel& pixel) {
            const double dist = std::sqrt(pixel.distSq);
            const double shape = dist > hardSpan ? raster::LargeBrushOptimizer::smoothHermite((r - dist) * spanInv) : 1.0;
            if (shape <= 0.0) return false;

            const PremultColor under = PremultColor::from(dst);
            PremultColor& carried = m_patch.at(pixel.gx - anchorX, pixel.gy - anchorY);
            if (carried.a < 0.0f) carried = under;

            bool changed = false;
            double deposit = dab.opacity * shape * strength;
            if (deposit > 0.0 && deposit < 1.0) deposit = 1.0 - std::pow(1.0 - deposit, referenceSteps);
            if (deposit > 0.0 && permission.apply(pixel.gx, pixel.gy, deposit) && deposit > 0.0) {
                const PremultColor mixed = under.towards(carried, static_cast<float>(deposit));
                const utils::ColorRGBA16 out = ctx.alphaLocked ? mixed.toStraight16(dst.a) : mixed.toStraight16();
                if (ctx.alphaLocked && dst.a == 0) {
                    // Trava de alfa: pixel sem tinta continua sem tinta.
                } else if (out.r != dst.r || out.g != dst.g || out.b != dst.b || out.a != dst.a) {
                    dst = out;
                    changed = true;
                }
            }
            carried = carried.towards(under, refill * static_cast<float>(shape));
            return changed;
        });
    } else {
        footprint.forEachPixel<utils::ColorRGBA>(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
            const double dist = std::sqrt(pixel.distSq);
            const double shape = dist > hardSpan ? raster::LargeBrushOptimizer::smoothHermite((r - dist) * spanInv) : 1.0;
            if (shape <= 0.0) return false;

            const PremultColor under = PremultColor::from(dst);
            PremultColor& carried = m_patch.at(pixel.gx - anchorX, pixel.gy - anchorY);
            if (carried.a < 0.0f) carried = under;  // primeira vez do pincel neste pixel: pega o que há

            bool changed = false;
            double deposit = dab.opacity * shape * strength;
            if (deposit > 0.0 && deposit < 1.0) deposit = 1.0 - std::pow(1.0 - deposit, referenceSteps);
            if (deposit > 0.0 && permission.apply(pixel.gx, pixel.gy, deposit) && deposit > 0.0) {
                const PremultColor mixed = under.towards(carried, static_cast<float>(deposit));
                const utils::ColorRGBA out = ctx.alphaLocked ? mixed.toStraight(dst.a) : mixed.toStraight();
                if (ctx.alphaLocked && dst.a == 0) {
                    // Trava de alfa: pixel sem tinta continua sem tinta.
                } else if (out.r != dst.r || out.g != dst.g || out.b != dst.b || out.a != dst.a) {
                    dst = out;
                    changed = true;
                }
            }
            carried = carried.towards(under, refill * static_cast<float>(shape));  // o pincel se limpa pisando
            return changed;
        });
    }
}

} // namespace aladyn::engine::engines
