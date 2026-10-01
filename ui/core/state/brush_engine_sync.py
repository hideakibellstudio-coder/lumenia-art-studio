"""BrushEngineSync — o único caminho entre BrushState e o motor.

Escuta o BrushState e aplica cada mudança no backend ativo. Nenhum painel,
slider ou workspace chama `set_brush_size`/`set_brush_color`/... para os
parâmetros que o BrushState conhece: se chamasse, o motor e a tela voltariam
a divergir (foi o que acontecia com o painel avançado, que escrevia no motor
direto E avisava o painel principal, que avisava o workspace, que escrevia no
motor de novo).

O backend não é guardado: é pedido a cada escrita ao `backend_provider`,
porque o documento ativo (e com ele a facade nativa) muda com as abas.
Quando o documento ativo muda, quem trocou o contexto do motor chama
`resync()` para que a facade nova receba os valores do estado.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6 import QtCore, QtGui

from ui.core.engine.backend import EngineBackend

from .brush_curves import BrushCurve, CurveSetting
from .brush_params import BrushParam
from .brush_state import BrushState

BackendProvider = Callable[[], Optional[EngineBackend]]

_SETTERS: dict[BrushParam, Callable[[EngineBackend, float | bool], None]] = {
    BrushParam.SIZE: lambda b, v: b.set_brush_size(float(v)),
    BrushParam.OPACITY: lambda b, v: b.set_brush_opacity(float(v)),
    BrushParam.PRESSURE: lambda b, v: b.set_brush_pressure(float(v)),
    BrushParam.PRESSURE_CURVE: lambda b, v: b.set_pressure_curve_power(float(v)),
    BrushParam.STABILIZER: lambda b, v: b.set_stabilizer_weight(float(v)),
    BrushParam.SPACING: lambda b, v: b.set_brush_spacing(float(v)),
    BrushParam.CONTRAST: lambda b, v: b.set_brush_contrast(float(v)),
    BrushParam.MIN_DENSITY_ACTIVE: lambda b, v: b.set_min_density_active(bool(v)),
    BrushParam.MIN_DENSITY_VALUE: lambda b, v: b.set_min_density_value(float(v)),
    BrushParam.INVERT_HEIGHT: lambda b, v: b.set_brush_invert_height(bool(v)),
}


class BrushEngineSync(QtCore.QObject):
    def __init__(
        self,
        brush_state: BrushState,
        backend_provider: BackendProvider,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._state = brush_state
        self._backend_provider = backend_provider
        brush_state.colorChanged.connect(self._push_color)
        brush_state.paramChanged.connect(self._push_param)
        brush_state.presetSelected.connect(self._push_preset)
        brush_state.curveChanged.connect(self._push_curve)

    def resync(self) -> None:
        """Reenvia parâmetros rápidos e cor ao backend (usar após trocar o documento ativo).

        O preset NÃO é reaplicado: o adaptador do motor já leva o perfil
        completo da facade que sai para a que entra (inclusive ajustes
        avançados como jitter e textura, que só o motor conhece). Até
        2026-09-24 o preset era reaplicado aqui e esses ajustes se perdiam a
        cada troca de aba.
        """
        backend = self._backend_provider()
        if backend is None:
            return
        for param, value in self._state.snapshot().items():
            _SETTERS[param](backend, value)
        self._apply_color(backend, self._state.color)
        self._apply_edited_curves(backend)

    def _push_color(self, color: QtGui.QColor) -> None:
        backend = self._backend_provider()
        if backend is not None:
            self._apply_color(backend, color)

    def _push_param(self, param: BrushParam, value: float | bool) -> None:
        backend = self._backend_provider()
        if backend is not None:
            _SETTERS[param](backend, value)

    def _push_preset(self, _tool_id: str, _name: str, data: dict) -> None:
        backend = self._backend_provider()
        if backend is not None:
            backend.apply_brush_preset_dict(data)
            # O preset não carrega curvas: as que o usuário editou valem por cima dele.
            self._apply_edited_curves(backend)

    def _push_curve(self, curve: BrushCurve, setting: CurveSetting) -> None:
        backend = self._backend_provider()
        if backend is not None:
            self._apply_curve(backend, curve, setting)

    def _apply_edited_curves(self, backend: EngineBackend) -> None:
        for curve, setting in self._state.edited_curves().items():
            self._apply_curve(backend, curve, setting)

    @staticmethod
    def _apply_curve(backend: EngineBackend, curve: BrushCurve, setting: CurveSetting) -> None:
        backend.set_curve_control_points(curve.value, [tuple(point) for point in setting.points], setting.enabled)

    @staticmethod
    def _apply_color(backend: EngineBackend, color: QtGui.QColor) -> None:
        backend.set_brush_color(color.redF(), color.greenF(), color.blueF())
