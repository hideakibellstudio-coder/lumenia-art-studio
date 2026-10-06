"""Seção 1 do painel avançado: tamanho, opacidade, mesclagem e estabilizador."""
from __future__ import annotations

from PySide6 import QtWidgets

from ui.infrastructure.i18n import tr
from ui.core.state import BrushParam, BrushState

from .brush_engine_writer import BrushEngineWriter
from .base import AdvancedSection


class SizeOpacitySection(AdvancedSection):
    def __init__(self, brush: BrushState, writer: BrushEngineWriter) -> None:
        super().__init__(tr("brush.sec_size_opacity", "1. Tamanho, Opacidade, Fluxo & Mesclagem"), brush, writer)
        self.slider_size = self.quick_slider(
            BrushParam.SIZE, tr("brush.size", "Tamanho"), 1, 500, 24, "px", 1.0, "size", True)
        self.sl_min_size = self.engine_slider(
            tr("brush.min_size", "Tamanho Mínimo (Pressão)"), 0, 100, 0, "%",
            "min_size_percent", 100.0, lambda v: writer.root("min_size_percent", v))
        self.slider_opacity = self.quick_slider(
            BrushParam.OPACITY, tr("brush.opacity", "Opacidade"), 1, 100, 100, "%", 100.0, "opacity", True)
        self.slider_flow = self.quick_slider(
            BrushParam.FLOW, tr("brush.flow", "Fluxo"), 1, 100, 100, "%", 100.0, "flow", True)
        self.sl_min_op = self.engine_slider(
            tr("brush.min_opacity", "Fluxo Mínimo (Pressão)"), 0, 100, 0, "%",
            "min_opacity_percent", 100.0, lambda v: writer.root("min_opacity_percent", v))
        self.body.addWidget(QtWidgets.QLabel(f"{tr('brush.blend_mode', 'Modo de Mesclagem')} (DabBlendMode):"))
        self.cmb_blend = self.engine_combo([
            f"{tr('blend_mode.normal', 'Normal')} (Alpha Over)",
            f"{tr('blend_mode.multiply', 'Multiplicação')} (Marcador/Feltro)",
            f"{tr('blend_mode.additive', 'Aditivo')} (Luz / Glow)",
            f"{tr('blend_mode.erase', 'Borracha')} (Alpha Erase)",
        ], lambda idx: writer.root("blend_mode", int(idx)), profile_key="blend_mode")
        self.body.addWidget(self.cmb_blend)
        self.chk_vel_size = self.engine_check(
            tr("brush.velocity_size", "Variação por Velocidade (Velocity Size)"),
            "velocity_size_enabled", lambda on: writer.root("velocity_size_enabled", on))
        self.sl_vel_flow = self.engine_slider(
            tr("brush.velocity_flow", "Perda de Fluxo por Velocidade"), 0, 100, 0, "%",
            "velocity_to_flow", 100.0, lambda v: writer.root("velocity_to_flow", v))
        self.slider_stabilizer = self.quick_slider(
            BrushParam.STABILIZER, tr("brush.stabilizer_label", "Suavização (Estabilizador)"),
            0, 98, 40, "%", 100.0, "stabilizer", False)
        self.chk_stroke_taper = self.engine_check(
            tr("brush.stroke_taper", "Afunilamento na Soltura (Tapering no Pen Up)"),
            "stroke_taper_enabled", lambda on: writer.root("stroke_taper_enabled", on), checked=True)
