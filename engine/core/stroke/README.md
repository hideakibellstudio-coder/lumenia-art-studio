# `engine/core/stroke/` — entrada do traço

**Responsabilidade:** o que chega da mesa ou do mouse antes de virar dab: o evento de ponteiro, a velocidade e o estabilizador.

## Porta de entrada

`PointerEvent.hpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `PointerEvent.hpp` | Evento de ponteiro (posição, pressão, inclinação, tempo, tipo). |
| `VelocityTracker.hpp` | Velocidade suavizada do traço (declaração). |
| `VelocityTracker.cpp` | Implementação com piso temporal contra rajadas da fila do sistema. |
| `DynamicStabilizer.hpp` | Estabilizador adaptativo (média ponderada com bypass por velocidade) (declaração). |
| `DynamicStabilizer.cpp` | Implementação. |

## Regras

- Sem dependência de pixels: esta pasta só conhece `engine/utils` (`Point2D`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/utils`
<!-- /arccc:deps -->
