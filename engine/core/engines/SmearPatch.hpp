#ifndef ALADYN_ENGINE_SMEAR_PATCH_HPP
#define ALADYN_ENGINE_SMEAR_PATCH_HPP

#include "../../utils/ColorRGBA.hpp"
#include "../../utils/ColorRGBA16.hpp"
#include "../../utils/MathUtils.hpp"
#include <algorithm>
#include <cmath>
#include <vector>

namespace aladyn::engine::engines {

// Cor em alfa pré-multiplicado, em ponto flutuante: a unidade em que o Borrar mistura, para que misturar
// duas cores iguais devolva a mesma cor e arrastar sobre uma área lisa não mude nada (a deriva de
// 200,100,50 para 193,93,43 por passada, medida em 2026-10-02, vinha de misturar bytes retos).
struct PremultColor {
    float r{0.0f}, g{0.0f}, b{0.0f}, a{0.0f};

    [[nodiscard]] static PremultColor from(utils::ColorRGBA c) noexcept {
        const float alpha = static_cast<float>(c.a) / 255.0f;
        return {static_cast<float>(c.r) / 255.0f * alpha, static_cast<float>(c.g) / 255.0f * alpha,
                static_cast<float>(c.b) / 255.0f * alpha, alpha};
    }

    [[nodiscard]] static PremultColor from(utils::ColorRGBA16 c) noexcept {
        const float alpha = static_cast<float>(c.a) / 65535.0f;
        return {static_cast<float>(c.r) / 65535.0f * alpha, static_cast<float>(c.g) / 65535.0f * alpha,
                static_cast<float>(c.b) / 65535.0f * alpha, alpha};
    }

    // De volta a 8 bits com alfa reto, arredondado. `keepAlpha`: o alfa do pixel (Alpha Lock) em vez do misturado.
    [[nodiscard]] utils::ColorRGBA toStraight(int keepAlpha = -1) const noexcept {
        if (!(a > 0.0f)) return keepAlpha >= 0 ? utils::ColorRGBA{0, 0, 0, static_cast<uint8_t>(keepAlpha)} : utils::ColorRGBA{0, 0, 0, 0};
        const auto channel = [&](float premult) { return utils::MathUtils::roundToByte(static_cast<double>(premult / a) * 255.0); };
        return utils::ColorRGBA{channel(r), channel(g), channel(b),
                                keepAlpha >= 0 ? static_cast<uint8_t>(keepAlpha) : utils::MathUtils::unitToByte(a)};
    }

    [[nodiscard]] utils::ColorRGBA16 toStraight16(int keepAlpha = -1) const noexcept {
        if (!(a > 0.0f)) return keepAlpha >= 0 ? utils::ColorRGBA16{0, 0, 0, static_cast<uint16_t>(keepAlpha)} : utils::ColorRGBA16{0, 0, 0, 0};
        const auto channel = [&](float premult) {
            return static_cast<uint16_t>(std::clamp(std::lround(static_cast<double>(premult / a) * 65535.0), 0L, 65535L));
        };
        const uint16_t outA = keepAlpha >= 0
            ? static_cast<uint16_t>(keepAlpha)
            : static_cast<uint16_t>(std::clamp(std::lround(static_cast<double>(a) * 65535.0), 0L, 65535L));
        return utils::ColorRGBA16{channel(r), channel(g), channel(b), outA};
    }

    // this + (other - this) * t
    [[nodiscard]] PremultColor towards(const PremultColor& other, float t) const noexcept {
        return {r + (other.r - r) * t, g + (other.g - g) * t, b + (other.b - b) * t, a + (other.a - a) * t};
    }
};

// O que o pincel carrega: um pedaço da imagem do tamanho do dab, não uma cor só.
//
// Cada célula é um deslocamento em relação ao centro do dab, e o pedaço anda junto com o dab: o que estava
// sob o pincel 30 px atrás aparece sob ele agora, com a forma que tinha (uma linha fina continua sendo uma
// linha, arrastada). Até 2026-10-02 o Borrar carregava a média de cor do dab, e a linha virava uma mancha
// opaca de cor média por cima dela.
//
// A célula ainda não carregada tem alfa -1; a primeira passagem do pincel por ela a preenche com o pixel.
class SmearPatch {
public:
    void reset() noexcept {
        m_cells.clear();
        m_radius = -1;
    }

    // Cabe um dab de `radius` px. O raio da célula cresce de 8 em 8 para a pressão não realocar a cada carimbo;
    // o que já foi carregado fica no lugar (mesmo deslocamento).
    void fit(double radius) {
        const int wanted = (static_cast<int>(std::ceil(radius)) + 3 + 7) / 8 * 8;
        if (wanted == m_radius) return;
        const int size = 2 * wanted + 1;
        std::vector<PremultColor> fresh(static_cast<size_t>(size) * static_cast<size_t>(size), PremultColor{0.0f, 0.0f, 0.0f, -1.0f});
        const int shared = std::min(wanted, m_radius);
        for (int dy = -shared; dy <= shared; ++dy) {
            for (int dx = -shared; dx <= shared; ++dx) {
                fresh[index(dx, dy, wanted)] = m_cells[index(dx, dy, m_radius)];
            }
        }
        m_cells = std::move(fresh);
        m_radius = wanted;
    }

    // A célula do deslocamento (dx, dy) em relação ao centro do dab; vale para dx, dy dentro do raio de `fit`.
    [[nodiscard]] PremultColor& at(int dx, int dy) noexcept { return m_cells[index(dx, dy, m_radius)]; }

private:
    [[nodiscard]] static size_t index(int dx, int dy, int radius) noexcept {
        const size_t size = static_cast<size_t>(2 * radius + 1);
        return static_cast<size_t>(dy + radius) * size + static_cast<size_t>(dx + radius);
    }

    std::vector<PremultColor> m_cells;
    int m_radius{-1};
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_SMEAR_PATCH_HPP
