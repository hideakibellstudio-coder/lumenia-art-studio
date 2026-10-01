# `engine/core/raster/` — rasterização

**Responsabilidade:** transformar pincelada e ferramentas em pixels: a interpolação dos dabs, a deposição com AVX2, o balde e a transformação de camada.

## Porta de entrada

`DabRenderer.hpp` para quem pinta e `DabFootprint.hpp` para quem escreve um motor de pincel novo; `TransformEngine.hpp` para transformar; `FloodFill.hpp` para o balde.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `DabInterpolator.hpp` | Interpolação de dabs entre amostras (linear e spline Catmull-Rom) (declaração). |
| `DabInterpolator.cpp` | Implementação. |
| `DabRenderer.hpp` | Desenha um dab numa `TileGrid` (declaração). |
| `DabRenderer.cpp` | O pincel padrão: quanta tinta cada pixel recebe (`DabInk`, com o caminho rápido sem textura) e como ela entra no destino (normal, multiplicar, aditivo). |
| `DabFootprint.hpp` | A pegada de um dab, comum aos nove motores de pincel: os tiles que ele toca, a geometria de cada pixel (círculo ou elipse girada) e o laço paralelo; o motor traz só o `kernel` que decide a cor de um pixel (declaração e o laço, em modelo). |
| `DabFootprint.cpp` | O construtor: caixa envolvente, rotação e descarte dos tiles que o círculo não toca. |
| `PixelPermission.hpp` | O quanto a seleção e a camada-base de um recorte deixam um pixel ser pintado (Alpha Lock é regra de cada motor, não daqui). |
| `StraightOver.hpp` | Alfa over em 8 bits sem gama linear, o depósito comum de Lápis, Caneta e Borrar. |
| `TipShape.hpp` | O alfa da forma da ponta (textura de forma ou disco com dureza e meio pixel de anti-aliasing): a forma do pincel padrão e da Borracha. |
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
