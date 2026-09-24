# `engine/boundary/` — fronteira do motor

**Responsabilidade:** o que o motor expõe para a ponte: a `PaintEngineFacade` e, por trás dela, os orquestradores que traduzem uma chamada pública em operações do núcleo.

## Porta de entrada

`public-api/PaintEngineFacade.hpp`.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `public-api/` | Fachada pública do motor e seus orquestradores internos. |

## Regras

- A fronteira traduz e coordena; regra de pintura, composição ou geometria mora em `engine/core/`.
