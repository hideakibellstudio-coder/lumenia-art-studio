"""telemetry_benchmark — benchmark sintético do motor num documento descartável.

O botão "Executar Benchmark" do diagnóstico traça 1000 carimbos. Até
2026-09-24 o traço ia para a camada ativa do documento do usuário (e ficava
no histórico dele); agora roda num contexto nativo próprio, que é fechado no
fim, e o motor volta para o documento que estava ativo.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

BENCHMARK_CONTEXT = "__telemetry_benchmark__"
_SIZE = 512


@dataclass(frozen=True)
class BenchmarkResult:
    elapsed_ms: float
    steps: int

    @property
    def dabs_per_second(self) -> int:
        return int(self.steps / self.elapsed_ms * 1000.0) if self.elapsed_ms > 0 else 0

    @property
    def ms_per_dab(self) -> float:
        return self.elapsed_ms / self.steps if self.steps else 0.0


def run_stroke_benchmark(backend: Any, active_size: Optional[tuple[int, int]], steps: int = 1000) -> BenchmarkResult:
    """Traça `steps` carimbos num contexto descartável e restaura o contexto ativo.

    `active_size` é (largura, altura) do documento ativo, ou None sem documento.
    """
    previous = backend.get_active_document_context()
    backend.set_active_document_context(BENCHMARK_CONTEXT, _SIZE, _SIZE)
    try:
        t0 = time.perf_counter()
        backend.start_stroke(100.0, 100.0, 1.0)
        for i in range(steps):
            backend.paint_stroke(100.0 + (i % 200), 100.0 + (i // 5), 0.8)
        backend.end_stroke(300.0, 300.0)
        elapsed = (time.perf_counter() - t0) * 1000.0
    finally:
        if previous is not None and active_size is not None:
            backend.set_active_document_context(previous, *active_size)
        backend.close_document_context(BENCHMARK_CONTEXT)
    return BenchmarkResult(elapsed, steps)
