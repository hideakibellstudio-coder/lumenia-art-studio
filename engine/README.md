# `engine/` — pilar do motor nativo (C++20, ALADYN)

**Responsabilidade:** todo o processamento pesado de pintura: pixels em tiles, pincéis, composição de camadas, seleção, transformação, snap de guias, histórico e telemetria.

Pilar 3 do ARCcC multi-pilar (`ui/` → `bridge/` → `engine/`). Só C++ aqui dentro;
o Python nunca inclui nada desta pasta — fala com o motor pelo módulo
`aladyn_engine_native`, gerado pela `bridge/`.

## Porta de entrada

`boundary/public-api/AladynEngine.hpp`: o único arquivo que a `bridge/` inclui (a `PaintEngineFacade`, as prévias do pincel e os tipos de valor expostos ao Python).

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `boundary/` | Fronteira: a API pública (`public-api/`) e os orquestradores que ela usa (`orchestrator/`). |
| `core/` | Núcleo: uma pasta por domínio (pixels, seleção, pincel, documento, histórico, rasterização...). |
| `infrastructure/` | Serviços técnicos sem regra de pintura: compressão LZ4, disco de rascunho, telemetria. |
| `utils/` | Tipos de valor usados pelo motor inteiro: ponto, retângulo, cor, dab e funções numéricas. |

## Camadas

De baixo para cima; uma pasta só inclui as camadas abaixo dela (conferido por `tests/test_arccc_cxx_layers.py`):

1. `utils/`
2. `infrastructure/` (`compression`, `storage`, `telemetry`, que não se incluem entre si)
3. `core/`, nesta ordem: `math` → `texture` → `color` → `stroke` → `canvas` → `selection` → `brush` → `document` → `history` → `raster` → `engines`
4. `boundary/orchestrator/`
5. `boundary/public-api/`
6. `bridge/`, só por `public-api/AladynEngine.hpp`

Subpasta nunca inclui a pasta-mãe: a mãe usa a filha, e o que as duas
compartilham mora na filha (ex.: `document/blending/LayerBlendMode.hpp`).

## Regras

- Namespace acompanha a pasta: `aladyn::engine::<pasta>` (`utils::Point2D`, `selection::SelectionMask`, `history::TileUndoManager`, `storage::ScratchDiskManager`); subpasta vira namespace aninhado (`document::filters`, `boundary::orchestrator`). A API pública usa `aladyn::engine::boundary`.
- Compilação fora da árvore (`python scripts/build_native.py`, objetos em `../build`); nenhum artefato aqui. Arquivo `.cpp` novo entra na lista de `setup.py`.
- Pasta nova ou `#include` novo entre pastas atualiza o README da pasta no mesmo commit (`python -m tests.arccc_package_docs`).
- Arquivo acima de 450 linhas é dividido por responsabilidade (mesmo teto do Python).
