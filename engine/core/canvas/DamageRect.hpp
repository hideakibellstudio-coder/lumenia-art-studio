#ifndef ALADYN_ENGINE_DAMAGE_RECT_HPP
#define ALADYN_ENGINE_DAMAGE_RECT_HPP

#include <algorithm>

namespace aladyn::engine::canvas {

// A união dos pixels que mudaram desde a última vez que alguém olhou: um
// retângulo [x0, x1) x [y0, y1), ou vazio. Quem escreve soma o que escreveu; quem
// guarda uma cópia derivada (a pirâmide de LOD) lê, refaz só isso e limpa.
//
// A união é a caixa que envolve os retângulos somados: pode cobrir pixels que não
// mudaram, nunca deixa de cobrir um que mudou. Errar para mais custa um pouco de
// trabalho; errar para menos mostraria um pixel velho na tela.
class DamageRect {
public:
    // Soma [x0, x1) x [y0, y1). Retângulo vazio ou invertido não soma nada.
    void add(int x0, int y0, int x1, int y1) noexcept {
        if (x0 >= x1 || y0 >= y1) return;
        if (empty()) {
            m_x0 = x0; m_y0 = y0; m_x1 = x1; m_y1 = y1;
            return;
        }
        m_x0 = std::min(m_x0, x0);
        m_y0 = std::min(m_y0, y0);
        m_x1 = std::max(m_x1, x1);
        m_y1 = std::max(m_y1, y1);
    }

    [[nodiscard]] bool empty() const noexcept { return m_x0 >= m_x1 || m_y0 >= m_y1; }
    [[nodiscard]] int x0() const noexcept { return m_x0; }
    [[nodiscard]] int y0() const noexcept { return m_y0; }
    [[nodiscard]] int x1() const noexcept { return m_x1; }
    [[nodiscard]] int y1() const noexcept { return m_y1; }

    void clear() noexcept { m_x0 = m_y0 = m_x1 = m_y1 = 0; }

private:
    int m_x0{0};
    int m_y0{0};
    int m_x1{0};
    int m_y1{0};
};

} // namespace aladyn::engine::canvas

#endif // ALADYN_ENGINE_DAMAGE_RECT_HPP
