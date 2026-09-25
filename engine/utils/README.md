# `engine/utils/` — tipos de valor do motor

**Responsabilidade:** os tipos de dado puro que todas as camadas do motor usam — ponto, retângulo, cor RGBA8, o dab (a unidade de tinta depositada) — e funções numéricas (clamp, interpolação).

## Porta de entrada

Não há porta única: cada tipo tem o seu cabeçalho (`Point2D.hpp`, `Rect2D.hpp`, `ColorRGBA.hpp`, `Dab.hpp`, `MathUtils.hpp`). Namespace `aladyn::engine::utils`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Point2D.hpp` | Ponto 2D com operações vetoriais. |
| `Rect2D.hpp` | Retângulo alinhado aos eixos. |
| `ColorRGBA.hpp` | Cor RGBA8 (sRGB, alfa reto): o tipo de pixel do motor inteiro. |
| `Dab.hpp` | `Dab` (posição, raio, opacidade, pressão, ângulo, cor, achatamento) e `DabBlendMode`. |
| `MathUtils.hpp` | Funções numéricas: clamp, lerp, smoothstep. |

## Regras

- Camada mais baixa do motor: só inclui a biblioteca padrão.
- Só tipo de valor e função pura; algoritmo com regra de pintura mora no módulo de `engine/core/` que é dono dele.
- Saíram de `core/math` e `core/raster` em 2026-09-25: eram usados por quase todos os módulos e criavam ciclos de pasta (`raster` ↔ `math`/`brush`/`color`/`canvas`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
