#ifndef ALADYN_ENGINE_OIL_IMPASTO_ENGINE_HPP
#define ALADYN_ENGINE_OIL_IMPASTO_ENGINE_HPP

#include "IBrushEngine.hpp"
#include "OilBristles.hpp"
#include "../raster/StrokeInkLedger.hpp"

namespace aladyn::engine::document { class Layer; }

namespace aladyn::engine::engines {

// ─── MINI-MOTOR DE ÓLEO 3D & IMPASTO (OilImpastoEngine) ───────────────────
//
// Física: um feixe de cerdas que carrega tinta. Cada cerda lembra a cor e a carga que leva; a carga esgota
//         com a distância, a cerda pega cor do que pisa e deixa riscos paralelos ao movimento. A pincelada
//         ganha relevo (cristas entre as cerdas, pilha de tinta nas bordas) iluminado por uma luz fixa.
//
// Parâmetros exclusivos usados:
//   profile.oilParams.impastoDepth       (volume do relevo: cristas e sombreado 0-1)
//   profile.oilParams.bristleGrooves     (quanto as cerdas diferem entre si: riscos e ranhuras 0-1)
//   profile.oilParams.viscosity          (tinta grossa: cobre mais, resiste a se misturar 0-1)
//   profile.oilParams.specularBrilliance (brilho úmido das cristas 0-1)
//   profile.oilParams.wetMixFactor       (quanto a cerda pega da tinta que já está na tela 0-1)
//   profile.oilParams.paintDepletion     (quão depressa a carga das cerdas acaba ao longo do traço 0-1)
//
// O motor guarda estado de um traço (cerdas, direção, relevo já aplicado a cada pixel); começar, terminar
// ou trocar de motor zera tudo. Com simetria ou espalhamento cada carimbo vem de um lugar diferente e o
// movimento deixa de significar um traço: as cerdas continuam, mas sem direção estável.
// ───────────────────────────────────────────────────────────────────────────
class OilImpastoEngine final : public IBrushEngine {
public:
    OilImpastoEngine() = default;

    void renderDab(
        const utils::Dab& dab,
        const brush::BrushProfile& profile,
        const canvas::CanvasTexture& canvasTexture,
        canvas::TileGrid& tileGrid,
        const raster::PixelContext& ctx = {}
    ) override;

    [[nodiscard]] brush::EngineType getType() const noexcept override {
        return brush::EngineType::OilImpasto;
    }

    void onActivate(const brush::BrushProfile& /*profile*/) noexcept override { resetStroke(); }
    void onBeginStroke() noexcept override { resetStroke(); }
    void onEndStroke() noexcept override { resetStroke(); }

private:
    void resetStroke() noexcept;
    void follow(const utils::Dab& dab, double diameter) noexcept;
    void advanceBristles(const utils::Dab& dab, const brush::OilParams& oil, double diameter, canvas::TileGrid& grid,
                         const utils::Rect2D& area);
    [[nodiscard]] PremultColor beforeStroke(canvas::TileGrid& grid, double x, double y, const utils::Rect2D& area);

    BristleBundle m_bristles;
    raster::StrokeInkLedger<utils::ColorRGBA> m_ledger;
    raster::StrokeInkLedger<utils::ColorRGBA16> m_ledger16;
    utils::Point2D m_lastPosition{0.0, 0.0};
    double m_moved{0.0};      // quanto o pincel andou desde o carimbo anterior, em px
    double m_travel{0.0};     // quanto andou no traço, em diâmetros
    double m_dirX{1.0}, m_dirY{0.0};  // direção do traço: as ranhuras correm ao longo dela
    bool m_started{false};
    bool m_hasDirection{false};
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_OIL_IMPASTO_ENGINE_HPP
