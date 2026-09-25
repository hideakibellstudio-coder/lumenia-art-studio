# `engine/core/color/` — cor

**Responsabilidade:** os perfis de cor canônicos que UI, rasterizador e arquivo `.lmn` compartilham, a simulação de impressão (CMYK), as tabelas do espaço linear usado pelo Deep Color e a conversão RGB ↔ HSV.

## Porta de entrada

`ColorProfile.hpp` (`ColorProfileType`, `ColorProfileManager`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `ColorProfile.hpp` | Ids canônicos de perfil (0–13), nomes e validação (declaração). |
| `ColorProfile.cpp` | Conversões por perfil, incluindo a simulação física de CMYK (ganho de ponto, limite de tinta). |
| `LinearColorSpace.hpp` | Tabelas de transferência sRGB ↔ linear (caminho rápido de 12 bits e caminho de precisão estendida). |
| `HsvConversion.hpp` | RGB ↔ HSV em float (usado pelo filtro Matiz/Saturação); saiu de `document/blending` em 2026-09-25. |

## Regras

- Id de perfil novo precisa existir aqui, no catálogo Python (`ui/core/color`) e na validação do `.lmn` (`ui/core/document/schema.py`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/utils`
<!-- /arccc:deps -->
