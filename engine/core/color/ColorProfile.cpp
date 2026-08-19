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
static inline raster::ColorRGBA simulateCmyk(
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

    return raster::ColorRGBA{
        static_cast<uint8_t>(std::clamp(simR * 255.0, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(simG * 255.0, 0.0, 255.0)),
        static_cast<uint8_t>(std::clamp(simB * 255.0, 0.0, 255.0)),
        a
    };
}

raster::ColorRGBA ColorProfileManager::transformColor(raster::ColorRGBA src, ColorProfileType profile) noexcept {
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
            return raster::ColorRGBA{
                static_cast<uint8_t>(std::clamp(p3R * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(p3G * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(p3B * 255.0, 0.0, 255.0)),
                src.a
            };
        }

        case ColorProfileType::Generic_CMYK:
            return simulateCmyk(r, g, b, src.a, 0.18, 3.0, 0.98, 0.95);

        case ColorProfileType::US_SWOP_Web_Coated_v2:
            return simulateCmyk(r, g, b, src.a, 0.18, 3.0, 0.98, 0.96);

        case ColorProfileType::US_SWOP_Web_Coated_G3:
            return simulateCmyk(r, g, b, src.a, 0.20, 2.9, 0.96, 0.94);

        case ColorProfileType::US_SWOP_Web_Coated_G5:
            return simulateCmyk(r, g, b, src.a, 0.22, 2.8, 0.94, 0.92);

        case ColorProfileType::US_GRACOL_Coated_2006:
            return simulateCmyk(r, g, b, src.a, 0.16, 3.2, 0.99, 0.98);

        case ColorProfileType::US_SWOP_Web_Uncoated_v2:
            return simulateCmyk(r, g, b, src.a, 0.26, 2.6, 0.90, 0.88);

        case ColorProfileType::Europe_FOGRA39_Coated:
            return simulateCmyk(r, g, b, src.a, 0.15, 3.3, 0.99, 0.97);

        case ColorProfileType::Euroscale_Coated_v2:
            return simulateCmyk(r, g, b, src.a, 0.17, 3.1, 0.98, 0.96);

        case ColorProfileType::Euroscale_Uncoated_v2:
            return simulateCmyk(r, g, b, src.a, 0.24, 2.7, 0.91, 0.89);

        case ColorProfileType::Japan_Coated_2011:
            return simulateCmyk(r, g, b, src.a, 0.14, 3.4, 1.00, 0.99);

        case ColorProfileType::Generic_Grayscale: {
            const double lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            const uint8_t lumByte = static_cast<uint8_t>(std::clamp(lum * 255.0, 0.0, 255.0));
            return raster::ColorRGBA{lumByte, lumByte, lumByte, src.a};
        }

        case ColorProfileType::Line_Art_HighContrast: {
            const double lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            const uint8_t binByte = (lum >= 0.5) ? 255 : 0;
            return raster::ColorRGBA{binByte, binByte, binByte, src.a};
        }

        case ColorProfileType::ColorBlindness_Protanopia: {
            // Matriz Brettel-Vienot para Protanopia (sem receptores de vermelho)
            const double pr = 0.56667 * r + 0.43333 * g;
            const double pg = 0.55833 * r + 0.44167 * g;
            const double pb = 0.24167 * g + 0.75833 * b;
            return raster::ColorRGBA{
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
            return raster::ColorRGBA{
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
            return raster::ColorRGBA{
                static_cast<uint8_t>(std::clamp(tr * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(tg * 255.0, 0.0, 255.0)),
                static_cast<uint8_t>(std::clamp(tb * 255.0, 0.0, 255.0)),
                src.a
            };
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
        raster::ColorRGBA srcCol{srcRgba[idx], srcRgba[idx + 1], srcRgba[idx + 2], srcRgba[idx + 3]};
        raster::ColorRGBA outCol = transformColor(srcCol, profile);
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
        case ColorProfileType::Generic_CMYK:             return "Generic CMYK";
        case ColorProfileType::US_SWOP_Web_Coated_v2:    return "SWOP Web Coated v2";
        case ColorProfileType::US_SWOP_Web_Coated_G3:    return "SWOP Web Coated, Grade 3";
        case ColorProfileType::US_SWOP_Web_Coated_G5:    return "SWOP Web Coated, Grade 5";
        case ColorProfileType::US_GRACOL_Coated_2006:    return "GRACoL Coated 2006";
        case ColorProfileType::US_SWOP_Web_Uncoated_v2:  return "SWOP Web Uncoated v2";
        case ColorProfileType::Europe_FOGRA39_Coated:    return "FOGRA39 Coated";
        case ColorProfileType::Euroscale_Coated_v2:      return "Euroscale Coated v2";
        case ColorProfileType::Euroscale_Uncoated_v2:    return "Euroscale Uncoated v2";
        case ColorProfileType::Japan_Coated_2011:        return "Japan Coated 2011";
        case ColorProfileType::Generic_Grayscale:        return "Escala de Cinza";
        case ColorProfileType::Line_Art_HighContrast:    return "Line Art (Alto Contraste)";
        case ColorProfileType::ColorBlindness_Protanopia:   return "Protanopia (Sem Vermelho)";
        case ColorProfileType::ColorBlindness_Deuteranopia: return "Deuteranopia (Sem Verde)";
        case ColorProfileType::ColorBlindness_Tritanopia:   return "Tritanopia (Sem Azul)";
        default: return "Desconhecido";
    }
}

std::vector<ColorProfileInfo> ColorProfileManager::getAvailableProfiles() {
    return {
        // Digital (RGB)
        {ColorProfileType::Default_sRGB, "Padrão (sRGB)", "Digital (RGB)", "Espaço de cor padrão universal para telas e web"},
        {ColorProfileType::Display_P3, "Display P3 (Wide-Gamut)", "Digital (RGB)", "Espaço de cor expandido para telas modernas"},

        // Impressão (CMYK)
        {ColorProfileType::Generic_CMYK, "Generic CMYK", "Impressão (CMYK)", "Simulação CMYK genérica"},
        {ColorProfileType::US_SWOP_Web_Coated_v2, "SWOP Web Coated v2", "Impressão (CMYK)", "Padrão americano para papel brilhante/revestido"},
        {ColorProfileType::US_SWOP_Web_Coated_G3, "SWOP Web Coated, Grade 3", "Impressão (CMYK)", "Padrão americano grau 3"},
        {ColorProfileType::US_SWOP_Web_Coated_G5, "SWOP Web Coated, Grade 5", "Impressão (CMYK)", "Padrão americano grau 5"},
        {ColorProfileType::US_SWOP_Web_Uncoated_v2, "SWOP Web Uncoated v2", "Impressão (CMYK)", "Padrão americano para papel fosco/não revestido"},
        {ColorProfileType::US_GRACOL_Coated_2006, "GRACoL Coated 2006", "Impressão (CMYK)", "Padrão comercial de alta definição G7"},
        {ColorProfileType::Europe_FOGRA39_Coated, "FOGRA39 Coated", "Impressão (CMYK)", "Padrão Europeu ISO 12647-2 para papéis revestidos"},
        {ColorProfileType::Euroscale_Coated_v2, "Euroscale Coated v2", "Impressão (CMYK)", "Padrão Euroscale para papéis revestidos"},
        {ColorProfileType::Euroscale_Uncoated_v2, "Euroscale Uncoated v2", "Impressão (CMYK)", "Padrão Euroscale para papéis foscos"},
        {ColorProfileType::Japan_Coated_2011, "Japan Coated 2011", "Impressão (CMYK)", "Padrão japonês para papéis de alta alvura"},

        // Escala de Cinza
        {ColorProfileType::Generic_Grayscale, "Escala de Cinza", "Escala de Cinza", "Prova tonal de valores de luz e sombra"},
        {ColorProfileType::Line_Art_HighContrast, "Line Art (Alto Contraste)", "Escala de Cinza", "Prova binária para arte-final e nanquim puro"},

        // Acessibilidade / Daltonismo
        {ColorProfileType::ColorBlindness_Protanopia, "Protanopia (Sem Vermelho)", "Acessibilidade", "Simulação de daltonismo para receptores L"},
        {ColorProfileType::ColorBlindness_Deuteranopia, "Deuteranopia (Sem Verde)", "Acessibilidade", "Simulação de daltonismo para receptores M"},
        {ColorProfileType::ColorBlindness_Tritanopia, "Tritanopia (Sem Azul)", "Acessibilidade", "Simulação de daltonismo para receptores S"}
    };
}

bool ColorProfileManager::isProfileValid(int profileId) {
    switch (static_cast<ColorProfileType>(profileId)) {
        case ColorProfileType::Default_sRGB:
        case ColorProfileType::Display_P3:
        case ColorProfileType::Generic_CMYK:
        case ColorProfileType::US_SWOP_Web_Coated_v2:
        case ColorProfileType::US_SWOP_Web_Coated_G3:
        case ColorProfileType::US_SWOP_Web_Coated_G5:
        case ColorProfileType::US_GRACOL_Coated_2006:
        case ColorProfileType::US_SWOP_Web_Uncoated_v2:
        case ColorProfileType::Europe_FOGRA39_Coated:
        case ColorProfileType::Euroscale_Coated_v2:
        case ColorProfileType::Euroscale_Uncoated_v2:
        case ColorProfileType::Japan_Coated_2011:
        case ColorProfileType::Generic_Grayscale:
        case ColorProfileType::Line_Art_HighContrast:
        case ColorProfileType::ColorBlindness_Protanopia:
        case ColorProfileType::ColorBlindness_Deuteranopia:
        case ColorProfileType::ColorBlindness_Tritanopia:
            return true;
        default:
            return false;
    }
}

} // namespace aladyn::engine::color
