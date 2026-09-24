# `engine/core/color/` — perfis de cor

**Responsabilidade:** os perfis de cor canônicos que UI, rasterizador e arquivo `.lmn` compartilham, a simulação de impressão (CMYK) e as tabelas do espaço linear usado pelo Deep Color.

## Porta de entrada

`ColorProfile.hpp` (`ColorProfileType`, `ColorProfileManager`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `ColorProfile.hpp` | Ids canônicos de perfil (0–13), nomes e validação (declaração). |
| `ColorProfile.cpp` | Conversões por perfil, incluindo a simulação física de CMYK (ganho de ponto, limite de tinta). |
| `LinearColorSpace.hpp` | Tabelas de transferência sRGB ↔ linear (caminho rápido de 12 bits e caminho de precisão estendida). |

## Regras

- Id de perfil novo precisa existir aqui, no catálogo Python (`ui/core/color`) e na validação do `.lmn` (`ui/core/document/schema.py`).

## Dívida conhecida (medida em 2026-09-24)

Inclui `raster/Dab.hpp` (tipo de cor) e `raster/` inclui esta pasta: ciclo `color` ↔ `raster`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/raster`
<!-- /arccc:deps -->
