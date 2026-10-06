#ifndef ALADYN_ENGINE_OIL_BRISTLES_HPP
#define ALADYN_ENGINE_OIL_BRISTLES_HPP

#include "SmearPatch.hpp"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

namespace aladyn::engine::engines {

// Uma cerda do pincel de óleo: carrega tinta, tem uma altura fixa e guarda mais ou menos tinta que as vizinhas.
struct Bristle {
    PremultColor paint{0.0f, 0.0f, 0.0f, -1.0f};  // a cor carregada; o alfa é a CARGA (1 = cheia, 0 = seca); -1: ainda sem tinta
    float height{0.5f};                           // 0..1, quanto a ponta sobressai AGORA: a base mais a oscilação ao longo do traço
    float pattern{0.5f};                          // 0..1, a altura base da cerda, fixa no traço (cerdas vizinhas se parecem)
    float capacity{1.0f};                         // 0,6..1,4, quanto de tinta guarda: a que guarda menos seca primeiro
    uint32_t streak{0};                           // semente da oscilação desta cerda ao longo do traço
};

// Número pseudoaleatório em [0, 1) que só depende de (semente, índice): o mesmo traço sai igual em qualquer
// máquina e a pré-visualização tem as mesmas cerdas do traço final. Só aritmética inteira.
[[nodiscard]] inline float bristleNoise(uint32_t seed, uint32_t index) noexcept {
    uint32_t h = seed ^ (index * 0x9E3779B9u);
    h ^= h >> 16;
    h *= 0x7FEB352Du;
    h ^= h >> 15;
    h *= 0x846CA68Bu;
    h ^= h >> 16;
    return static_cast<float>(h >> 8) * (1.0f / 16777216.0f);
}

// Ruído suave de uma dimensão em [0, 1): interpola linearmente suavizado entre valores aleatórios nos inteiros.
[[nodiscard]] inline float smoothNoise(uint32_t seed, float x) noexcept {
    const float floored = std::floor(x);
    const float t = x - floored;
    const uint32_t cell = static_cast<uint32_t>(static_cast<int32_t>(floored));
    const float a = bristleNoise(seed, cell);
    const float b = bristleNoise(seed, cell + 1u);
    return a + (b - a) * (t * t * (3.0f - 2.0f * t));
}

// O feixe de cerdas do pincel: N cerdas lado a lado através do pincel, de um lado ao outro.
//
// Até 2026-10-02 o Óleo não tinha cerdas: a "ranhura" era uma senoidal do pixel em coordenadas do carimbo, que
// não acompanhava o traço, e a tinta era a cor do pincel, sempre cheia, sem lembrar de nada entre carimbos.
// Aqui cada cerda lembra o que carrega (cor e carga): ela esgota, pega cor do que pisa e deixa riscos paralelos
// ao movimento porque a cerda de um lado do traço continua sendo a mesma cerda carimbo após carimbo.
//
// O feixe é só leitura dentro do laço paralelo de pixels; quem o atualiza é o motor, em série, uma vez por carimbo.
class BristleBundle {
public:
    // Onde uma posição através do pincel cai no feixe: entre as cerdas `lo` e `hi`, a `frac` do caminho.
    struct Place {
        int lo;
        int hi;
        float frac;
    };

    void reset() noexcept { m_bristles.clear(); }
    [[nodiscard]] bool empty() const noexcept { return m_bristles.empty(); }
    [[nodiscard]] int count() const noexcept { return static_cast<int>(m_bristles.size()); }

    // Cria `count` cerdas sem tinta; altura base e capacidade vêm da semente. As alturas formam tufos: metade é
    // ruído de cada cerda e metade é um ruído suave que varia a cada ~3 cerdas.
    void load(int count, uint32_t seed) {
        m_bristles.assign(static_cast<std::size_t>(std::max(2, count)), Bristle{});
        for (std::size_t i = 0; i < m_bristles.size(); ++i) {
            const uint32_t index = static_cast<uint32_t>(i);
            Bristle& bristle = m_bristles[i];
            bristle.pattern = 0.5f * bristleNoise(seed, index) + 0.5f * smoothNoise(seed ^ 0x5BD1E995u, static_cast<float>(i) / 3.0f);
            bristle.height = bristle.pattern;
            bristle.capacity = 0.6f + 0.8f * bristleNoise(seed ^ 0xA5A5A5A5u, index);
            bristle.streak = seed ^ (index * 0x85EBCA6Bu);
        }
    }

    // A altura de cada cerda oscila ao longo do traço (`travel` em diâmetros): os riscos nascem, engrossam e somem
    // em vez de correrem iguais de ponta a ponta.
    void sway(double travel) noexcept {
        for (Bristle& bristle : m_bristles) {
            const float wobble = smoothNoise(bristle.streak, static_cast<float>(travel) * 2.2f) - 0.5f;
            bristle.height = std::clamp(bristle.pattern + 0.8f * wobble, 0.0f, 1.0f);
        }
    }

    [[nodiscard]] Bristle& at(int index) noexcept { return m_bristles[static_cast<std::size_t>(index)]; }
    [[nodiscard]] const Bristle& at(int index) const noexcept { return m_bristles[static_cast<std::size_t>(index)]; }

    // `across` vai de -1 (um lado do pincel) a +1 (o outro). As cerdas ficam nos centros das N faixas iguais.
    [[nodiscard]] Place place(double across) const noexcept {
        const int last = count() - 1;
        const double position = std::clamp((across + 1.0) * 0.5 * count() - 0.5, 0.0, static_cast<double>(last));
        const int lo = std::min(static_cast<int>(position), last - 1);
        return {lo, lo + 1, static_cast<float>(std::clamp(position - lo, 0.0, 1.0))};
    }

private:
    std::vector<Bristle> m_bristles;
};

} // namespace aladyn::engine::engines

#endif // ALADYN_ENGINE_OIL_BRISTLES_HPP
