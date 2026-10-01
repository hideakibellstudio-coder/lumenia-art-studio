# `engine/core/document/blending/` — mesclagem de pixel

**Responsabilidade:** a matemática de mesclar um pixel sobre outro (alpha over e os 13 modos de mesclagem de camada).

## Porta de entrada

`BlendEquations.hpp` (`blendPixel`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `LayerBlendMode.hpp` | Enum dos modos de mesclagem; espelhado 1:1 por `ui/core/document/layer_blend_mode.py` e reexportado como `document::LayerBlendMode`. |
| `BlendEquations.hpp` | `blendPixel` escolhe o caminho (atalhos exatos do Normal, Erase, Normal em linear ou sRGB, modos separáveis) e cada caminho é uma função com nome em `detail` (CCN máximo 13; era 32 numa função só). |

## Regras

- Não inclui a pasta-mãe (`document/`): trabalha com pixel e modo, não com camada.
- Modo novo: valor no enum, caso em `detail::separableBlend` (uma equação de canal; o modo é escolhido uma vez por pixel, não por canal: escolher por canal custou 30% no Darken), espelho em Python e `tests/test_layer_blend_mode_contract.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/color`
- `engine/utils`
<!-- /arccc:deps -->
