# `engine/core/raster/` — rasterização

**Responsabilidade:** transformar pincelada e ferramentas em pixels: o dab e sua interpolação, a deposição com AVX2, o balde, a seleção (máscaras e morfologia) e a transformação de camada.

## Porta de entrada

`Dab.hpp` (tipo do dab e da cor) para quem pinta; `SelectionMask.hpp` para quem seleciona; `TransformEngine.hpp` para transformar.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Dab.hpp` | `Dab`, `ColorRGBA` e modos de deposição. |
| `DabInterpolator.hpp` | Interpolação de dabs entre amostras (linear e spline Catmull-Rom) (declaração). |
| `DabInterpolator.cpp` | Implementação. |
| `DabRenderer.hpp` | Desenha um dab numa `TileGrid` (declaração). |
| `DabRenderer.cpp` | Implementação (achatamento, rotação, caixa envolvente). |
| `SimdSpanBlender.hpp` | Mesclagem de trechos contínuos com AVX2 (e caminho escalar). |
| `LargeBrushOptimizer.hpp` | Espaçamento adaptativo para pincéis grandes (declaração). |
| `LargeBrushOptimizer.cpp` | Implementação. |
| `PixelContext.hpp` | Restrições de deposição por pixel (máscara, Alpha Lock, recorte). |
| `FloodFill.hpp` | Balde de tinta por spans (declaração). |
| `FloodFill.cpp` | Implementação (tolerância, contíguo, expansão, fechar vãos). |
| `SelectionMask.hpp` | Máscara de seleção e modos de combinação (nova, somar, subtrair, interseção). |
| `SelectionEngine.hpp` | Máscaras de varinha, retângulo, elipse, polígono e suavização (declaração). |
| `SelectionEngine.cpp` | Varinha mágica (global e contígua). |
| `SelectionShapeMasks.cpp` | Máscaras geométricas (separadas em 2026-09-22, teto de 450 linhas). |
| `SelectionMorphology.hpp` | Seleção → Modificar: expandir, contrair, suavizar borda (declaração). |
| `SelectionMorphology.cpp` | Implementação com transformada de distância euclidiana exata. |
| `TransformEngine.hpp` | Transformar livre e distorcer, espelhar e girar a camada (declaração, `TransformState`). |
| `TransformEngine.cpp` | Amostragem e execução da transformação. |
| `TransformEngineCommit.cpp` | Confirmar e cancelar a transformação (separado em 2026-09-22). |
| `TransformEngineDistort.cpp` | Distorcer por homografia (2026-09-23). |

## Regras

- Pixel escrito aqui vai para uma `TileGrid` e passa pelo histórico antes (`canvas/TileUndoManager`).

## Dívida conhecida (medida em 2026-09-24)

- Pasta que mais inclui irmãs (`brush`, `canvas`, `color`, `document`, `math`) e forma ciclo com quatro delas.
- `SelectionMorphology.cpp` tem tipos e funções com nome em português (`Linha`, `Desfoque`, `roiAoRedor`, `varrerDistancias`, `paraByte`), contra a regra de idioma do ARCcC (seção 14).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/brush`
- `engine/core/canvas`
- `engine/core/color`
- `engine/core/document`
- `engine/core/math`
- `engine/core/raster/transform`
<!-- /arccc:deps -->
