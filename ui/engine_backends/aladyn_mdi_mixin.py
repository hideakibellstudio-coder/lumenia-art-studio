"""AladynMdiMixin — Gerenciador de Contextos MDI Multi-Documento para o AladynBackend."""

from __future__ import annotations
import logging
from typing import Any

from .native_fallback import native_has
from .aladyn_base import AladynBackendBase

logger = logging.getLogger(__name__)

# Contexto nativo provisório do boot, enquanto nenhum documento está aberto.
# É liberado quando o primeiro documento real fica ativo: até 2026-09-24 ele
# ficava alocado pelo resto da sessão (~4 MB em 800×600, medido).
PLACEHOLDER_CONTEXT = "default_doc"


class AladynMdiMixin(AladynBackendBase):
    """Mixin para gerenciamento de múltiplas instâncias de PaintEngineFacade por documento."""

    def get_active_document_context(self):
        return self._active_doc_uid

    def _push_render_options(self, facade) -> None:
        """Aplica as opções de render guardadas numa facade (único ponto do fallback).

        O caminho normal é `set_render_options(...)`. O `else` existe só para um
        `.pyd` compilado antes desse método existir (ver lista de fallbacks
        legítimos em tests/test_native_guard_ratchet.py).
        """
        options = self._render_options
        if not facade:
            return
        if native_has(facade, "set_render_options", "opções de render aplicadas uma a uma"):
            facade.set_render_options(**options)
            return
        for key, value in options.items():
            setter = getattr(facade, f"set_{key}", None)
            if setter:
                setter(value)

    def set_active_document_context(self, uid: str, width: int, height: int) -> None:
        """
        Alterna o contexto ativo de execução C++ para o documento especificado em tempo O(1).
        Se a PaintEngineFacade para o documento ainda não existir, ela é alocada imediatamente.
        """
        if self._native is None:
            return

        w = max(1, int(width))
        h = max(1, int(height))

        if uid not in self._doc_facades:
            try:
                facade = self._native.PaintEngineFacade(w, h)
                facade.set_undo_memory_limit_mb(self._undo_memory_limit_mb)
                facade.set_undo_max_steps(self._undo_max_steps)
                self._push_render_options(facade)
                if facade:
                    c_tex = facade.get_canvas_texture()
                    if c_tex:
                        c_tex.canvas_grain_enabled = False
                self._doc_facades[uid] = facade
                logger.info(f"[AladynBackend] Nova PaintEngineFacade C++ criada para doc '{uid}' ({w}×{h}).")
            except Exception as e:
                logger.error(f"[AladynBackend] Falha ao alocar PaintEngineFacade para doc '{uid}': {e}")
                return

        # Sincroniza o cache de pincel com o estado REAL do facade que esta
        # saindo, ANTES de trocar.
        #
        # `_last_brush_preset` so era atualizado por `apply_brush_preset_dict`.
        # Os controles da UI (slider de estabilizador, opacidade, espacamento,
        # dureza...) gravam DIRETO no facade via seus setters e nunca tocavam o
        # cache. Resultado medido: mover o slider para 95% funcionava, e a
        # reaplicacao logo abaixo devolvia o valor do preset (40%) na primeira
        # re-ativacao de contexto — inclusive do MESMO documento.
        #
        # Sao ~46 propriedades reaplicadas aqui, entao o defeito nunca foi so do
        # estabilizador: opacidade e espacamento sofriam o mesmo, e espacamento
        # errado num pincel grande multiplica o numero de carimbos.
        #
        # O merge (cache primeiro, estado vivo por cima) e necessario e nao
        # cosmetico: `get_brush_profile_dict` produz 42 das ~46 chaves, mas nao
        # produz `engine_type`, `shape_preset` nem `brush_height_preset`. Um
        # `replace` as perderia; o merge preserva o que o getter nao sabe ler.
        if self._facade is not None:
            try:
                live_state = self.get_brush_profile_dict()
                if live_state:
                    merged = dict(self._last_brush_preset)
                    merged.update(live_state)
                    self._last_brush_preset = merged
            except Exception as exc:
                logger.warning(f"[AladynBackend] Nao foi possivel sincronizar o pincel: {exc}")

        self._active_doc_uid = uid
        self._facade = self._doc_facades[uid]
        self._width = self._facade.get_width()
        self._height = self._facade.get_height()
        # O perfil é de cada documento (a facade já guarda o nativo). Até
        # 2026-09-24 o valor do último documento configurado valia para todos:
        # salvar outro documento gravava o perfil errado no arquivo.
        self._color_profile_id = self._doc_profiles.get(uid, 0)
        self._push_render_options(self._facade)
        if self._last_brush_preset:
            self.apply_brush_preset_dict(self._last_brush_preset)
        if uid != PLACEHOLDER_CONTEXT:
            self._doc_facades.pop(PLACEHOLDER_CONTEXT, None)
            self._doc_profiles.pop(PLACEHOLDER_CONTEXT, None)

    def close_document_context(self, uid: str) -> None:
        """Libera a memória C++ e deleta a PaintEngineFacade do documento fechado."""
        self._doc_profiles.pop(uid, None)
        if uid in self._doc_facades:
            del self._doc_facades[uid]
            logger.info(f"[AladynBackend] PaintEngineFacade C++ liberada para doc '{uid}'.")

        if self._active_doc_uid == uid:
            self._active_doc_uid = None
            if self._doc_facades:
                first_uid = next(iter(self._doc_facades))
                self._facade = self._doc_facades[first_uid]
                self._active_doc_uid = first_uid
                self._color_profile_id = self._doc_profiles.get(first_uid, 0)
                self._width = self._facade.get_width()
                self._height = self._facade.get_height()
            else:
                self._facade = None
                self._color_profile_id = 0
