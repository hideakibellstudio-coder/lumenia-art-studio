#ifndef ALADYN_ENGINE_OIL_SURFACE_HPP
#define ALADYN_ENGINE_OIL_SURFACE_HPP

#include "OilBristles.hpp"
#include "IBrushEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include <algorithm>
#include <array>
#include <cmath>

namespace aladyn::engine::engines {

// ─── O QUE UM PIXEL DO CARIMBO DE ÓLEO VÊ ───────────────────────────────────────
//
// A parte só-leitura do motor de óleo: os seis controles limitados, a curva que reescala a cobertura ao
// espaçamento e a superfície (forma do pincel + feixe de cerdas + direção) que diz, para cada pixel, que tinta
// há ali e qual o declive do relevo. Quem a atualiza entre carimbos é o motor (OilImpastoEngine.cpp).
namespace oil_surface {

// A pilha de tinta que o pincel empurra para as bordas do traço: posição e largura (frações do raio), altura.
constexpr double kEdgeCenter = 0.8;
constexpr double kEdgeWidth = 0.12;
constexpr double kEdgeHeight = 1.4;

inline double unit(double value) { return std::clamp(value, 0.0, 1.0); }

// Os seis controles do óleo, já limitados.
struct OilSettings {
    explicit OilSettings(const brush::OilParams& p)
        : impasto(unit(p.impastoDepth)), grooves(unit(p.bristleGrooves)), viscosity(unit(p.viscosity)),
          specular(unit(p.specularBrilliance)), wet(unit(p.wetMixFactor)), depletion(unit(p.paintDepletion)) {}

    double impasto, grooves, viscosity, specular, wet, depletion;
};

// A cobertura de um carimbo reescalada ao espaçamento de referência: 1 - (1 - w)^densidade, com a densidade
// igual ao espaçamento real sobre o de referência (carimbos mais juntos cobrem menos cada um). Tabelada para
// não calcular uma potência por pixel.
class DensityCurve {
public:
    explicit DensityCurve(double density) : m_identity(std::abs(density - 1.0) < 1e-3) {
        if (m_identity) return;
        for (std::size_t i = 0; i < m_table.size(); ++i) {
            const double w = static_cast<double>(i) / static_cast<double>(kSteps);
            m_table[i] = static_cast<float>(1.0 - std::pow(1.0 - w, density));
        }
    }

    [[nodiscard]] double operator()(double weight) const {
        if (m_identity) return weight;
        const double scaled = std::clamp(weight, 0.0, 1.0) * kSteps;
        const std::size_t lo = std::min(static_cast<std::size_t>(scaled), kSteps - 1);
        const double t = scaled - static_cast<double>(lo);
        return m_table[lo] + (m_table[lo + 1] - m_table[lo]) * t;
    }

private:
    static constexpr std::size_t kSteps = 256;
    std::array<float, kSteps + 1> m_table{};
    bool m_identity;
};

// O que um pixel do carimbo vê: o pincel (forma), o feixe (tinta e altura das cerdas) e a direção do traço.
class OilSurface {
public:
    struct Sample {
        PremultColor paint;     // a tinta da cerda neste ponto; o alfa é a carga
        double weight{0.0};     // quanto deste carimbo cobre o pixel, antes da seleção
        float ceiling{1.0f};    // o máximo que o traço cobre este pixel: as cerdas baixas deixam o papel aparecer
        float slopeX{0.0f};     // o declive do relevo neste ponto
        float slopeY{0.0f};
    };

    OilSurface(const utils::Dab& dab, const brush::BrushProfile& profile, const OilSettings& oil,
               const BristleBundle& bristles, double dirX, double dirY, double density)
        : m_oil(oil), m_bristles(bristles), m_density(density), m_centerX(dab.position.x), m_centerY(dab.position.y),
          m_dirX(dirX), m_dirY(dirY), m_radius(std::max(0.001, dab.radius)),
          m_hardSpan(std::clamp(profile.hardness, 0.0, 0.99) * m_radius),
          m_opacity(dab.opacity * (0.6 + oil.viscosity * 0.4)),
          m_slopeScale(static_cast<float>(0.3 + 0.7 * oil.impasto)) {}

    [[nodiscard]] const DensityCurve& density() const noexcept { return m_density; }

    // false: o pixel está fora do pincel.
    bool sampleAt(const raster::DabPixel& pixel, Sample& out) const {
        const double dist = std::sqrt(pixel.distSq);
        double shape = 1.0;
        if (dist > m_hardSpan) shape = std::clamp((m_radius - dist) / std::max(0.001, m_radius - m_hardSpan), 0.0, 1.0);
        if (shape <= 0.0) return false;

        // `across` mede o pixel perpendicularmente ao traço: -1 numa borda do pincel, +1 na outra.
        const double across = (-(pixel.gx + 0.5 - m_centerX) * m_dirY + (pixel.gy + 0.5 - m_centerY) * m_dirX) / m_radius;
        const BristleBundle::Place place = m_bristles.place(across);
        const Bristle& first = m_bristles.at(place.lo);
        const Bristle& second = m_bristles.at(place.hi);
        const float f = place.frac;
        const float blend = f * f * (3.0f - 2.0f * f);
        out.paint = first.paint.towards(second.paint, f);

        const double height = first.height + (second.height - first.height) * blend;
        out.weight = m_opacity * shape;
        out.ceiling = static_cast<float>(1.0 - m_oil.grooves * 0.8 * (1.0 - height) * (1.0 - height));

        const double load = std::clamp(static_cast<double>(out.paint.a), 0.0, 1.0);
        const double slope = relief(across, (second.height - first.height) * 6.0f * f * (1.0f - f)) * load
                           * (0.5 + 0.5 * m_oil.viscosity) * m_slopeScale;
        out.slopeX = static_cast<float>(-slope * m_dirY);
        out.slopeY = static_cast<float>(slope * m_dirX);
        return true;
    }

private:
    // O declive através do traço, em alturas de cerda por cerda: a diferença entre as cerdas vizinhas mais a
    // pilha de tinta das bordas (derivada da gaussiana em `across`).
    double relief(double across, double bristleSlope) const {
        const double e = (std::abs(across) - kEdgeCenter) / kEdgeWidth;
        const double pile = kEdgeHeight * std::exp(-e * e);
        const double pileSlope = -2.0 * e / kEdgeWidth * pile * (across < 0.0 ? -1.0 : 1.0);
        return m_oil.grooves * bristleSlope * 1.5 + pileSlope * 2.0 / m_bristles.count();
    }

    OilSettings m_oil;
    const BristleBundle& m_bristles;
    DensityCurve m_density;
    double m_centerX, m_centerY, m_dirX, m_dirY, m_radius, m_hardSpan, m_opacity;
    float m_slopeScale;
};

} // namespace oil_surface

using oil_surface::DensityCurve;
using oil_surface::OilSettings;
using oil_surface::OilSurface;

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_OIL_SURFACE_HPP
