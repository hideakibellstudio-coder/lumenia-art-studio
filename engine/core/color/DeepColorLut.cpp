#include "DeepColorLut.hpp"

#include <cmath>
#include <cstring>

namespace aladyn::engine::color {

namespace {

uint64_t bitsOf(double value) noexcept {
    uint64_t bits = 0;
    std::memcpy(&bits, &value, sizeof bits);
    return bits;
}

double doubleOf(uint64_t bits) noexcept {
    double value = 0.0;
    std::memcpy(&value, &bits, sizeof value);
    return value;
}

// O menor double em [0, 1] cuja imagem pela definição é >= step. Os doubles não negativos se ordenam
// como os seus bits, então a bisecção é sobre os bits: 63 passos exatos, sem aproximar nada.
double firstDoubleReaching(unsigned step) noexcept {
    uint64_t below = bitsOf(0.0);  // imagem < step (step >= 1)
    uint64_t reach = bitsOf(1.0);  // imagem = 255 >= step
    while (reach - below > 1) {
        const uint64_t middle = below + (reach - below) / 2;
        if (linearToSRGBPrecise(doubleOf(middle)) >= step) {
            reach = middle;
        } else {
            below = middle;
        }
    }
    return doubleOf(reach);
}

} // namespace

DeepColorLut::DeepColorLut() noexcept {
    for (int c = 0; c < 256; ++c) {
        // A expressão do `toLinear` de blendLinearNormalHighPrecision, sem mudar uma conta.
        const double s = static_cast<double>(c) / 255.0;
        toLinear[c] = (s <= 0.04045) ? s / 12.92 : std::pow((s + 0.055) / 1.055, 2.4);
    }
    threshold[0] = 0.0;
    for (unsigned step = 1; step <= 255; ++step) threshold[step] = firstDoubleReaching(step);
    threshold[256] = INFINITY;
    for (int bucket = 0; bucket <= kBuckets; ++bucket) {
        const double left = static_cast<double>(bucket) / kBuckets;
        const double right = static_cast<double>(bucket + 1) / kBuckets;
        lowest[bucket] = linearToSRGBPrecise(left > 1.0 ? 1.0 : left);
        highest[bucket] = linearToSRGBPrecise(right > 1.0 ? 1.0 : right);
    }
}

const DeepColorLut& deepColorLut() noexcept {
    static const DeepColorLut lut;
    return lut;
}

} // namespace aladyn::engine::color
