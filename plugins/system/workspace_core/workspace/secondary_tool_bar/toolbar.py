"""SecondaryToolBar — barra flutuante com as opções da ferramenta ativa.

Só moldura: cápsula com sombra, orientação (horizontal quando a barra de
ferramentas está em cima/embaixo, vertical quando está nas laterais) e uma
pilha com uma view por ferramenta e orientação (`views/`). Cada view lê e
escreve o `ToolState` sozinha; a barra não guarda opção nenhuma.

Para fora, dois sinais:
- `commandRequested(ToolCommand)`: botões pontuais (Aplicar, Desmarcar,
  Inserir texto...). O workspace liga em `RenderWidget.run_tool_command`.
- `sizeChanged()`: o conteúdo mudou de tamanho (troca de ferramenta, tipo de
  forma com parâmetro extra). O workspace reposiciona a barra.

Até 2026-09-24 a barra tinha 366 linhas mais três mixins de handlers e nove
funções `build_*_panels(toolbar)` que penduravam ~200 atributos nela; cada
opção existia duas vezes (`slider_x_h`/`slider_x_v`) e era copiada de uma
para a outra à mão, e os botões chamavam `self.parent().canvas_widget`.
"""
from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from ui.core.dialogs.floating_tool_window import FloatingToolWindow
from ui.core.state import BrushState, ToolState, options_key

from .dynamic_stacked_widget import DynamicStackedWidget
from .views import OrientedOptionsView, build_option_views

_H, _V = QtCore.Qt.Horizontal, QtCore.Qt.Vertical


class SecondaryToolBar(FloatingToolWindow):
    commandRequested = QtCore.Signal(str)
    sizeChanged = QtCore.Signal()

    def __init__(self, tool_state: ToolState, brush_state: BrushState,
                 parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent, transparent_stylesheet=True)
        self._tool_state = tool_state
        self._orientation = _H
        self._build_frame()

        self._views: dict[QtCore.Qt.Orientation, dict[str, OrientedOptionsView]] = {
            orientation: build_option_views(tool_state, brush_state, orientation) for orientation in (_H, _V)
        }
        for views in self._views.values():
            for view in views.values():
                self.stacked_widget.addWidget(view)
                view.commandRequested.connect(self.commandRequested)
        self._apply_orientation_constraints()
        self._select_page()

        tool_state.activeToolChanged.connect(self._on_active_tool_changed)
        tool_state.optionsChanged.connect(self._on_options_changed)

    # ── API pública ───────────────────────────────────────────────────────

    def option_view(self, key: str, orientation: QtCore.Qt.Orientation | None = None) -> OrientedOptionsView:
        """View das opções `key` na orientação pedida (padrão: a atual)."""
        return self._views[orientation or self._orientation][key]

    def set_orientation(self, orientation: QtCore.Qt.Orientation) -> None:
        """Chamado pelo workspace, que reposiciona a barra logo depois."""
        if self._orientation == orientation:
            return
        self._orientation = orientation
        self._apply_orientation_constraints()
        self._select_page()
        self._refit()

    # ── Estado → barra ────────────────────────────────────────────────────

    def _on_active_tool_changed(self, _tool: str, _previous: str) -> None:
        if self._select_page():
            self.show()
            self._refit()
            self.sizeChanged.emit()
        else:
            self.hide()

    def _on_options_changed(self, key: str, _options: dict) -> None:
        if not self.isVisible() or key != options_key(self._tool_state.active_tool):
            return
        before = self.size()
        self._refit()
        if self.size() != before:
            self.sizeChanged.emit()

    def _refit(self) -> None:
        """Ajusta a barra ao conteúdo da página atual, já.

        Esconder/mostrar um widget (o parâmetro extra da forma) só invalida os
        layouts por evento postado; sem forçar aqui, a barra ficava com a
        largura antiga (até 2026-09-24 ela não encolhia de estrela para elipse).
        """
        page = self.stacked_widget.currentWidget()
        if page is not None:
            page.layout().invalidate()
            page.layout().activate()
        self.stacked_widget.updateGeometry()
        self.box_layout.invalidate()
        self.box_layout.activate()
        self.layout().activate()
        self.adjustSize()

    def _select_page(self) -> bool:
        """Mostra na pilha a view da ferramenta ativa; False se ela não tem opções aqui."""
        view = self._views[self._orientation].get(options_key(self._tool_state.active_tool))
        if view is not None:
            self.stacked_widget.setCurrentWidget(view)
        return view is not None

    # ── Moldura ───────────────────────────────────────────────────────────

    def _build_frame(self) -> None:
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 10)
        main_layout.setSpacing(0)
        main_layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)

        self.container = QtWidgets.QWidget(self)
        self.container.setObjectName("SecondaryBarContainer")
        shadow = QtWidgets.QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        self.container.setGraphicsEffect(shadow)
        main_layout.addWidget(self.container)

        self.box_layout = QtWidgets.QBoxLayout(QtWidgets.QBoxLayout.LeftToRight, self.container)
        self.stacked_widget = DynamicStackedWidget(self.container)
        self.box_layout.addWidget(self.stacked_widget)

    def _apply_orientation_constraints(self) -> None:
        if self._orientation == _V:
            self.container.setMinimumHeight(0)
            self.container.setMaximumHeight(16777215)
            self.container.setFixedWidth(206)
            self.box_layout.setContentsMargins(12, 12, 12, 14)
            self.box_layout.setSpacing(6)
            self.box_layout.setAlignment(QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter)
        else:
            self.container.setMinimumWidth(0)
            self.container.setMaximumWidth(16777215)
            self.container.setFixedHeight(40)
            self.box_layout.setContentsMargins(12, 0, 12, 0)
            self.box_layout.setSpacing(8)
            self.box_layout.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
