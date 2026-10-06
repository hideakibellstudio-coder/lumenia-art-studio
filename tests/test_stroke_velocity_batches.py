"""Leitura de velocidade do traço com a mesa real: vários eventos por timestamp.

A mesa gravada no Windows (Windows Ink via wmpointer, 59,94 Hz) entrega os eventos em
rajadas de ~6 com o MESMO timestamp em milissegundos inteiros. O rastreador antigo só
atualizava a velocidade quando o tempo avançava e só media o último passo: lia ~11% da
velocidade real, e todo recurso dependente de velocidade (tamanho por velocidade, atalho
do estabilizador, aerógrafo parado) ficava cego na caneta.

O conserto tem duas partes, e este arquivo mede as duas pelo resultado que o artista
observa (`update_stroke_raw` devolve a velocidade suavizada no índice 7):

  1. regime: com a caneta a velocidade constante, a leitura fica perto da real
     qualquer que seja o jeito de entregar os eventos (rajadas, 1 kHz, 125 Hz);
  2. partida: a leitura chega perto da real em poucos quadros, não em 250 ms.
"""

from __future__ import annotations

import pytest

native = pytest.importorskip(
    "aladyn_engine_native", reason="módulo nativo não compilado neste ambiente"
)

TRUE_SPEED = 1400.0  # px/s: traço rápido de ilustração
FRAME_HZ = 59.94
VELOCITY_INDEX = 7  # {dirty x, y, w, h, x, y, pressão, velocidade, opacidade}


def _engine():
    engine = native.PaintEngineFacade(900, 64)
    engine.set_render_options(low_latency=False, linear_gamma=False, deep_color=False)
    engine.get_stabilizer().set_stabilization_percentage(0.0)
    engine.get_brush_profile().brush_size = 4.0
    return engine


def _readings(events_per_stamp: int, stamp_hz: float, seconds: float = 0.5) -> list[tuple[float, float]]:
    """(tempo, leitura) a cada evento de um traço reto a TRUE_SPEED px/s.

    Os eventos de um mesmo carimbo saem espaçados no tempo real, mas levam o timestamp do
    carimbo, em milissegundos inteiros como o Qt entrega (`QInputEvent.timestamp()`).
    """
    engine = _engine()
    stamps = int(seconds * stamp_hz)
    engine.begin_stroke_raw(20.0, 32.0, 0.6, 0.0 + 1e-3)
    out = []
    for stamp in range(1, stamps + 1):
        stamp_time = stamp / stamp_hz
        stamped = round(stamp_time * 1000.0) / 1000.0
        for k in range(events_per_stamp):
            real_time = stamp_time - (events_per_stamp - 1 - k) / (stamp_hz * events_per_stamp)
            x = 20.0 + TRUE_SPEED * real_time
            result = engine.update_stroke_raw(x, 32.0, 0.6, stamped + 1e-3)
            out.append((real_time, float(result[VELOCITY_INDEX])))
    engine.end_stroke_raw()
    return out


def _steady(readings, after: float = 0.25):
    return [v for t, v in readings if t >= after]


@pytest.mark.parametrize(
    "events_per_stamp,stamp_hz",
    [(6, FRAME_HZ), (1, 1000.0), (1, 125.0), (2, 125.0)],
    ids=["pen_6_per_stamp_60hz", "mouse_1khz", "mouse_125hz", "pair_per_stamp_125hz"],
)
def test_steady_reading_is_near_the_true_speed(events_per_stamp, stamp_hz):
    values = _steady(_readings(events_per_stamp, stamp_hz))
    assert values, "o traço não gerou leituras"
    worst = max(abs(v - TRUE_SPEED) / TRUE_SPEED for v in values)
    assert worst <= 0.15, (
        f"{events_per_stamp} evento(s) por carimbo a {stamp_hz} Hz: a leitura chegou a "
        f"{min(values):.0f}..{max(values):.0f} px/s para {TRUE_SPEED:.0f} px/s reais "
        f"(pior erro {worst:.0%}, limite 15%)"
    )


@pytest.mark.parametrize(
    "events_per_stamp,stamp_hz",
    [(6, FRAME_HZ), (1, 1000.0), (1, 125.0)],
    ids=["pen_6_per_stamp_60hz", "mouse_1khz", "mouse_125hz"],
)
def test_reading_reaches_the_true_speed_quickly(events_per_stamp, stamp_hz):
    readings = _readings(events_per_stamp, stamp_hz)
    reached = next((t for t, v in readings if v >= 0.85 * TRUE_SPEED), None)
    assert reached is not None, f"a leitura nunca passou de 85%: máximo {max(v for _, v in readings):.0f} px/s"
    assert reached <= 0.12, f"85% da velocidade real só aos {reached * 1000:.0f} ms (limite 120 ms)"


def test_a_stopped_pen_reads_zero_again():
    """Parar tem que zerar a leitura: o aerógrafo só emite parado quando ela chega perto de 0."""
    engine = _engine()
    engine.begin_stroke_raw(20.0, 32.0, 0.6, 1e-3)
    t = 0.0
    for i in range(1, 31):
        t = i / 125.0
        engine.update_stroke_raw(20.0 + TRUE_SPEED * t, 32.0, 0.6, t + 1e-3)
    x = 20.0 + TRUE_SPEED * t
    last = 0.0
    for i in range(1, 126):
        last = float(engine.update_stroke_raw(x, 32.0, 0.6, t + i / 125.0 + 1e-3)[VELOCITY_INDEX])
    assert last < 3.0, f"1 s parada e a leitura ainda é {last:.1f} px/s"
