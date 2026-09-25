#ifndef ALADYN_ENGINE_SELECTION_MORPHOLOGY_HPP
#define ALADYN_ENGINE_SELECTION_MORPHOLOGY_HPP

// Seleção -> Modificar (Expandir, Contrair, Suavizar Borda).
//
// Expandir/Contrair usam a transformada de distância euclidiana exata
// (Felzenszwalb & Huttenlocher, 2012): custo O(pixels) independente do raio,
// com borda antisserrilhada. A borda da seleção é a linha de 50% (>= 128).
// Pixels suaves que já existiam são preservados (max ao expandir, min ao
// contrair), então uma seleção com feather continua suave depois.
//
// Suavizar = desfoque gaussiano da máscara com sigma = raio / 2: a transição
// ocupa ~raio pixels para cada lado da borda. Raios pequenos usam o kernel
// gaussiano direto; a partir de sigma 2, três passadas de caixa (aproximação
// padrão de gaussiana, O(pixels) por passada).
//
// Borda da tela: fora da tela conta como "igual à vizinhança" -- Selecionar
// Tudo continua tudo depois de Contrair ou Suavizar (padrão do Photoshop com
// "aplicar nos limites da tela" desligado).

#include "SelectionMask.hpp"

namespace aladyn::engine::selection::SelectionMorphology {

/// Raio máximo aceito (px). Valores acima são limitados.
constexpr int kMaxRadiusPx = 500;

/// Devolvem false quando não há seleção ou o raio é <= 0 (nada muda).
bool expand(selection::SelectionMask& mask, int radiusPx);
bool contract(selection::SelectionMask& mask, int radiusPx);
bool feather(selection::SelectionMask& mask, int radiusPx);

} // namespace aladyn::engine::selection::SelectionMorphology

#endif // ALADYN_ENGINE_SELECTION_MORPHOLOGY_HPP
