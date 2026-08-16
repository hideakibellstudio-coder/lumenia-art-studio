#include "ProceduralTextures.hpp"
#include "../math/MathUtils.hpp"
#include <cmath>
#include <random>
#include <algorithm>

namespace aladyn::engine::texture {

std::shared_ptr<Texture2D> ProceduralTextures::createShapePreset(ShapePreset preset, int size) {
    auto tex = std::make_shared<Texture2D>(size, size);
    const double center = static_cast<double>(size) * 0.5;
    const double maxDist = center;
    std::mt19937 rng(123);
    std::uniform_real_distribution<double> distNoise(0.5, 1.0);

    for (int y = 0; y < size; ++y) {
        const double dy = static_cast<double>(y) + 0.5 - center;
        for (int x = 0; x < size; ++x) {
            const double dx = static_cast<double>(x) + 0.5 - center;
            const double dist = std::sqrt(dx * dx + dy * dy);

            double alpha = 0.0;
            switch (preset) {
                case ShapePreset::SoftCircle: {
                    if (dist <= maxDist * 0.8) {
                        alpha = 1.0;
                    } else if (dist <= maxDist) {
                        alpha = (maxDist - dist) / (maxDist * 0.2);
                    }
                    break;
                }
                case ShapePreset::HardCircle: {
                    if (dist <= maxDist * 0.95) {
                        alpha = 1.0;
                    } else if (dist <= maxDist) {
                        alpha = (maxDist - dist) / (maxDist * 0.05);
                    }
                    break;
                }
                case ShapePreset::DryBristles: {
                    if (dist <= maxDist) {
                        const double baseFalloff = 1.0 - (dist / maxDist);
                        const double bristleNoise = std::sin(dx * 0.4) * std::cos(dy * 0.4) * 0.5 + 0.5;
                        alpha = baseFalloff * bristleNoise * distNoise(rng);
                    }
                    break;
                }
                case ShapePreset::Square: {
                    if (std::abs(dx) <= maxDist * 0.9 && std::abs(dy) <= maxDist * 0.9) {
                        alpha = 1.0;
                    }
                    break;
                }
            }
            alpha = math::MathUtils::clamp(alpha, 0.0, 1.0);
            tex->setPixel(x, y, static_cast<uint8_t>(alpha * 255.0));
        }
    }
    return tex;
}

std::shared_ptr<Texture2D> ProceduralTextures::createHeightPreset(HeightPreset preset, int width, int height) {
    auto tex = std::make_shared<Texture2D>(width, height);
    std::mt19937 rng(42);
    std::uniform_int_distribution<int> dist(0, 255);

    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            double val = 128.0;
            switch (preset) {
                case HeightPreset::FinePaper: {
                    const double wave1 = std::sin(static_cast<double>(x) * 0.03) * std::cos(static_cast<double>(y) * 0.03) * 40.0;
                    const double noise = static_cast<double>(dist(rng)) * 0.2;
                    val = 128.0 + wave1 + noise;
                    break;
                }
                case HeightPreset::WatercolorPaper: {
                    const double wave1 = std::sin(static_cast<double>(x) * 0.06) * 50.0;
                    const double wave2 = std::cos(static_cast<double>(y) * 0.06) * 50.0;
                    const double noise = static_cast<double>(dist(rng)) * 0.4;
                    val = 128.0 + (wave1 + wave2) * 0.5 + noise;
                    break;
                }
                case HeightPreset::CanvasOil: {
                    const double threadH = (std::sin(static_cast<double>(y) * 0.25) > 0.0) ? 60.0 : -60.0;
                    const double threadV = (std::sin(static_cast<double>(x) * 0.25) > 0.0) ? 60.0 : -60.0;
                    const double noise = static_cast<double>(dist(rng)) * 0.15;
                    val = 128.0 + (threadH + threadV) * 0.5 + noise;
                    break;
                }
                case HeightPreset::NoiseGrain: {
                    val = static_cast<double>(dist(rng));
                    break;
                }
            }
            val = math::MathUtils::clamp(val, 0.0, 255.0);
            tex->setPixel(x, y, static_cast<uint8_t>(val));
        }
    }
    return tex;
}

std::shared_ptr<Texture2D> ProceduralTextures::createRadialShapeMask(int size) {
    return createShapePreset(ShapePreset::SoftCircle, size);
}

std::shared_ptr<Texture2D> ProceduralTextures::createPaperGrain(int width, int height) {
    return createHeightPreset(HeightPreset::FinePaper, width, height);
}

} // namespace aladyn::engine::texture
