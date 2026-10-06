#include "LinearColorSpace16.hpp"

#include <algorithm>
#include <cmath>

namespace aladyn::engine::color {

double srgbToLinearReference(double encoded) noexcept {
    return (encoded <= 0.04045) ? encoded / 12.92 : std::pow((encoded + 0.055) / 1.055, 2.4);
}

double linearToSrgbReference(double linear) noexcept {
    const double clamped = std::clamp(linear, 0.0, 1.0);
    return (clamped <= 0.0031308) ? clamped * 12.92 : 1.055 * std::pow(clamped, 1.0 / 2.4) - 0.055;
}

uint16_t linearToSrgb16Reference(double linear) noexcept {
    return static_cast<uint16_t>(std::clamp(std::lround(linearToSrgbReference(linear) * 65535.0), 0l, 65535l));
}

Srgb16Tables::Srgb16Tables() noexcept {
    for (int value = 0; value < 65536; ++value) {
        toLinear[value] = static_cast<float>(srgbToLinearReference(static_cast<double>(value) / 65535.0));
    }
    for (int point = 0; point <= kEncodeBuckets; ++point) {
        encode[point] = static_cast<float>(linearToSrgbReference(static_cast<double>(point) / kEncodeBuckets) * 65535.0);
    }
    encode[kEncodeBuckets + 1] = encode[kEncodeBuckets];
}

const Srgb16Tables& srgb16Tables() noexcept {
    static const Srgb16Tables tables;
    return tables;
}

} // namespace aladyn::engine::color
