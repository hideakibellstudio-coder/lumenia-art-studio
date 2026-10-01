"""AladynBackendBase — estado e serviços compartilhados por todos os mixins do AladynBackend.

Por que existe (2026-09-24): cada mixin (`AladynLayerMixin`, `AladynStrokeMixin`,
...) usava atributos criados por outro mixin ou pela classe final, sem saber
se eles existiriam. O resultado eram 40+ `hasattr(self, "_mark_document_dirty")`,
`hasattr(self, "_doc_facades")`, `getattr(self, "_undo_max_steps", 50)`... —
cada mixin tateando a si mesmo. Agora todos herdam desta base, que declara e
inicializa o estado compartilhado num lugar só; os mixins usam os atributos
diretamente.

Regra para quem mexer: atributo usado por mais de um mixin é declarado e
inicializado AQUI. Atributo usado por um mixin só pode continuar nele, mas é
criado no `_init_backend_state` (nunca preguiçosamente com hasattr).
"""
from __future__ import annotations

from typing import Any, Optional

from ui.core.color.proofing import SoftProofConfig


class AladynBackendBase:
    # ── Binário e facade ativa ────────────────────────────────────────────
    _native: Any                       # módulo aladyn_engine_native, ou None (modo casca)
    _load_error: str                   # por que o motor não carregou; "" quando carregou
    _facade: Any                       # PaintEngineFacade do documento ativo, ou None
    _width: int
    _height: int

    # ── MDI: uma facade por documento ─────────────────────────────────────
    _doc_facades: dict[str, Any]
    _active_doc_uid: Optional[str]
    # Perfil de pincel carregado de uma facade para a próxima ao trocar de aba
    # (inclui os parâmetros avançados que só o motor conhece).
    _last_brush_preset: dict[str, Any]

    # ── Histórico ─────────────────────────────────────────────────────────
    _action_stack: list[tuple[str, int]]
    _redo_stack: list[tuple[str, int]]
    _undo_memory_limit_mb: int
    _undo_max_steps: int
    _is_filling: bool
    _last_x: Optional[float]
    _last_y: Optional[float]

    # ── Render e cor ──────────────────────────────────────────────────────
    _render_options: dict[str, bool]
    _view_state: tuple[float, float, float, float]
    _soft_proof_config: SoftProofConfig
    _color_profile_id: int
    # Perfil de cor de cada contexto de documento: o de `_color_profile_id` é
    # o do contexto ativo e volta daqui na troca de documento.
    _doc_profiles: dict[str, int]
    last_telemetry: tuple[float, float, float]

    def _init_backend_state(self) -> None:
        """Inicializa todo o estado compartilhado com os valores padrão."""
        self._native = None
        self._load_error = ""
        self._facade = None
        self._width = 800
        self._height = 600

        self._doc_facades = {}
        self._active_doc_uid = None
        self._last_brush_preset = {}

        self._action_stack = []
        self._redo_stack = []
        self._undo_memory_limit_mb = 512
        self._undo_max_steps = 50
        self._is_filling = False
        # Último ponto do traço (end_stroke sem coordenadas usa este).
        self._last_x: Optional[float] = None
        self._last_y: Optional[float] = None

        self._render_options = {"low_latency": True, "linear_gamma": False, "deep_color": False}
        self._view_state = (0.0, 0.0, 1.0, 0.0)
        self._soft_proof_config = SoftProofConfig()
        self._color_profile_id = 0
        self._doc_profiles = {}
        self.last_telemetry = (0.0, 0.0, 0.0)

    def _mark_document_dirty(self, reason: str) -> None:
        """Avisa que o documento ativo mudou (o DocumentManager escuta pelo EngineRegistry)."""
        from ui.core.engine.registry import EngineRegistry

        EngineRegistry.instance().notify_document_modified(self._active_doc_uid, reason)
