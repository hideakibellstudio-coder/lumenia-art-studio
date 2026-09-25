# `engine/core/brush/` — perfil e dinâmica do pincel

**Responsabilidade:** o que descreve um pincel (motor, ponta, curvas, texturas, parâmetros de cada mini-motor) e como pressão e velocidade viram tamanho, opacidade e dispersão de cada dab.

## Porta de entrada

`BrushProfile.hpp` (struct do perfil e enum `EngineType`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `BrushProfile.hpp` | Perfil completo do pincel: `EngineType`, parâmetros de cada motor (`PencilParams`, `InkerParams`, `MarkerParams`, `BlurParams`, `SmudgeParams`...), curvas e texturas. |
| `BrushTip.hpp` | Geometria da ponta: ângulo, achatamento, seguir o traço e jitters. |
| `DynamicMapper.hpp` | `DynamicMapper`/`MappedBrushState`: estado do dab a partir de pressão, velocidade e perfil. |
| `DynamicMapper.cpp` | Implementação do mapeamento dinâmico e da dispersão (scatter). |

## Regras

- Parâmetro novo de pincel entra no perfil aqui, é lido pelo mini-motor em `engines/` e chega da UI pela tabela `ui/infrastructure/bridge_client/brush_param_table.py`.

## Dívida conhecida (medida em 2026-09-24)

`raster/` inclui arquivos daqui e esta pasta inclui `raster/Dab.hpp`: ciclo de pasta `brush` ↔ `raster`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/math`
- `engine/core/raster`
- `engine/core/texture`
<!-- /arccc:deps -->
