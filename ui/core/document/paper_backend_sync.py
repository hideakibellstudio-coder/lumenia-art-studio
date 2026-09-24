"""paper_backend_sync — leva o papel do documento ao motor.

Único escritor do papel no motor fora da restauração de arquivo
(`restore.py`). Até 2026-09-24 eram dois: o widget de papel do painel de
camadas (que guardava a própria cópia do estado) e a troca de documento do
workspace, cada um com seu subconjunto de campos.
"""
from __future__ import annotations

from typing import Iterable, Optional

from ui.core.engine.registry import EngineRegistry
from ui.core.plugins.canvas_access import request_canvas_repaint


def sync_paper_to_backend(document, changed: Optional[Iterable[str]] = None) -> None:
    """Envia cor, visibilidade, textura e grão do papel de `document` ao motor.

    Só age se o contexto ativo do motor for este documento. `changed` são os
    campos alterados; trocar `texture_id` recarrega o relevo do preset.
    """
    backend = EngineRegistry.instance().get_backend()
    if backend is None or not backend.available:
        return
    if backend.get_active_document_context() != document.uid:
        return
    reset_texture = changed is not None and "texture_id" in changed
    backend.set_canvas_paper_state(
        document.paper_color, document.paper_visible,
        document.paper_texture_id, document.paper_texture_enabled,
        reset_texture=reset_texture,
    )
    backend.set_canvas_grain_scale(float(document.paper_scale))
    backend.set_canvas_grain_contrast(float(document.paper_contrast))
    backend.set_canvas_grain_invert(bool(document.paper_invert))
    request_canvas_repaint()
