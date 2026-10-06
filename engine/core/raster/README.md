# `engine/core/raster/` — rasterização

**Responsabilidade:** transformar pincelada e ferramentas em pixels: a interpolação dos dabs, a deposição com AVX2, o balde e a transformação de camada.

## Porta de entrada

`DabRenderer.hpp` para quem pinta e `DabFootprint.hpp` para quem escreve um motor de pincel novo; `TransformEngine.hpp` para transformar; `FloodFill.hpp` para o balde.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `DabInterpolator.hpp` | Interpolação de dabs entre amostras (linear e spline Catmull-Rom) (declaração). O ângulo do dab é o da ponta; a direção do traço só entra com "seguir o traço". |
| `DabInterpolator.cpp` | Implementação. |
| `DabRenderer.hpp` | Desenha um dab numa `TileGrid` (declaração). |
| `DabRenderer.cpp` | O pincel padrão: quanta tinta cada pixel recebe (`DabInk`, com o caminho rápido sem textura) e como ela entra no destino (normal, multiplicar, aditivo). |
| `DabFootprint.hpp` | A pegada de um dab, comum aos nove motores de pincel (e `tipAspect`, a proporção da ponta do carimbo, que os motores leem em vez da fixa do perfil): os tiles que ele toca, a geometria de cada pixel (círculo ou elipse girada) e o laço paralelo; o motor traz só o `kernel` que decide a cor de um pixel (declaração e o laço, em modelo). |
| `DabFootprint.cpp` | O construtor: caixa envolvente, rotação e descarte dos tiles que o círculo não toca. |
| `StrokeOpacityMix.hpp` | Opacidade do traço como teto: com opacidade < 100% o motor pinta numa cópia de trabalho da camada e a camada recebe a mistura base <-> trabalho (declaração). |
| `StrokeOpacityMix.cpp` | Cópia Copy-on-Write da base e do trabalho, e a mistura em alfa pré-multiplicado, arredondada, só dos tiles que o traço mudou. |
| `StrokeInkLedger.hpp` | A memória de um traço, pixel a pixel (a base antes do primeiro carimbo, a cobertura alcançada e a luz já posta): com ela a tinta translúcida do Marcador e da Aquarela tem a cor da tinta uma vez só, em vez de se multiplicar a cada carimbo, e o relevo do Óleo não acumula brilho (declaração). |
| `StrokeInkLedger.cpp` | Planos de 192 KB por tile tocado, criados em série antes do laço paralelo do carimbo e descartados ao fim do traço. |
| `PixelPermission.hpp` | O quanto a seleção e a camada-base de um recorte deixam um pixel ser pintado (Alpha Lock é regra de cada motor, não daqui). |
| `StraightOver.hpp` | Alfa over em 8 bits sem gama linear, o depósito comum de Lápis, Caneta e Borrar. |
| `TipShape.hpp` | O alfa da forma da ponta (textura de forma ou disco com dureza e meio pixel de anti-aliasing): a forma do pincel padrão e da Borracha. |
| `BrushGrain.hpp` | O grão do pincel (a textura de altura) lido num pixel, num lugar só para o Pincel e o Lápis: **Móvel**, preso ao carimbo (o de sempre), ou **Fixo**, preso à tela como o grão do papel. Com os carimbos se sobrepondo o grão móvel se apaga num traço; o fixo mantém o dente. Os presets de grafite continuam no Móvel: nos 2H/HB/6B o desvio do alfa quase não muda entre os modos (6B a 0,6 de pressão: 88,7 móvel contra 86,4 fixo) porque o grão do papel, que já é fixo, domina; o Fixo é opção do artista. |
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
