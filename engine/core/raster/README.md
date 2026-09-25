# `engine/core/raster/` — rasterização

**Responsabilidade:** transformar pincelada e ferramentas em pixels: a interpolação dos dabs, a deposição com AVX2, o balde e a transformação de camada.

## Porta de entrada

`DabRenderer.hpp` para quem pinta; `TransformEngine.hpp` para transformar; `FloodFill.hpp` para o balde.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `DabInterpolator.hpp` | Interpolação de dabs entre amostras (linear e spline Catmull-Rom) (declaração). |
| `DabInterpolator.cpp` | Implementação. |
| `DabRenderer.hpp` | Desenha um dab numa `TileGrid` (declaração). |
| `DabRenderer.cpp` | Implementação (achatamento, rotação, caixa envolvente). |
| `SimdSpanBlender.hpp` | Mesclagem de trechos contínuos com AVX2 (e caminho escalar). |
| `LargeBrushOptimizer.hpp` | Espaçamento adaptativo para pincéis grandes e a queda suave (`smoothHermite`) (declaração). |
| `LargeBrushOptimizer.cpp` | Implementação. |
| `PixelContext.hpp` | Restrições de deposição por pixel (máscara de seleção, Alpha Lock, recorte). |
| `FloodFill.hpp` | Balde de tinta por spans (declaração). |
| `FloodFill.cpp` | Implementação (tolerância, contíguo, expansão, fechar vãos). |
| `TransformEngine.hpp` | Transformar livre e distorcer, espelhar e girar a camada (declaração, `TransformState`). |
| `TransformEngine.cpp` | Amostragem e execução da transformação. |
| `TransformEngineCommit.cpp` | Confirmar e cancelar a transformação (separado em 2026-09-22). |
| `TransformEngineDistort.cpp` | Distorcer por homografia (2026-09-23). |

| Pasta | Responsabilidade |
|---|---|
| `transform/` | Núcleo da transformação: amostradores, homografia e composição por mapeamento inverso. |

## Regras

- Pixel escrito aqui vai para uma `TileGrid` e passa pelo histórico antes (`history::TileUndoManager`).
- O `Dab` e a `ColorRGBA` moram em `engine/utils`; a seleção em `engine/core/selection` (saíram daqui em 2026-09-25 e desfizeram os ciclos com `math`, `brush`, `color` e `canvas`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/brush`
- `engine/core/canvas`
- `engine/core/color`
- `engine/core/document`
- `engine/core/history`
- `engine/core/raster/transform`
- `engine/core/selection`
- `engine/utils`
<!-- /arccc:deps -->
