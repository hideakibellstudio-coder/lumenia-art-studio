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
| `EventClock.hpp` | Um instante crescente por evento a partir do instante do aparelho: no Windows o relógio de mensagens anda em degraus de ~15,6 ms e repete o instante em pares (mouse de 125 Hz), grupos de 16 (1 kHz) ou rajadas de 6 (caneta); o instante repetido vai um intervalo aprendido depois do anterior. Instante já crescente passa intacto. Só o cabeçalho. |
| `DynamicStabilizer.hpp` | Estabilizador: média ponderada sobre uma janela de TEMPO (o peso cai com a idade da amostra até zero na borda), com bypass por velocidade; os instantes passam pelo `EventClock`; `drain` leva a linha até onde a caneta levantou (declaração). |
| `DynamicStabilizer.cpp` | Implementação. Até 2026-10-09 a janela contava eventos: o atraso dependia da taxa do aparelho (mouse de 60 Hz atrasava 6 vezes mais que a caneta) e a linha dobrava quando a janela enchia. Intervalo sem eventos é preenchido com amostras no caminho entre a última posição e a nova (o mouse parado manda o evento seguinte ao lado de onde parou; um evento atrasado não puxa a linha para trás). |

## Regras

- Sem dependência de pixels: esta pasta só conhece `engine/utils` (`Point2D`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/utils`
<!-- /arccc:deps -->
