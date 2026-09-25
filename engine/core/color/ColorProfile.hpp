#ifndef ALADYN_ENGINE_COLOR_PROFILE_HPP
#define ALADYN_ENGINE_COLOR_PROFILE_HPP

#include <cstdint>
#include <string>
#include <vector>
#include "../../utils/ColorRGBA.hpp"

namespace aladyn::engine::color {

enum class ColorProfileType : int {
    // IDs canônicos compartilhados pela UI, pelo rasterizador e pelo LMN.
    Default_sRGB                = 0,
    Display_P3                  = 1,
    Adobe_RGB                   = 2,
    Rec2020                     = 3,
    SWOP_Coated                 = 4,
    FOGRA39_Coated              = 5,
    GRACOL_Coated_2006          = 6,
    Japan_Coated_2001           = 7,
    ColorBlindness_Protanopia   = 8,
    ColorBlindness_Deuteranopia = 9,
    ColorBlindness_Tritanopia   = 10,
    Acromatopsia                = 11,
    Linear_sRGB                 = 12,
    ACEScg                      = 13
};

struct ColorProfileInfo {
    ColorProfileType type;
    std::string name;
    std::string category; // "Digital (RGB)", "Impressão (CMYK)", "Escala de Cinza", "Acessibilidade"
    std::string description;
    // Metadados de apresentação pertencem ao catálogo canônico e chegam à UI
    // apenas pela ponte, evitando uma segunda tabela de especificações.
    std::string gamut;
    std::string whitepoint;
    std::string transfer;
};

class ColorProfileManager {
public:
    static utils::ColorRGBA transformColor(utils::ColorRGBA src, ColorProfileType profile) noexcept;

    static void transformBuffer(
        const uint8_t* srcRgba,
        uint8_t* dstRgba,
        int pixelCount,
        ColorProfileType profile
    ) noexcept;

    static std::string getProfileName(ColorProfileType profile);
    static std::vector<ColorProfileInfo> getAvailableProfiles();
    static bool isProfileValid(int profileId);
};

} // namespace aladyn::engine::color

#endif // ALADYN_ENGINE_COLOR_PROFILE_HPP
