#include "BlurEngine.hpp"
#include "../raster/DabFootprint.hpp"
#include "../raster/LargeBrushOptimizer.hpp"
#include "../raster/PixelPermission.hpp"
#include <algorithm>
#include <cmath>
#include <vector>

namespace aladyn::engine::engines {

namespace {

// Amostra segura na TileGrid da camada ativa
utils::ColorRGBA getTilePixel(const canvas::TileGrid& tileGrid, int globalX, int globalY) {
    if (globalX < 0 || globalX >= tileGrid.getWidth() || globalY < 0 || globalY >= tileGrid.getHeight()) {
        return {0, 0, 0, 0};
    }
    const int tx  = globalX / canvas::Tile::TILE_SIZE;
    const int ty  = globalY / canvas::Tile::TILE_SIZE;
    const int lpx = globalX % canvas::Tile::TILE_SIZE;
    const int lpy = globalY % canvas::Tile::TILE_SIZE;

    const canvas::Tile* t = const_cast<canvas::TileGrid&>(tileGrid).getTile(tx, ty);
    return t ? t->getBuffer().getPixel(lpx, lpy) : utils::ColorRGBA{0, 0, 0, 0};
}

struct Region {
    int minX, maxX, minY, maxY;
    [[nodiscard]] int width() const { return maxX - minX + 1; }
    [[nodiscard]] int height() const { return maxY - minY + 1; }
    [[nodiscard]] bool empty() const { return width() <= 0 || height() <= 0; }
    [[nodiscard]] bool contains(int x, int y) const { return x >= minX && x <= maxX && y >= minY && y <= maxY; }
};

// Resultado do passe horizontal de um pixel do snapshot.
struct HorizontalSum {
    float r{0.0f}, g{0.0f}, b{0.0f}, a{0.0f};
    float alphaWeight{0.0f}, totalWeight{0.0f};
};

// O desfoque gaussiano de uma região: uma cópia contígua da área da camada (com a borda do kernel),
// o passe horizontal já feito e `blurredAt`, que faz o vertical de um pixel. Lê só da cópia: o resultado
// de um pixel não depende de os vizinhos já terem sido pintados.
class BlurredRegion {
public:
    BlurredRegion(const canvas::TileGrid& grid, const Region& roi, int kernelRadius, double sigma)
        : m_kernelRadius(kernelRadius),
          m_snap{std::max(0, roi.minX - kernelRadius), std::min(grid.getWidth() - 1, roi.maxX + kernelRadius),
                 std::max(0, roi.minY - kernelRadius), std::min(grid.getHeight() - 1, roi.maxY + kernelRadius)} {
        m_width = m_snap.width();
        m_height = m_snap.height();
        if (m_snap.empty()) return;

        copyFrom(grid);
        buildWeights(sigma);
        blurRows();
    }

    [[nodiscard]] bool empty() const { return m_snap.empty(); }

    // O pixel original, na cópia.
    [[nodiscard]] utils::ColorRGBA originalAt(int globalX, int globalY) const {
        return m_source[static_cast<size_t>((globalY - m_snap.minY) * m_width + (globalX - m_snap.minX))];
    }

    struct Blurred {
        float r, g, b, a;
        float alphaWeight, totalWeight;
    };

    // Passe vertical sobre os resultados do horizontal.
    [[nodiscard]] Blurred blurredAt(int globalX, int globalY) const {
        const int snapX = globalX - m_snap.minX;
        const int snapY = globalY - m_snap.minY;
        Blurred sum{0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
        for (int k = -m_kernelRadius; k <= m_kernelRadius; ++k) {
            const int ky = std::clamp(snapY + k, 0, m_height - 1);
            const float w = m_weights[static_cast<size_t>(k + m_kernelRadius)];
            const HorizontalSum& sample = m_rows[static_cast<size_t>(ky * m_width + snapX)];
            sum.r += sample.r * w;
            sum.g += sample.g * w;
            sum.b += sample.b * w;
            sum.a += sample.a * w;
            sum.alphaWeight += sample.alphaWeight * w;
            sum.totalWeight += sample.totalWeight * w;
        }
        return sum;
    }

private:
    void copyFrom(const canvas::TileGrid& grid) {
        m_source.resize(static_cast<size_t>(m_width * m_height));
        for (int sy = 0; sy < m_height; ++sy) {
            for (int sx = 0; sx < m_width; ++sx) {
                m_source[static_cast<size_t>(sy * m_width + sx)] = getTilePixel(grid, m_snap.minX + sx, m_snap.minY + sy);
            }
        }
    }

    // Pesos gaussianos 1D (LUT).
    void buildWeights(double sigma) {
        m_weights.resize(static_cast<size_t>(2 * m_kernelRadius + 1));
        for (int k = -m_kernelRadius; k <= m_kernelRadius; ++k) {
            m_weights[static_cast<size_t>(k + m_kernelRadius)] = static_cast<float>(std::exp(-(k * k) / (2.0 * sigma * sigma)));
        }
    }

    // Convolução separável em dois passes: O(2K) em vez de O(K²).
    void blurRows() {
        m_rows.resize(static_cast<size_t>(m_width * m_height));
        for (int sy = 0; sy < m_height; ++sy) {
            for (int sx = 0; sx < m_width; ++sx) {
                m_rows[static_cast<size_t>(sy * m_width + sx)] = horizontalSum(sx, sy);
            }
        }
    }

    HorizontalSum horizontalSum(int sx, int sy) const {
        HorizontalSum sum;
        for (int k = -m_kernelRadius; k <= m_kernelRadius; ++k) {
            const int kx = std::clamp(sx + k, 0, m_width - 1);
            const float w = m_weights[static_cast<size_t>(k + m_kernelRadius)];
            const utils::ColorRGBA px = m_source[static_cast<size_t>(sy * m_width + kx)];

            const float alpha = static_cast<float>(px.a) / 255.0f;
            if (px.a > 0) {
                sum.r += static_cast<float>(px.r) * alpha * w;
                sum.g += static_cast<float>(px.g) * alpha * w;
                sum.b += static_cast<float>(px.b) * alpha * w;
                sum.alphaWeight += alpha * w;
            }
            sum.a += static_cast<float>(px.a) * w;
            sum.totalWeight += w;
        }
        return sum;
    }

    int m_kernelRadius;
    Region m_snap;
    int m_width{0};
    int m_height{0};
    std::vector<utils::ColorRGBA> m_source;
    std::vector<float> m_weights;
    std::vector<HorizontalSum> m_rows;
};

// Mistura o pixel original com o desfocado na proporção `mix`; com Alpha Lock o alfa fica.
utils::ColorRGBA mixTowardBlur(
    utils::ColorRGBA original, const BlurredRegion::Blurred& blurred, double mix, bool alphaLocked
) {
    float targetR = static_cast<float>(original.r);
    float targetG = static_cast<float>(original.g);
    float targetB = static_cast<float>(original.b);
    if (blurred.alphaWeight > 0.0f) {
        targetR = blurred.r / blurred.alphaWeight;
        targetG = blurred.g / blurred.alphaWeight;
        targetB = blurred.b / blurred.alphaWeight;
    }
    const auto toward = [mix](uint8_t from, float to) {
        return static_cast<double>(from) * (1.0 - mix) + static_cast<double>(to) * mix;
    };
    double outA = static_cast<double>(original.a);
    if (!alphaLocked) {
        const double smoothedA = (blurred.totalWeight > 0.0f) ? static_cast<double>(blurred.a / blurred.totalWeight)
                                                              : static_cast<double>(original.a);
        outA = static_cast<double>(original.a) * (1.0 - mix) + smoothedA * mix;
    }
    const auto byte = [](double v) { return static_cast<uint8_t>(std::clamp(v, 0.0, 255.0)); };
    return utils::ColorRGBA{byte(toward(original.r, targetR)), byte(toward(original.g, targetG)),
                            byte(toward(original.b, targetB)), byte(outA)};
}

} // namespace

void BlurEngine::renderDab(
    const utils::Dab& dab,
    const brush::BrushProfile& profile,
    const canvas::CanvasTexture& /*canvasTexture*/,
    canvas::TileGrid& tileGrid,
    const raster::PixelContext& ctx
) {
    if (dab.radius <= 0.0) return;

    const double r      = dab.radius;
    const double aspect = std::max(0.05, profile.tip.aspectRatio);
    const double maxR   = r / aspect + 2.0;

    const int blurRadiusSetting = std::clamp(profile.blurParams.blurRadius, 1, 5);
    const double strength       = std::clamp(profile.blurParams.blurStrength, 0.0, 1.0);

    // Raio do kernel proporcional ao dab (mínimo 2px, máximo 20px)
    const int kernelRadius = std::clamp(
        static_cast<int>(std::round(r * 0.20 * static_cast<double>(blurRadiusSetting))), 2, 20);
    const double sigma = std::max(0.8, static_cast<double>(kernelRadius) * (0.35 + strength * 0.45));

    // Caixa do dab com a margem do kernel, para a cópia da área
    const Region roi{
        std::max(0, static_cast<int>(std::floor(dab.position.x - maxR))),
        std::min(tileGrid.getWidth() - 1, static_cast<int>(std::ceil(dab.position.x + maxR))),
        std::max(0, static_cast<int>(std::floor(dab.position.y - maxR))),
        std::min(tileGrid.getHeight() - 1, static_cast<int>(std::ceil(dab.position.y + maxR)))};
    if (roi.empty()) return;

    const BlurredRegion region(tileGrid, roi, kernelRadius, sigma);
    if (region.empty()) return;

    // O desfoque ignora a rotação e o achatamento da ponta: o dab é sempre um círculo.
    utils::Dab disc = dab;
    disc.angle = 0.0;
    const raster::DabFootprint footprint(disc, r, 1.0, tileGrid);
    if (footprint.empty()) return;

    const double hardSpan = std::clamp(profile.hardness, 0.0, 0.99) * r;
    const double spanInv  = 1.0 / std::max(0.001, r - hardSpan);
    const raster::PixelPermission permission(ctx);
    footprint.forEachPixel(6, [&](utils::ColorRGBA& dst, const raster::DabPixel& pixel) {
        if (!roi.contains(pixel.gx, pixel.gy)) return false;  // fora da cópia e do canvas

        // Falloff smoothstep
        const double dist = std::sqrt(pixel.distSq);
        const double shape = dist > hardSpan ? raster::LargeBrushOptimizer::smoothHermite((r - dist) * spanInv) : 1.0;
        double mix = dab.opacity * shape * strength;
        if (shape <= 0.0 || mix <= 0.0) return false;

        // Pixel fora da cópia (borda do canvas) não existe; um pixel vazio sem tinta em volta não muda
        const utils::ColorRGBA original = region.originalAt(pixel.gx, pixel.gy);
        const BlurredRegion::Blurred blurred = region.blurredAt(pixel.gx, pixel.gy);
        if (original.a == 0 && blurred.alphaWeight <= 0.0f) return false;
        if (ctx.alphaLocked && original.a == 0) return false;

        if (!permission.apply(pixel.gx, pixel.gy, mix) || mix <= 0.0) return false;

        dst = mixTowardBlur(original, blurred, mix, ctx.alphaLocked);
        return true;
    });
}

} // namespace aladyn::engine::engines
