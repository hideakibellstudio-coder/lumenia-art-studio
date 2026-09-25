# `engine/core/` — núcleo do motor

**Responsabilidade:** os domínios do motor, cada um numa pasta: matemática de guias e viewport, texturas, cor, entrada do traço, armazenamento de pixels, seleção, pincel, documento e camadas, histórico, rasterização e os mini-motores de pincel.

## Porta de entrada

Não há porta única: quem usa o núcleo é `engine/boundary/` (orquestradores e API pública).

## Conteúdo

Na ordem das camadas, de baixo para cima (cada módulo só inclui os anteriores, `engine/utils` e `engine/infrastructure`):

| Pasta | Responsabilidade |
|---|---|
| `math/` | Bézier, viewport, simetria, snap de guias e de perspectiva, trajetória. |
| `texture/` | Texturas 2D e procedurais (ponta e papel). |
| `color/` | Perfis de cor canônicos, espaço linear (Deep Color) e conversão HSV. |
| `stroke/` | Entrada do traço: eventos de ponteiro, velocidade e estabilizador. |
| `canvas/` | Armazenamento de pixels: tiles com COW e compressão, grade, mipmaps, textura do papel. |
| `selection/` | Máscara de seleção, varinha e formas, morfologia (expandir, contrair, suavizar). |
| `brush/` | Perfil do pincel e mapeamento dinâmico pressão/velocidade → dab. |
| `document/` | Camadas, pilha, mesclagem, filtros e compositor. |
| `history/` | Desfazer/refazer por tile e por estrutura, com paginação em disco. |
| `raster/` | Rasterização: dabs, interpolação, deposição, balde, transformação. |
| `engines/` | Mini-motores de pincel (lápis, nanquim, marcador, aquarela, óleo, borracha, desfoque, smudge). |

## Regras

- Módulo novo vira pasta com README e entra em `CORE_ORDER` de `tests/test_arccc_cxx_layers.py` no lugar que as dependências dele pedem.
- `#include` entre módulos só para baixo na ordem acima; `#include` entre pastas aparece no bloco `arccc:deps` do README de quem inclui.

## Decisão registrada (2026-09-25)

O ARCcC proíbe irmãs se incluírem diretamente. Aqui 19 relações de inclusão
são entre módulos irmãos (ex.: `raster` → `canvas`), todas no sentido da ordem
acima e sem ciclo: a ordem declarada é o contrato entre eles. Antes eram 23
entre módulos de `core/`, com 9 pares de pastas em ciclo no motor.
