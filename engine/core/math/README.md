# `engine/core/math/` — matemática e geometria

**Responsabilidade:** tipos geométricos e cálculos puros: pontos, retângulos, Bézier, transformação de viewport, simetria e o snap de guias (reto, curvo, curvilíneo 6P e perspectiva).

## Porta de entrada

Não há porta única; os tipos básicos são `Point2D.hpp` e `Rect2D.hpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Point2D.hpp` | Ponto 2D com operações vetoriais. |
| `Rect2D.hpp` | Retângulo alinhado aos eixos. |
| `MathUtils.hpp` | Funções utilitárias (clamp, interpolação). |
| `BezierCurve.hpp` | Curva Bézier com presets e tabela (LUT) para curvas de pressão (declaração). |
| `BezierCurve.cpp` | Implementação. |
| `ViewportTransform.hpp` | Transformação canvas ↔ tela (zoom, pan, rotação, espelho) (declaração). |
| `ViewportTransform.cpp` | Implementação das matrizes. |
| `SymmetryEngine.hpp` | Modos e configuração de simetria; replica um dab nos eixos (declaração). |
| `SymmetryEngine.cpp` | Implementação. |
| `GuideSnapEngine.hpp` | Tipos e configuração de guia (`GuideType`, `GuideConfig`) e snap de réguas (declaração). |
| `GuideSnapEngine.cpp` | Snap de régua reta e curva. |
| `CurvilinearSnapEngine.hpp` | Curvas candidatas da perspectiva curvilínea 6P (declaração). |
| `CurvilinearSnapEngine.cpp` | Projeção e snap curvilíneo. |
| `SnapCandidate.hpp` | Trilha candidata genérica (reta ou círculo) (declaração). |
| `SnapCandidate.cpp` | Projeção num candidato. |
| `SnapLockStateMachine.hpp` | Máquina de estados de trava do snap (atração, compromisso, soltura) (declaração). |
| `SnapLockStateMachine.cpp` | Implementação. |
| `TrajectoryEstimator.hpp` | Direção e confiança da trajetória recente do traço (declaração). |
| `TrajectoryEstimator.cpp` | Implementação. |

## Regras

- Lei do rio nº 2: snap, simetria e transformação existem aqui; a UI não reimplementa em Python.

## Dívida conhecida (medida em 2026-09-24)

`SymmetryEngine.hpp` inclui `raster/Dab.hpp`: a matemática depende da rasterização (e `raster/` depende daqui), ciclo `math` ↔ `raster`. Pelo ARCcC esta pasta seria utilitário (`engine/utils/`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/raster`
<!-- /arccc:deps -->
