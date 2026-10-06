# `engine/core/stroke/` — entrada do traço

**Responsabilidade:** o que chega da mesa ou do mouse antes de virar dab: o evento de ponteiro, a velocidade e o estabilizador.

## Porta de entrada

`PointerEvent.hpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `PointerEvent.hpp` | Evento de ponteiro (posição, pressão, inclinação, tempo, tipo). |
| `VelocityTracker.hpp` | Velocidade do traço em px/s: caminho numa janela de tempo, suavização por constante de tempo (declaração). |
| `VelocityTracker.cpp` | Implementação: acumula o caminho de todos os eventos (rajadas com o mesmo timestamp inclusive) e só recalcula quando a janela tem 0,8 ms ou mais. |
| `PenPose.hpp` | A posição da caneta (altitude, azimute, torção) na última amostra do traço: os carimbos criados sem amostra (alcance do estabilizador, afunilamento) a herdam. Só o cabeçalho. |
| `PressureCalibration.hpp` | Curva global de entrada da pressão (zona morta, pressão total, gama): o que a mesa entrega vira o que o motor lê, antes do estabilizador. Padrão: identidade. |
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
