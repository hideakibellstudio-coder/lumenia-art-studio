"""ToolOptionsView — widget que mostra e edita as opções de UMA ferramenta no ToolState.

É a base de toda tela de opções de ferramenta: as páginas do painel de pincel
(esta pasta) e as views da barra secundária
(`ui/plugins/system/workspace_core/workspace/secondary_tool_bar/views/`).

Contrato:
- a subclasse monta os widgets e chama `bind()` no fim do construtor;
- `show_options(opções)` põe o estado na tela; roda ao ligar e a cada
  `ToolState.optionsChanged` da chave desta view;
- quem o usuário mexeu vira `publish(campo=valor)` — só os campos editados,
  nunca o dicionário inteiro (publicar tudo sobrescrevia com valores velhos o
  que outra tela tinha acabado de mudar);
- enquanto `show_options` roda, `publish` não faz nada: mostrar nunca
  republica, sem `blockSignals` em cada widget;
- botões de ação (Aplicar, Desmarcar...) emitem `commandRequested` com um
  `ui.core.tools.ToolCommand`; quem executa é o canvas.

Várias telas mostram a mesma ferramenta ao mesmo tempo e não se conhecem:
ficam iguais porque todas mostram o mesmo estado.
"""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ui.infrastructure.i18n import I18nManager
from ui.core.state import ToolState


class ToolOptionsView(QtWidgets.QWidget):
    commandRequested = QtCore.Signal(str)

    def __init__(self, tool_state: ToolState, key: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.key = key
        self._tool_state = tool_state
        self._showing = False

    def bind(self) -> None:
        """Liga ao estado e ao idioma; chamar no fim do construtor da subclasse."""
        self._tool_state.optionsChanged.connect(self._on_options_changed)
        I18nManager.instance().languageChanged.connect(self.retranslate_ui)
        self.retranslate_ui()
        self._show(self.options())

    def set_key(self, key: str) -> None:
        """Passa a mostrar outra ferramenta com as mesmas opções (ex.: retângulo → laço)."""
        if key != self.key:
            self.key = key
            self._show(self.options())

    # ── Para as subclasses ────────────────────────────────────────────────

    def show_options(self, options: dict) -> None:
        raise NotImplementedError

    def retranslate_ui(self) -> None:
        """Textos traduzíveis; o padrão é não ter nenhum."""

    def publish(self, **changes) -> None:
        if not self._showing:
            self._tool_state.update_options(self.key, changes)

    def options(self) -> dict:
        return self._tool_state.options(self.key)

    # ── Ligação com o estado ──────────────────────────────────────────────

    def _on_options_changed(self, key: str, options: dict) -> None:
        if key == self.key:
            self._show(options)

    def _show(self, options: dict) -> None:
        self._showing = True
        try:
            self.show_options(options)
        finally:
            self._showing = False
