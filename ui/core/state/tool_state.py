"""ToolState — fonte única da ferramenta ativa e das opções de cada ferramenta.

Antes de 2026-09-24 a ferramenta ativa era escrita em quatro lugares (canvas,
barra flutuante, painel de pincel, barra lateral da janela) por três caminhos
diferentes, com guardas de reentrância (`_is_selecting_tool`) em dois deles
para o laço não explodir; o próprio canvas trocava "shape_rect" por "shapes"
por conta própria. As opções de ferramenta tinham um cache na barra
secundária que ninguém lia e chegavam ao canvas por um roteador no workspace
que escrevia nos dicionários privados do canvas.

Agora:
- quem troca de ferramenta chama `set_active_tool(id)`; quem mostra escuta
  `activeToolChanged(novo, anterior)`;
- quem edita opções chama `update_options(id, mudanças)`; o estado normaliza
  com `ui.core.tool_settings` e emite `optionsChanged(chave, opções completas)`.
Valor igual não emite (sem laço, sem guarda).

"Chave de opções" é a ferramenta, exceto as formas: shape_rect, shape_star...
compartilham as opções de "shapes" (o tipo de forma é uma das opções).
"""
from __future__ import annotations

from typing import Any, Mapping

from PySide6 import QtCore

from ui.core.tool_settings import TOOL_SETTING_DEFAULTS, default_tool_settings, normalize_tool_settings
from ui.core.tools import TOOL_META

DEFAULT_TOOL = "brush"


def options_key(tool_id: str) -> str:
    """Chave de opções de uma ferramenta (`shape_*` -> "shapes")."""
    return "shapes" if tool_id.startswith("shape_") else tool_id


def is_shape_tool(tool_id: str) -> bool:
    return tool_id == "shapes" or tool_id.startswith("shape_")


class ToolState(QtCore.QObject):
    # (ferramenta nova, ferramenta anterior)
    activeToolChanged = QtCore.Signal(str, str)
    # (chave de opções, opções normalizadas completas)
    optionsChanged = QtCore.Signal(str, dict)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._active = DEFAULT_TOOL
        self._options: dict[str, dict[str, Any]] = {
            key: default_tool_settings(key) for key in TOOL_SETTING_DEFAULTS
        }

    # ── Ferramenta ativa ──────────────────────────────────────────────────

    @property
    def active_tool(self) -> str:
        return self._active

    def set_active_tool(self, tool_id: str) -> None:
        if tool_id not in TOOL_META:
            raise ValueError(f"ferramenta desconhecida: {tool_id!r} (ver ui.core.tools.TOOL_META)")
        if tool_id == self._active:
            return
        # Escolher "shape_star" é escolher o tipo de forma: as opções mudam
        # antes, para quem reage à troca de ferramenta já ler o tipo certo.
        if tool_id.startswith("shape_"):
            self.update_options("shapes", {"shape_type": tool_id})
        previous, self._active = self._active, tool_id
        self.activeToolChanged.emit(tool_id, previous)

    # ── Opções por ferramenta ─────────────────────────────────────────────

    def options(self, tool_id: str) -> dict[str, Any]:
        """Cópia das opções atuais (vazia para ferramenta sem opções)."""
        return dict(self._options.get(options_key(tool_id), {}))

    def update_options(self, tool_id: str, changes: Mapping[str, Any]) -> None:
        key = options_key(tool_id)
        current = self._options.get(key)
        if current is None:
            raise ValueError(f"ferramenta sem opções configuráveis: {tool_id!r}")
        merged = normalize_tool_settings(key, changes, current)
        if merged == current:
            return
        self._options[key] = merged
        self.optionsChanged.emit(key, dict(merged))
