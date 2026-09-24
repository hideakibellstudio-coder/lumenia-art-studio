"""BrushState — fonte única da cor ativa, dos parâmetros rápidos e do preset por ferramenta.

Antes de 2026-09-24 esse estado vivia em seis lugares ao mesmo tempo
(WorkspaceContainer._saved_color, CanvasWidget.active_color, sliders do painel,
sliders do painel avançado, BrushDropdown._tool_preset_state e o perfil do
motor) e era mantido em sincronia à mão por um mediador que reescrevia os
widgets internos dos outros plugins. Agora:

    widget que edita  ──set_*──►  BrushState  ──sinais──►  todo mundo que mostra
                                      │
                                      └──►  BrushEngineSync  ──►  motor (único caminho)

Regras do contrato:
- quem edita chama `set_color` / `set_value` / `select_preset`;
- quem mostra escuta `colorChanged` / `paramChanged` / `presetSelected`;
- valor igual ao atual não emite nada — por isso nenhum widget precisa de
  `blockSignals` nem de guarda de reentrância para evitar laço;
- ninguém fala com o motor sobre esses valores além do BrushEngineSync.
"""
from __future__ import annotations

from typing import Any

from PySide6 import QtCore, QtGui

from .brush_params import BRUSH_PARAM_DEFAULTS, BrushParam, coerce_param, quick_params_from_preset


class BrushState(QtCore.QObject):
    colorChanged = QtCore.Signal(QtGui.QColor)
    # (BrushParam, float | bool)
    paramChanged = QtCore.Signal(object, object)
    # (tool_id, preset_name, preset_data)
    presetSelected = QtCore.Signal(str, str, dict)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._color = QtGui.QColor(QtCore.Qt.GlobalColor.black)  # tinta padrão: conteúdo, não tema
        self._params: dict[BrushParam, float | bool] = dict(BRUSH_PARAM_DEFAULTS)
        self._presets: dict[str, tuple[str, dict[str, Any]]] = {}

    # ── Cor ───────────────────────────────────────────────────────────────

    @property
    def color(self) -> QtGui.QColor:
        """Cópia da cor ativa (alterar a cópia não altera o estado)."""
        return QtGui.QColor(self._color)

    def set_color(self, color: QtGui.QColor) -> None:
        if not isinstance(color, QtGui.QColor) or not color.isValid():
            raise ValueError(f"cor inválida: {color!r}")
        if color.rgba() == self._color.rgba():
            return
        self._color = QtGui.QColor(color)
        self.colorChanged.emit(QtGui.QColor(self._color))

    # ── Parâmetros rápidos ────────────────────────────────────────────────

    def value(self, param: BrushParam) -> float | bool:
        return self._params[BrushParam(param)]

    def set_value(self, param: BrushParam, value: Any) -> None:
        param = BrushParam(param)
        coerced = coerce_param(param, value)
        if self._params[param] == coerced:
            return
        self._params[param] = coerced
        self.paramChanged.emit(param, coerced)

    def snapshot(self) -> dict[BrushParam, float | bool]:
        return dict(self._params)

    # ── Preset por ferramenta (brush / eraser / smudge) ───────────────────

    def preset(self, tool_id: str) -> tuple[str, dict[str, Any]] | None:
        """Último preset escolhido para a ferramenta, ou None se nunca houve escolha."""
        entry = self._presets.get(tool_id)
        return (entry[0], dict(entry[1])) if entry else None

    def select_preset(self, tool_id: str, name: str, data: dict[str, Any]) -> None:
        """Registra o preset da ferramenta e aplica os parâmetros rápidos que ele define.

        Ordem garantida: `presetSelected` sai primeiro (o motor recebe o perfil
        completo), depois um `paramChanged` por parâmetro rápido que mudou.
        """
        record = dict(data)
        self._presets[tool_id] = (name, record)
        self.presetSelected.emit(tool_id, name, dict(record))
        for param, value in quick_params_from_preset(record).items():
            self.set_value(param, value)
