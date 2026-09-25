"""Seção 3 do painel avançado: variações aleatórias (jitter) de tamanho, rotação e posição.

Os sliders são 0–100 %; no motor os três jitters são 0.0–1.0 (o de rotação é
multiplicado por 180° e o de posição por 2× o raio lá dentro).
"""
from __future__ import annotations

from ui.infrastructure.i18n import tr
from ui.core.state import BrushState

from .brush_engine_writer import BrushEngineWriter
from .base import AdvancedSection


class JittersSection(AdvancedSection):
    def __init__(self, brush: BrushState, writer: BrushEngineWriter) -> None:
        super().__init__(tr("brush.sec_jitters", "3. Jitters (Variações Aleatórias)"), brush, writer)
        self.sl_jit_size = self.engine_slider(
            tr("brush.jitter_size", "Jitter de Tamanho"), 0, 100, 0, "%",
            "jitter_size", 100.0, lambda v: writer.tip("jitter_size", v))
        self.sl_jit_angle = self.engine_slider(
            tr("brush.jitter_angle", "Jitter de Rotação"), 0, 100, 0, "%",
            "jitter_angle", 100.0, lambda v: writer.tip("jitter_angle", v))
        self.sl_jit_pos = self.engine_slider(
            tr("brush.jitter_pos", "Jitter de Posição (Deslocamento)"), 0, 100, 0, "%",
            "jitter_position", 100.0, lambda v: writer.tip("jitter_position", v))
