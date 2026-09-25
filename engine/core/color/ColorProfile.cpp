#include "ColorProfile.hpp"
#include <cmath>
#include <algorithm>

namespace aladyn::engine::color {

static inline double srgbToLinear(double c) noexcept {
    return (c <= 0.04045) ? (c / 12.92) : std::pow((c + 0.055) / 1.055, 2.4);
}

static inline double linearToSrgb(double c) noexcept {
    const double clamped = std::clamp(c, 0.0, 1.0);
    return (clamped <= 0.0031308) ? (clamped * 12.92) : (1.055 * std::pow(clamped, 1.0 / 2.4) - 0.055);
}

// Simulação espectral CMYK física com ganho de ponto e limite de tinta
static inline utils::ColorRGBA simulateCmyk(
    double r, double g, double b, uint8_t a,
    double dotGain, double inkLimit, double paperWhiteness, double blackDensity
) noexcept {
    // 1. Conversão RGB -> CMYK (GCR com ganho de ponto)
    double k = 1.0 - std::max({r, g, b});
    double c = (k < 0.999) ? (1.0 - r - k) / (1.0 - k) : 0.0;
    double m = (k < 0.999) ? (1.0 - g - k) / (1.0 - k) : 0.0;
    double y = (k < 0.999) ? (1.0 - b - k) / (1.0 - k) : 0.0;

    // Ganho de ponto (Dot Gain da chapa/tinta)
    c = std::clamp(c + c * (1.0 - c) * dotGain, 0.0, 1.0);
    m = std::clamp(m + m * (1.0 - m) * dotGain, 0.0, 1.0);
    y = std::clamp(y + y * (1.0 - y) * dotGain, 0.0, 1.0);
    k = std::clamp(k + k * (1.0 - k) * dotGain, 0.0, 1.0);

    // Total Ink Coverage (TAC Limit)
    double totalInk = c + m + y + k;
    if (totalInk > inkLimit && totalInk > 0.001) {
        double scale = inkLimit / totalInk;
        c *= scale;
        m *= scale;
        y *= scale;
        k *= scale;
    }

    // 2. Reconversão CMYK -> RGB simulado com absorção do papel
    double simR = (1.0 - c) * (1.0 - k * blackDensity) * paperWhiteness;
    double simG = (1.0 - m) * (1.0 - k * blackDensity) * paperWhiteness;
    double simB = (1.0 - y) * (1.0 - k * blackDensity) * paperWhiteness;

    return utils::ColorRGBA{
        static_cast<uint8_t>(std::clamp(simR * 255.0, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(simG * 255.0, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(simB * 255.0, 0.0, 255.0)),
        a
    };
}

utils::ColorRGBA ColorProfileManager::transformColor(utils::ColorRGBA src, ColorProfileType profile) noexcept {
    if (profile == ColorProfileType::Default_sRGB) {
        return src;
    }

    const double r = static_cast<double>(src.r) / 255.0;
    const double g = static_cast<double>(src.g) / 255.0;
    const double b = static_cast<double>(src.b) / 255.0;

    switch (profile) {
        case ColorProfileType::Display_P3: {
            // Conversão aproximada sRGB -> Display P3 (ligeira expansão e brilho nos primários)
            const double p3R = 0.8225 * r + 0.1775 * g;
            const double p3G = 0.0332 * r + 0.9668 * g;
            const double p3B = 0.0171 * r + 0.0724 * g + 0.9105 * b;
            return utils::ColorRGBA{
                static_cast<uint8_t>(std::clamp(p3R * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(p3G * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(p3B * 255.0, 0.0, 255.0)),
                src.a
            };
        }

        case ColorProfileType::Adobe_RGB: {
            const double ar = std::clamp(r * 0.98, 0.0, 1.0);
            const double ag = std::clamp(g * 1.12, 0.0, 1.0);
            const double ab = std::clamp(b * (g > 0.3 ? 1.08 : 1.0), 0.0, 1.0);
            return utils::ColorRGBA{
                static_cast<uint8_t>(ar * 255.0), static_cast<uint8_t>(ag * 255.0),
                static_cast<uint8_t>(ab * 255.0), src.a};
        }

        case ColorProfileType::Rec2020:
            return utils::ColorRGBA{
                static_cast<uint8_t>(std::clamp(std::pow(r, 0.9) * 1.05 * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(std::pow(g, 0.9) * 1.08 * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(std::pow(b, 0.9) * 1.05 * 255.0, 0.0, 255.0)), src.a};

        case ColorProfileType::SWOP_Coated:
            return simulateCmyk(r, g, b, src.a, 0.18, 3.0, 0.98, 0.96);

        case ColorProfileType::FOGRA39_Coated:
            return simulateCmyk(r, g, b, src.a, 0.15, 3.3, 0.99, 0.97);

        case ColorProfileType::GRACOL_Coated_2006:
            return simulateCmyk(r, g, b, src.a, 0.16, 3.2, 0.99, 0.98);

        case ColorProfileType::Japan_Coated_2001:
            return simulateCmyk(r, g, b, src.a, 0.14, 3.4, 1.00, 0.99);

        case ColorProfileType::Acromatopsia: {
            const double lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            const uint8_t lumByte = static_cast<uint8_t>(std::clamp(lum * 255.0, 0.0, 255.0));
            return utils::ColorRGBA{lumByte, lumByte, lumByte, src.a};
        }

        case ColorProfileType::ColorBlindness_Protanopia: {
            // Matriz Brettel-Vienot para Protanopia (sem receptores de vermelho)
            const double pr = 0.56667 * r + 0.43333 * g;
            const double pg = 0.55833 * r + 0.44167 * g;
            const double pb = 0.24167 * g + 0.75833 * b;
            return utils::ColorRGBA{
                static_cast<uint8_t>(std::clamp(pr * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(pg * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(pb * 255.0, 0.0, 255.0)),
                src.a
            };
        }

        case ColorProfileType::ColorBlindness_Deuteranopia: {
            // Matriz Brettel-Vienot para Deuteranopia (sem receptores de verde)
            const double dr = 0.62500 * r + 0.37500 * g;
            const double dg = 0.70000 * r + 0.30000 * g;
            const double db = 0.30000 * g + 0.70000 * b;
            return utils::ColorRGBA{
                static_cast<uint8_t>(std::clamp(dr * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(dg * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(db * 255.0, 0.0, 255.0)),
                src.a
            };
        }

        case ColorProfileType::ColorBlindness_Tritanopia: {
            // Matriz Brettel-Vienot para Tritanopia (sem receptores de azul)
            const double tr = 0.95000 * r + 0.05000 * g;
            const double tg = 0.43333 * g + 0.56667 * b;
            const double tb = 0.47500 * g + 0.52500 * b;
            return utils::ColorRGBA{
                static_cast<uint8_t>(std::clamp(tr * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(tg * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(tb * 255.0, 0.0, 255.0)),
                src.a
            };
        }

        case ColorProfileType::Linear_sRGB:
            return utils::ColorRGBA{
                static_cast<uint8_t>(std::clamp(std::pow(r, 2.2) * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(std::pow(g, 2.2) * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(std::pow(b, 2.2) * 255.0, 0.0, 255.0)), src.a};

        case ColorProfileType::ACEScg: {
            const auto tone = [](double value) {
                constexpr double a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
                return std::clamp((value * (a * value + b)) / (value * (c * value + d) + e), 0.0, 1.0);
            };
            return utils::ColorRGBA{
                static_cast<uint8_t>(tone(r * 1.2) * 255.0),
                static_cast<uint8_t>(tone(g * 1.2) * 255.0),
                static_cast<uint8_t>(tone(b * 1.2) * 255.0), src.a};
        }

        default:
            return src;
    }
}

void ColorProfileManager::transformBuffer(
    const uint8_t* srcRgba,
    uint8_t* dstRgba,
    int pixelCount,
    ColorProfileType profile
) noexcept {
    if (!srcRgba || !dstRgba || pixelCount <= 0) return;

    if (profile == ColorProfileType::Default_sRGB) {
        if (srcRgba != dstRgba) {
            std::copy(srcRgba, srcRgba + pixelCount * 4, dstRgba);
        }
        return;
    }

    for (int i = 0; i < pixelCount; ++i) {
        const int idx = i * 4;
        utils::ColorRGBA srcCol{srcRgba[idx], srcRgba[idx + 1], srcRgba[idx + 2], srcRgba[idx + 3]};
        utils::ColorRGBA outCol = transformColor(srcCol, profile);
        dstRgba[idx]     = outCol.r;
        dstRgba[idx + 1] = outCol.g;
        dstRgba[idx + 2] = outCol.b;
        dstRgba[idx + 3] = outCol.a;
    }
}

std::string ColorProfileManager::getProfileName(ColorProfileType profile) {
    switch (profile) {
        case ColorProfileType::Default_sRGB:             return "Padrão (sRGB)";
        case ColorProfileType::Display_P3:               return "Display P3 (Wide-Gamut)";
        case ColorProfileType::Adobe_RGB:                return "Adobe RGB (1998)";
        case ColorProfileType::Rec2020:                  return "Rec. 2020 (UHD TV)";
        case ColorProfileType::SWOP_Coated:              return "U.S. Web Coated (SWOP) v2";
        case ColorProfileType::FOGRA39_Coated:           return "ISO Coated v2 (FOGRA39)";
        case ColorProfileType::GRACOL_Coated_2006:       return "GRACoL 2006";
        case ColorProfileType::Japan_Coated_2001:        return "Japan Color 2001 Coated";
        case ColorProfileType::ColorBlindness_Protanopia:   return "Protanopia (Sem Vermelho)";
        case ColorProfileType::ColorBlindness_Deuteranopia: return "Deuteranopia (Sem Verde)";
        case ColorProfileType::ColorBlindness_Tritanopia:   return "Tritanopia (Sem Azul)";
        case ColorProfileType::Acromatopsia:              return "Acromatopsia (Monocromático)";
        case ColorProfileType::Linear_sRGB:               return "Linear sRGB (Physical Blending)";
        case ColorProfileType::ACEScg:                    return "ACEScg (Academy Color Encoding)";
        default: return "Desconhecido";
    }
}

std::vector<ColorProfileInfo> ColorProfileManager::getAvailableProfiles() {
    return {
        // Digital (RGB)
        {ColorProfileType::Default_sRGB, "Padrão (sRGB)", "Digital (RGB)", "Espaço de cor padrão universal para telas e web", "sRGB IEC61966-2.1", "D65 (6500K)", "sRGB"},
        {ColorProfileType::Display_P3, "Display P3 (Wide-Gamut)", "Digital (RGB)", "Espaço de cor expandido para telas modernas", "DCI-P3 D65", "D65 (6500K)", "sRGB Transfer"},
        {ColorProfileType::Adobe_RGB, "Adobe RGB (1998)", "Digital (RGB)", "Gamut ampliado para fotografia e pré-impressão", "Adobe RGB 1998", "D65 (6500K)", "Gamma 2.2"},
        {ColorProfileType::Rec2020, "Rec. 2020 (UHD TV)", "Digital (RGB)", "Gamut ultra-amplo para vídeo UHD", "BT.2020", "D65 (6500K)", "ITU-R BT.2020"},

        // Impressão (CMYK)
        {ColorProfileType::SWOP_Coated, "U.S. Web Coated (SWOP) v2", "Impressão (CMYK)", "Padrão americano para papel couché", "SWOP v2 (CMYK)", "D50 (5000K)", "Press Tone Value"},
        {ColorProfileType::FOGRA39_Coated, "ISO Coated v2 (FOGRA39)", "Impressão (CMYK)", "Referência europeia ISO 12647-2", "FOGRA39 (CMYK)", "D50 (5000K)", "ISO 12647-2"},
        {ColorProfileType::GRACOL_Coated_2006, "GRACoL 2006", "Impressão (CMYK)", "Especificação comercial G7", "GRACoL 2006", "D50 (5000K)", "G7 Curves"},
        {ColorProfileType::Japan_Coated_2001, "Japan Color 2001 Coated", "Impressão (CMYK)", "Padrão japonês para papel revestido", "Japan Color 2001", "D50 (5000K)", "Japan Print Std"},

        // Acessibilidade / Daltonismo
        {ColorProfileType::ColorBlindness_Protanopia, "Protanopia (Sem Vermelho)", "Acessibilidade", "Simulação de daltonismo para receptores L", "Simulação Protanopia", "D65", "Linear Match"},
        {ColorProfileType::ColorBlindness_Deuteranopia, "Deuteranopia (Sem Verde)", "Acessibilidade", "Simulação de daltonismo para receptores M", "Simulação Deuteranopia", "D65", "Linear Match"},
        {ColorProfileType::ColorBlindness_Tritanopia, "Tritanopia (Sem Azul)", "Acessibilidade", "Simulação de daltonismo para receptores S", "Simulação Tritanopia", "D65", "Linear Match"},
        {ColorProfileType::Acromatopsia, "Acromatopsia (Monocromático)", "Acessibilidade", "Prova de luminância Rec.709", "Luminância Pura (Y)", "D65", "Luminance Rec.709"},

        // Motor físico
        {ColorProfileType::Linear_sRGB, "Linear sRGB (Physical Blending)", "Motor Físico", "Mistura fotométrica linear", "sRGB Primaries", "D65 (6500K)", "1.0 (Linear)"},
        {ColorProfileType::ACEScg, "ACEScg (Academy Color Encoding)", "Motor Físico", "Codificação linear para VFX", "AP1 Primaries", "D60 (ACES)", "1.0 (Linear Float)"}
    };
}

bool ColorProfileManager::isProfileValid(int profileId) {
    return profileId >= static_cast<int>(ColorProfileType::Default_sRGB)
        && profileId <= static_cast<int>(ColorProfileType::ACEScg);
}

} // namespace aladyn::engine::color
