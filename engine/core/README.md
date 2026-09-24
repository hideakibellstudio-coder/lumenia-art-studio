# `engine/core/` — núcleo do motor

**Responsabilidade:** os domínios do motor, cada um numa pasta: pixels e tiles, pincel, cor, documento e camadas, mini-motores de pincel, matemática, rasterização, traço, textura, compressão e telemetria.

## Porta de entrada

Não há porta única: quem usa o núcleo é `engine/boundary/public-api` (fachada e orquestradores).

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `brush/` | Perfil do pincel (parâmetros por motor) e mapeamento dinâmico pressão/velocidade → dab. |
| `canvas/` | Armazenamento de pixels: tiles com COW e compressão, grade, histórico por tile, disco de rascunho, mipmaps. |
| `color/` | Perfis de cor canônicos e espaço linear (Deep Color). |
| `compression/` | Codec LZ4 dos tiles. |
| `document/` | Camadas, pilha, mesclagem de camadas e compositor. |
| `engines/` | Mini-motores de pincel (lápis, nanquim, marcador, aquarela, óleo, borracha, desfoque, smudge). |
| `math/` | Geometria: pontos, retângulos, Bézier, viewport, simetria, snap de guias e de perspectiva. |
| `raster/` | Rasterização: dabs, interpolação, preenchimento, seleção, transformação. |
| `stroke/` | Entrada do traço: eventos de ponteiro, velocidade e estabilizador. |
| `telemetry/` | Medidas do traço em tempo real. |
| `texture/` | Texturas 2D e texturas procedurais (ponta e papel). |

## Regras

- Domínio novo vira pasta com README; `#include` entre pastas aparece no bloco `arccc:deps` do README de quem inclui.

## Dívida conhecida (medida em 2026-09-24)

Pelo ARCcC, pastas irmãs não se incluem diretamente; aqui 24 relações de inclusão são entre irmãs e 5 pares formam ciclo (medido em 2026-09-24). `math` e `compression` são utilitários (candidatos a `engine/utils/`).
