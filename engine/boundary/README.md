# `engine/boundary/` — fronteira do motor

**Responsabilidade:** o que o motor expõe para a ponte (`public-api/`) e, por trás dele, os orquestradores que traduzem uma chamada pública em operações do núcleo (`orchestrator/`).

## Porta de entrada

`public-api/AladynEngine.hpp`.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `public-api/` | Contrato público: `AladynEngine.hpp` (porta única da ponte), a `PaintEngineFacade` e as prévias do pincel. |
| `orchestrator/` | Um orquestrador por assunto (traço, camadas, seleção, transformação, snap, memória, exportação...). |

## Regras

- A fronteira traduz e coordena; regra de pintura, composição ou geometria mora em `engine/core/`.
- `public-api/` usa `orchestrator/`, nunca o contrário (`tests/test_arccc_cxx_layers.py`); é o par fronteira/pública → orquestrador da seção 3.1 do ARCcC.
