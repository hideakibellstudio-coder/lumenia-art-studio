# `engine/` — pilar do motor nativo (C++20, ALADYN)

**Responsabilidade:** todo o processamento pesado de pintura: pixels em tiles, pincéis, composição de camadas, seleção, transformação, snap de guias, histórico e telemetria.

Pilar 3 do ARCcC multi-pilar (`ui/` → `bridge/` → `engine/`). Só C++ aqui dentro;
o Python nunca inclui nada desta pasta — fala com o motor pelo módulo
`aladyn_engine_native`, gerado pela `bridge/`.

## Porta de entrada

`boundary/public-api/PaintEngineFacade.hpp` (classe `PaintEngineFacade`): o único tipo que a `bridge/` deveria enxergar.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `boundary/` | Fronteira do motor: a fachada pública e os orquestradores que ela usa. |
| `core/` | Núcleo: um subpasta por domínio (pixels, pincel, documento, matemática...). |

## Regras

- Compilação fora da árvore (`python scripts/build_native.py`, objetos em `../build`); nenhum artefato aqui.
- Pasta nova ou `#include` novo entre pastas atualiza o README da pasta no mesmo commit (`python -m tests.arccc_package_docs`).
- Arquivo acima de 450 linhas é dividido por responsabilidade (mesmo teto do Python).

## Dívida conhecida (medida em 2026-09-24)

- Falta `infrastructure/` e `utils/` exigidos pelo ARCcC multi-pilar: `core/math` e `core/compression` fazem papel de utilitário e ficam como irmãos dos domínios.
- As pastas de `core/` se incluem entre irmãs e há ciclos de pasta (`canvas` ↔ `document`, `raster` ↔ `math`, `raster` ↔ `brush`, `raster` ↔ `canvas`, `raster` ↔ `color`); detalhe em cada README.
