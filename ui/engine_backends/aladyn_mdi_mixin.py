"""AladynMdiMixin — Gerenciador de Contextos MDI Multi-Documento para o AladynBackend."""

from __future__ import annotations
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AladynMdiMixin:
    """Mixin para gerenciamento de múltiplas instâncias de PaintEngineFacade por documento."""

    def __init_mdi__(self) -> None:
        self._doc_facades: dict[str, Any] = {}
        self._active_doc_uid: str | None = None

    def set_active_document_context(self, uid: str, width: int, height: int) -> None:
        """
        Alterna o contexto ativo de execução C++ para o documento especificado em tempo O(1).
        Se a PaintEngineFacade para o documento ainda não existir, ela é alocada imediatamente.
        """
        if not hasattr(self, "_doc_facades"):
            self._doc_facades = {}

        if self._native is None:
            return

        w = max(1, int(width))
        h = max(1, int(height))

        if uid not in self._doc_facades:
            try:
                facade = self._native.PaintEngineFacade(w, h)
                if hasattr(facade, "get_canvas_texture"):
                    c_tex = facade.get_canvas_texture()
                    if c_tex:
                        c_tex.canvas_grain_enabled = False
                self._doc_facades[uid] = facade
                logger.info(f"[AladynBackend] Nova PaintEngineFacade C++ criada para doc '{uid}' ({w}×{h}).")
            except Exception as e:
                logger.error(f"[AladynBackend] Falha ao alocar PaintEngineFacade para doc '{uid}': {e}")
                return

        self._active_doc_uid = uid
        self._facade = self._doc_facades[uid]
        self._width = self._facade.get_width()
        self._height = self._facade.get_height()

    def close_document_context(self, uid: str) -> None:
        """Libera a memória C++ e deleta a PaintEngineFacade do documento fechado."""
        if not hasattr(self, "_doc_facades"):
            return

        if uid in self._doc_facades:
            del self._doc_facades[uid]
            logger.info(f"[AladynBackend] PaintEngineFacade C++ liberada para doc '{uid}'.")

        if self._active_doc_uid == uid:
            self._active_doc_uid = None
            if self._doc_facades:
                first_uid = next(iter(self._doc_facades))
                self._facade = self._doc_facades[first_uid]
                self._active_doc_uid = first_uid
                self._width = self._facade.get_width()
                self._height = self._facade.get_height()
            else:
                self._facade = None
