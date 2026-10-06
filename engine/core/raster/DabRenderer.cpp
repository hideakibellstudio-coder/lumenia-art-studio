#include "DabRenderer.hpp"
#include "BrushGrain.hpp"
#include "DabFootprint.hpp"
#include "PixelPermission.hpp"
#include "TipShape.hpp"
#include "../../utils/MathUtils.hpp"
#include "../color/LinearColorSpace.hpp"
#include "../color/LinearColorSpace16.hpp"
#include <algorithm>
#include <cmath>

namespace aladyn::engine::raster {

namespace {

constexpr double kInkFeather = 0.15;

// Achatamento elíptico (Aspect Ratio) com modulação de caneta/dab e perfil.
double dabAspect(const utils::Dab& dab, const brush::BrushProfile& profile) {
    double aspect = std::clamp(dab.aspectRatio, 0.05, 1.0);
    if (profile.pressureToAspect > 0.0 && dab.aspectRatio >= 0.999) {
        aspect = std::clamp(profile.tip.aspectRatio - (dab.pressure * profile.pressureToAspect), 0.05, 1.0);
    }
    return std::max(0.05, aspect);
}

// Quanta tinta o dab deposita num pixel: constante quando nenhuma textura está ligada (caminho
// rápido) e, com textura, o contato entre o relevo do pincel (móvel no dab) e o do papel (fixo no
// canvas) contra a pressão.
class DabInk {
public:
    DabInk(const utils::Dab& dab, const brush::BrushProfile& profile, const canvas::CanvasTexture& paper)
        : m_paper(paper),
          m_grain(profile),
          m_paperTexture(paper.canvasHeightTexture.get()),
          m_safeRadius(std::max(0.001, dab.radius)),
          m_invTwoSafeRadius(0.5 / m_safeRadius),
          m_baseAlpha((static_cast<double>(dab.color.a) / 255.0) * dab.opacity),
          m_threshold(1.0 - dab.pressure),
          m_paperScale(0.002 * paper.canvasGrainScale) {
        m_brushGrain = m_grain.enabled();
        m_paperGrain = paper.canvasGrainEnabled && m_paperTexture;
        m_textured = m_brushGrain || m_paperGrain;
        // Sem textura o depósito é analítico e igual em todo o dab.
        const double flatInk = m_textured ? 1.0 : utils::MathUtils::smoothstep(m_threshold - kInkFeather, m_threshold + kInkFeather, 1.0);
        m_flatAlpha = m_baseAlpha * flatInk;
        m_nothingToDeposit = m_textured ? (m_flatAlpha <= 0.0) : (flatInk <= 0.0 || m_flatAlpha <= 0.0);
        // O LUT do papel se monta na primeira leitura; montá-lo aqui evita que várias threads o façam juntas.
        if (m_paperGrain) static_cast<void>(paper.sampleLUT(0));
    }

    [[nodiscard]] bool nothingToDeposit() const noexcept { return m_nothingToDeposit; }

    // O alfa do depósito num pixel cuja ponta dá `shape`.
    [[nodiscard]] double alphaAt(const DabPixel& pixel, double shape) const {
        if (!m_textured) return m_flatAlpha * shape;
        const double combined = brushHeight(pixel) * paperHeight(pixel);
        return m_baseAlpha * shape * utils::MathUtils::smoothstep(m_threshold - kInkFeather, m_threshold + kInkFeather, combined);
    }

private:
    double brushHeight(const DabPixel& pixel) const {
        if (!m_brushGrain) return 1.0;
        const double u = (pixel.rotX + m_safeRadius) * m_invTwoSafeRadius;
        const double v = (pixel.scaledY + m_safeRadius) * m_invTwoSafeRadius;
        return m_grain.height(pixel, u, v);
    }

    double paperHeight(const DabPixel& pixel) const {
        if (!m_paperGrain) return 1.0;
        const double u = (static_cast<double>(pixel.gx) + 0.5) * m_paperScale;
        const double v = (static_cast<double>(pixel.gy) + 0.5) * m_paperScale;
        return m_paper.sampleLUT(m_paperTexture->sampleNormalizedFastByte(u, v));
    }

    const canvas::CanvasTexture& m_paper;
    BrushGrain m_grain;
    const texture::Texture2D* m_paperTexture;
    double m_safeRadius;
    double m_invTwoSafeRadius;
    double m_baseAlpha;
    double m_threshold;
    double m_paperScale;
    double m_flatAlpha{0.0};
    bool m_brushGrain{false};
    bool m_paperGrain{false};
    bool m_textured{false};
    bool m_nothingToDeposit{false};
};

uint8_t toByte(double unit) {
    return utils::MathUtils::unitToByte(unit);
}

uint16_t toWord(double unit) {
    return static_cast<uint16_t>(std::clamp(std::lround(unit * 65535.0), 0L, 65535L));
}

bool depositNormal(utils::ColorRGBA& dst, utils::ColorRGBA color, double alpha) {
    if (dst.a == 0) {
        dst = utils::ColorRGBA{color.r, color.g, color.b, toByte(alpha)};
    } else if (dst.a == 255) {
        dst = color::blendLinearNormalOpaque(color, static_cast<float>(alpha), dst);
    } else {
        dst = color::blendLinearNormal(color, static_cast<float>(alpha), dst);
    }
    return true;
}

bool depositNormal16(utils::ColorRGBA16& dst, utils::ColorRGBA16 color, double alpha) {
    if (dst.a == 0) {
        dst = utils::ColorRGBA16{color.r, color.g, color.b, toWord(alpha)};
    } else if (dst.a == 65535) {
        dst = color::blendLinearNormalOpaque16(color, static_cast<float>(alpha), dst);
    } else {
        dst = color::blendLinearNormal16(color, static_cast<float>(alpha), dst);
    }
    return true;
}

// Modo Canetinha / Marker: escurece o destino pela cor do dab, sem mexer no alfa.
bool depositMultiply(utils::ColorRGBA& dst, utils::ColorRGBA color, double alpha) {
    const auto channel = [alpha](uint8_t src, uint8_t under) {
        const double s = static_cast<double>(src) / 255.0;
        const double d = static_cast<double>(under) / 255.0;
        return utils::MathUtils::unitToByte(d * (1.0 - alpha * (1.0 - s)));
    };
    dst = utils::ColorRGBA{channel(color.r, dst.r), channel(color.g, dst.g), channel(color.b, dst.b), dst.a};
    return true;
}

bool depositMultiply16(utils::ColorRGBA16& dst, utils::ColorRGBA16 color, double alpha) {
    const auto channel = [alpha](uint16_t src, uint16_t under) {
        const double s = static_cast<double>(src) / 65535.0;
        const double d = static_cast<double>(under) / 65535.0;
        return toWord(d * (1.0 - alpha * (1.0 - s)));
    };
    dst = utils::ColorRGBA16{channel(color.r, dst.r), channel(color.g, dst.g), channel(color.b, dst.b), dst.a};
    return true;
}

// Modo Luz / Glow: soma a cor do dab ao destino e o deixa opaco.
bool depositAdditive(utils::ColorRGBA& dst, utils::ColorRGBA color, double alpha) {
    const auto channel = [alpha](uint8_t src, uint8_t under) {
        return utils::MathUtils::roundToByte(static_cast<double>(under) + static_cast<double>(src) * alpha);
    };
    dst = utils::ColorRGBA{channel(color.r, dst.r), channel(color.g, dst.g), channel(color.b, dst.b), 255};
    return true;
}

bool depositAdditive16(utils::ColorRGBA16& dst, utils::ColorRGBA16 color, double alpha) {
    const auto channel = [alpha](uint16_t src, uint16_t under) {
        return static_cast<uint16_t>(std::clamp(std::lround(static_cast<double>(under) + static_cast<double>(src) * alpha), 0L, 65535L));
    };
    dst = utils::ColorRGBA16{channel(color.r, dst.r), channel(color.g, dst.g), channel(color.b, dst.b), 65535};
    return true;
}

bool deposit(utils::ColorRGBA& dst, const utils::Dab& dab, double alpha, bool alphaLocked) {
    if (alphaLocked) {
        if (dst.a == 0) return false;
        const uint8_t originalAlpha = dst.a;
        dst = color::blendLinearNormal(dab.color, static_cast<float>(alpha), dst);
        dst.a = originalAlpha;
        return true;
    }
    switch (dab.blendMode) {
        case utils::DabBlendMode::Normal:   return depositNormal(dst, dab.color, alpha);
        case utils::DabBlendMode::Multiply: return depositMultiply(dst, dab.color, alpha);
        case utils::DabBlendMode::Additive: return depositAdditive(dst, dab.color, alpha);
        case utils::DabBlendMode::Erase:    return false;  // a borracha pinta sozinha (EraserEngine)
    }
    return false;
}

bool deposit16(utils::ColorRGBA16& dst, const utils::Dab& dab, utils::ColorRGBA16 dabColor16, double alpha, bool alphaLocked) {
    if (alphaLocked) {
        if (dst.a == 0) return false;
        const uint16_t originalAlpha = dst.a;
        dst = color::blendLinearNormal16(dabColor16, static_cast<float>(alpha), dst);
        dst.a = originalAlpha;
        return true;
    }
    switch (dab.blendMode) {
        case utils::DabBlendMode::Normal:   return depositNormal16(dst, dabColor16, alpha);
        case utils::DabBlendMode::Multiply: return depositMultiply16(dst, dabColor16, alpha);
        case utils::DabBlendMode::Additive: return depositAdditive16(dst, dabColor16, alpha);
        case utils::DabBlendMode::Erase:    return false;
    }
    return false;
}

} // namespace

void DabRenderer::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& canvasTexture,
    canvas::TileGrid& tileGrid,
    const PixelContext& ctx
) {
    if (dab.radius <= 0.5 || dab.color.a == 0 || dab.opacity < 0.005) return;

    const DabFootprint footprint(dab, dab.radius, dabAspect(dab, profile), tileGrid);
    if (footprint.empty()) return;

    const DabInk ink(dab, profile, canvasTexture);
    if (ink.nothingToDeposit()) return;

    const TipShape tip(profile, dab.radius);
    const PixelPermission permission(ctx);
    if (tileGrid.getFormat() == canvas::PixelFormat::RGBA16) {
        const utils::ColorRGBA16 color16 = canvas::widen(dab.color);
        footprint.forEachPixel<utils::ColorRGBA16>(4, [&](utils::ColorRGBA16& dst, const DabPixel& pixel) {
            const double shape = tip.alphaAt(pixel);
            if (shape <= 0.0) return false;

            double alpha = ink.alphaAt(pixel, shape);
            if (alpha <= 0.0 || !permission.apply(pixel.gx, pixel.gy, alpha) || alpha <= 0.0) return false;
            return deposit16(dst, dab, color16, alpha, ctx.alphaLocked);
        });
    } else {
        footprint.forEachPixel<utils::ColorRGBA>(4, [&](utils::ColorRGBA& dst, const DabPixel& pixel) {
            const double shape = tip.alphaAt(pixel);
            if (shape <= 0.0) return false;

            double alpha = ink.alphaAt(pixel, shape);
            if (alpha <= 0.0 || !permission.apply(pixel.gx, pixel.gy, alpha) || alpha <= 0.0) return false;
            return deposit(dst, dab, alpha, ctx.alphaLocked);
        });
    }
}

} // namespace aladyn::engine::raster
