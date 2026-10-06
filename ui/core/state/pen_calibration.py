"""PenCalibration — a curva global de entrada da pressão da caneta e o assistente que a sugere.

A pressão que chega do Qt depende da mesa e do driver: a caneta gravada em 2026-10-02
(Windows Ink) mal passa de 0,35 no desenho livre (mediana 0,12), então curvas de pincel
pensadas para 0..1 deixavam o Lápis HB com 74% do trajeto sem tinta. A conta mora no motor
(`PressureCalibration`, aplicada antes do estabilizador); aqui ficam só o valor que o
artista escolhe, sua leitura/escrita na configuração e o cálculo da sugestão a partir de
traços medidos.

    lido = ((bruto - floor) / (ceiling - floor)) ** gamma, preso em 0..1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, NamedTuple

# Faixas aceitas (as mesmas que o motor impõe ao aplicar): uma configuração malformada
# nunca chega ao motor com valor que ele teria de corrigir sozinho.
FLOOR_RANGE = (0.0, 0.5)
CEILING_RANGE = (0.1, 1.0)
GAMMA_RANGE = (0.3, 3.0)

# Abaixo disto a medição não diz nada sobre a caneta (poucos pontos de movimento).
MIN_MEASURED_SAMPLES = 60
# Um pico isolado não deve definir "a pressão total": o assistente usa o percentil 95.
MEASURED_PERCENTILE = 0.95
# Pressão abaixo disto é o pouso e a retirada da caneta, não o gesto de desenhar.
MEASURE_NOISE_FLOOR = 0.01
# Se o p95 já chega perto de 1, a caneta cobre a faixa inteira e a sugestão é não mexer.
FULL_RANGE_FROM = 0.9


def _clamp(value: float, bounds: tuple[float, float]) -> float:
    low, high = bounds
    return max(low, min(high, float(value)))


@dataclass(frozen=True)
class PenCalibration:
    """Os três números da curva; o padrão (0, 1, 1) é a identidade."""

    floor: float = 0.0
    ceiling: float = 1.0
    gamma: float = 1.0

    @property
    def is_identity(self) -> bool:
        return self.floor == 0.0 and self.ceiling == 1.0 and self.gamma == 1.0

    def normalized(self) -> "PenCalibration":
        """Os mesmos números presos nas faixas aceitas, com `ceiling` sempre acima de `floor`."""
        floor = _clamp(self.floor, FLOOR_RANGE)
        ceiling = max(_clamp(self.ceiling, CEILING_RANGE), floor + 0.05)
        return PenCalibration(floor, min(1.0, ceiling), _clamp(self.gamma, GAMMA_RANGE))

    def to_config(self) -> dict[str, float]:
        return {"floor": self.floor, "ceiling": self.ceiling, "gamma": self.gamma}

    @classmethod
    def from_config(cls, data: Mapping[str, Any] | None) -> "PenCalibration":
        """Lê da configuração; qualquer defeito (ausente, texto, NaN) volta para a identidade."""
        if not isinstance(data, Mapping):
            return cls()
        try:
            values = (float(data.get("floor", 0.0)), float(data.get("ceiling", 1.0)), float(data.get("gamma", 1.0)))
        except (TypeError, ValueError):
            return cls()
        if any(v != v for v in values):  # NaN
            return cls()
        return cls(*values).normalized()


def percentile(values: list[float], fraction: float) -> float:
    """Percentil por posição ordenada (sem interpolar: as amostras já são densas)."""
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


class PressureSummary(NamedTuple):
    """O que o assistente mostra enquanto o artista desenha: quantas amostras, o pico e o aperto habitual."""

    count: int
    peak: float
    habitual: float  # p95 da pressão medida


def summarize_pressures(pressures: Iterable[float]) -> PressureSummary | None:
    """Resumo da pressão dos movimentos medidos; `None` enquanto não há nenhum além do ruído de pouso."""
    measured = [float(p) for p in pressures if p > MEASURE_NOISE_FLOOR]
    if not measured:
        return None
    return PressureSummary(len(measured), max(measured), percentile(measured, MEASURED_PERCENTILE))


def suggest_from_pressures(pressures: Iterable[float]) -> PenCalibration | None:
    """Sugestão a partir da pressão dos movimentos de traços feitos "como o artista desenha de verdade".

    `ceiling` = p95 da pressão medida: o aperto que ele usa no dia a dia passa a contar como
    pressão total. Devolve `None` quando há poucos pontos para concluir algo e a identidade
    quando a caneta já cobre a faixa inteira.
    """
    summary = summarize_pressures(pressures)
    if summary is None or summary.count < MIN_MEASURED_SAMPLES:
        return None
    if summary.habitual >= FULL_RANGE_FROM:
        return PenCalibration()
    return PenCalibration(ceiling=round(max(summary.habitual, CEILING_RANGE[0]), 2)).normalized()
