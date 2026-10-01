# `engine/core/selection/` — seleção

**Responsabilidade:** a máscara de seleção e o que produz ou modifica uma: varinha mágica, retângulo, elipse, polígono, suavização e Seleção → Modificar (expandir, contrair, suavizar borda).

## Porta de entrada

`SelectionMask.hpp` (máscara e `SelectionMode`); `SelectionEngine.hpp` para criar máscaras. Namespace `selection`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `SelectionMask.hpp` | Máscara de seleção e modos de combinação (nova, somar, subtrair, interseção). |
| `SelectionEngine.hpp` | Máscaras de varinha, retângulo, elipse, polígono e suavização (declaração). |
| `SelectionEngine.cpp` | Varinha mágica (global e contígua). |
| `SelectionShapeMasks.cpp` | Máscaras geométricas (separadas em 2026-09-22, teto de 450 linhas); o laço tem suavização por cobertura de área desde 2026-09-25; retângulo e elipse contam em 64 bits, e qualquer coordenada que o `int` carrega é recusada ou recortada, nunca derruba o processo (`tests/test_selection_extreme_coordinates.py`). |
| `SelectionMorphology.hpp` | Seleção → Modificar: expandir, contrair, suavizar borda (declaração). |
| `SelectionMorphology.cpp` | Implementação com transformada de distância euclidiana exata. |

## Regras

- Lê pixels de `canvas/` (varinha) e não escreve pixel nenhum: quem pinta respeitando a seleção é `raster/` (`PixelContext`).
- Saiu de `raster/` em 2026-09-25 para o histórico guardar seleções sem depender da rasterização.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/utils`
<!-- /arccc:deps -->
