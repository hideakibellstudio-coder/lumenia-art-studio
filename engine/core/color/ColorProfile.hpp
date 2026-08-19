#ifndef ALADYN_ENGINE_COLOR_PROFILE_HPP
#define ALADYN_ENGINE_COLOR_PROFILE_HPP

#include <cstdint>
#include <string>
#include <vector>
#include "../raster/Dab.hpp"

namespace aladyn::engine::color {

enum class ColorProfileType : int {
    // Digital RGB
    Default_sRGB             = 0,
    Display_P3               = 1,

    // Impressão CMYK (Soft-Proofing)
    Generic_CMYK             = 10,
    US_SWOP_Web_Coated_v2    = 20,
    US_SWOP_Web_Coated_G3    = 21,
    US_SWOP_Web_Coated_G5    = 22,
    US_GRACOL_Coated_2006    = 23,
    US_SWOP_Web_Uncoated_v2  = 25,
    Europe_FOGRA39_Coated    = 30,
    Euroscale_Coated_v2      = 31,
    Euroscale_Uncoated_v2    = 35,
    Japan_Coated_2011        = 40,

    // Escala de Cinza
    Generic_Grayscale        = 50,
    Line_Art_HighContrast    = 51,

    // Acessibilidade / Daltonismo (Color Blindness Simulation)
    ColorBlindness_Protanopia   = 60,
    ColorBlindness_Deuteranopia = 61,
    ColorBlindness_Tritanopia   = 62
};

struct ColorProfileInfo {
    ColorProfileType type;
    std::string name;
    std::string category; // "Digital (RGB)", "Impressão (CMYK)", "Escala de Cinza", "Acessibilidade"
    std::string description;
};

class ColorProfileManager {
public:
    static raster::ColorRGBA transformColor(raster::ColorRGBA src, ColorProfileType profile) noexcept;

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
