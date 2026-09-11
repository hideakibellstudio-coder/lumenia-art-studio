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

    def get_active_document_context(self):
        return self._active_doc_uid

    def _mark_document_dirty(self, reason):
        from ui.core.document.manager import DocumentManager
        document = DocumentManager.instance().get_document(self._active_doc_uid)
        if document is not None:
            document.mark_dirty(reason)

    def replace_document_context(self, uid: str, prepared_uid: str) -> bool:
        if uid == prepared_uid or uid not in self._doc_facades or prepared_uid not in self._doc_facades:
            return False
        prepared = self._doc_facades[prepared_uid]
        self._doc_facades[uid] = prepared
        del self._doc_facades[prepared_uid]
        self._active_doc_uid = uid
        self._facade = prepared
        self._width, self._height = prepared.get_width(), prepared.get_height()
        return True

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
                if hasattr(self, "_undo_memory_limit_mb") and hasattr(facade, "set_undo_memory_limit_mb"):
                    facade.set_undo_memory_limit_mb(self._undo_memory_limit_mb)
                if hasattr(self, "_undo_max_steps") and hasattr(facade, "set_undo_max_steps"):
                    facade.set_undo_max_steps(self._undo_max_steps)
                if hasattr(self, "_render_options"):
                    if hasattr(facade, "set_render_options"):
                        facade.set_render_options(**self._render_options)
                    else:
                        for key, value in self._render_options.items():
                            setter = getattr(facade, f"set_{key}", None)
                            if setter:
                                setter(value)
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
        if hasattr(self, "_render_options") and hasattr(self._facade, "set_render_options"):
            self._facade.set_render_options(**self._render_options)
        if hasattr(self, "_last_brush_preset") and self._last_brush_preset:
            self.apply_brush_preset_dict(self._last_brush_preset)

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
