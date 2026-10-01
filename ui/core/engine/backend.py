"""
ui.core.engine.backend — Contrato Canônico EngineBackend + PointerEvent
========================================================================
Contrato abstrato universal (ARCcC Pilar 2.4 e Seção 15) que todo motor
(hoje: Aladyn C++; futuramente qualquer outro motor) implementa para integração
com a interface gráfica do Lumenia.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from ui.core.engine.telemetry_dto import TelemetrySnapshot
from ui.core.engine.display_image import DisplayImage
from ui.core.engine.engine_type import EngineType


# Maior lado de canvas que a casca assume enquanto NÃO há motor registrado (modo
# casca). Com motor, quem manda é `max_canvas_dimension()` dele; o número do motor
# mora em engine/core/canvas/CanvasLimits.hpp e `tests/test_canvas_limit_contract.py`
# confere que esta constante é igual a ele.
SHELL_MODE_MAX_CANVAS_DIMENSION = 16384


@dataclass(frozen=True)
class PointerEvent:
    """Ponto já convertido para o espaço do canvas (resultado de to_canvas)."""

    x: float
    y: float
    pressure: float
    timestamp: float


class EngineBackend(ABC):
    """
    Contrato canônico universal de um motor de pintura plugável no padrão ARCcC.

    Responsabilidades encapsuladas:
      - Superfície de renderização e viewport (init_renderer, update_view, resize, to_canvas);
      - Traço e mini-motores (start/paint/end stroke, parâmetros dinâmicos de pincel);
      - Camadas, grupos, modos de mesclagem e máscaras de recorte;
      - Seleção vetorial/raster e transformação livre afim;
      - Texturas procedurais (pincel, papel e canvas 3D);
      - Simetria, réguas e guias de perspectiva;
      - Telemetria de diagnóstico em tempo real;
      - Perfis de cor, prova de impressão e histórico (Undo/Redo).
    """

    name: str = "unnamed"

    # ── Disponibilidade & ciclo de vida ──────────────────────────────────

    @property
    def available(self) -> bool:
        """True se o binário/recursos do motor puderem ser carregados."""
        return True

    @property
    def load_error(self) -> str:
        """Por que o motor não carregou ("" quando carregou). A casca mostra isto ao usuário."""
        return ""

    def get_capabilities(self) -> Dict[str, Any]:
        """Recursos efetivos do backend, sem inferência pela presença da UI."""
        return {
            "native_engine": False,
            "render": False,
            "stroke": False,
            "brush_controls": False,
            "raster_document": False,
            "multi_document": False,
            "layers": False,
            "groups": False,
            "filters": False,
            "selection": False,
            "transform": False,
            "guides": False,
            "canvas_texture": False,
            "history": False,
            "scratch_history": False,
            "lod": False,
            "telemetry": False,
            "low_latency": False,
            "linear_gamma": False,
            "deep_color": False,
            "color_profiles": False,
            "color_profile_preview": False,
            "embedded_icc_profiles": False,
            "rgba16_document": False,
            "export_image": False,
            "document_pixel_format": "indisponível",
        }

    def supports_capability(self, capability: str) -> bool:
        """Consulta segura para widgets que precisam ocultar um controle indisponível."""
        return bool(self.get_capabilities().get(str(capability), False))

    @abstractmethod
    def init_renderer(self, hwnd: int, width: int, height: int, canvas_w: int, canvas_h: int) -> None:
        """Cria a superfície de renderização a partir do HWND nativo da janela."""

    @abstractmethod
    def resize(self, width: int, height: int) -> None:
        """Redimensiona a superfície de renderização (view reescale)."""

    @abstractmethod
    def render(self, pan_x: float, pan_y: float, zoom: float, rotation_rad: float) -> None:
        """Renderiza o quadro atual com a câmera informada."""

    def max_canvas_dimension(self) -> int:
        """Maior lado de canvas, em px, que o motor aceita. Diálogos e ações perguntam aqui."""
        return SHELL_MODE_MAX_CANVAS_DIMENSION

    def set_active_document_context(self, uid: Any, width: int, height: int) -> None:
        """Sincroniza o contexto de execução nativo com a aba/documento ativa.

        Levanta `EngineContextError` se o motor não conseguir criar o contexto
        (falta de memória); o contexto ativo antes da chamada continua ativo.
        """
        pass

    def close_document_context(self, uid: Any) -> None:
        """Libera toda a memória nativa e buffers associados a um documento fechado."""
        pass

    @abstractmethod
    def clear_canvas(self) -> None:
        """Limpa o canvas do documento ativo."""

    def get_qimage(self) -> Any:
        """Snapshot para viewport, válido após mutações e fechamento do documento."""
        return None

    def get_pixel_buffer(self) -> Optional[bytes]:
        """Snapshot RGBA imutável e independente do armazenamento do motor."""
        return None

    def get_display_pixel_buffer(self) -> Optional[bytes]:
        """Snapshot RGBA de exibição, válido após render/resize/fechamento."""
        return None

    def get_layer_pixel_buffer(self, layer_index: int) -> Optional[bytes]:
        """Retorna um snapshot RGBA independente para persistência."""
        return None

    def get_qimage_lod(self, zoom: float) -> Tuple[Optional[Any], float]: return (None, 1.0)

    def get_display_image(self, zoom: float, region: Any) -> Optional[DisplayImage]:
        """As imagens que a tela pinta: a `region` (QRect do canvas) em zoom de trabalho, ou o nível LOD afastado."""
        return None

    def get_dirty_tile_indices(self) -> List[Tuple[int, int]]: return []
    def clear_dirty_tiles(self) -> None: ...

    def get_document_generation(self) -> int:
        return 0

    def get_history_error(self) -> str:
        """Código de falha do último undo/redo; vazio quando não houve erro."""
        return ""

    # ── Traço (Stroke) & Fast-Path ────────────────────────────────────────

    @abstractmethod
    def start_stroke(self, x: float, y: float, pressure: float, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0) -> None:
        """Inicia um traço no canvas."""

    @abstractmethod
    def paint_stroke(self, x: float, y: float, pressure: float, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0) -> None:
        """Continua um traço em andamento."""

    @abstractmethod
    def end_stroke(self, x: Optional[float] = None, y: Optional[float] = None) -> Any:
        """Finaliza o traço atual (no ponto dado, ou no último ponto recebido).

        Retorna o retângulo sujo [x, y, w, h] no espaço do canvas, ou vazio.
        """

    def begin_stroke_raw(self, x: float, y: float, pressure: float = 1.0, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0) -> None: pass
    def update_stroke_raw(self, x: float, y: float, pressure: float = 1.0, timestamp: float = 0.0, tilt_x: float = 0.0, tilt_y: float = 0.0, twist: float = 0.0) -> List[float]: return [0.0, 0.0, 0.0]
    def end_stroke_raw(self) -> List[float]: return []

    # ── Parâmetros Básicos de Pincel ──────────────────────────────────────

    @abstractmethod
    def set_brush_color(self, r: float, g: float, b: float) -> None: ...

    @abstractmethod
    def set_brush_size(self, size: float) -> None: ...

    def set_brush_pressure(self, pressure: float) -> None: pass
    def set_brush_contrast(self, contrast: float) -> None: pass
    def set_brush_hardness(self, hardness: float) -> None: pass
    def set_brush_spacing(self, spacing: float) -> None: pass
    def set_brush_opacity(self, opacity: float) -> None: pass
    def set_stabilizer_weight(self, weight: float) -> None: pass
    def set_min_density_active(self, active: bool) -> None: pass
    def set_min_density_value(self, value: float) -> None: pass

    def set_brush_invert_height(self, invert: bool) -> None: ...
    def set_pressure_curve_power(self, power: float) -> None: ...
    def set_curve_control_points(self, curve_type: str, points: List[Tuple[float, float]], enabled: bool) -> None: ...

    # ── Mini-Motores & Perfis Dinâmicos ───────────────────────────────────

    def set_engine_type(self, engine_type_id: int) -> None: ...
    def get_active_engine_type(self) -> int: return EngineType.BRUSH

    def set_brush_param(self, group: str, param: str, value: Any) -> None: ...
    def get_brush_profile_dict(self) -> Dict[str, Any]: return {}
    def apply_brush_preset_dict(self, data: Dict[str, Any]) -> None: ...

    # ── Texturas de Pincel (Shape / Grão) ─────────────────────────────────

    def set_shape_texture(self, pixels: bytes, width: int, height: int) -> None:
        """Recebe RGBA compacto; a ponte converte para intensidade × alfa."""
    def set_heightmap_texture(self, pixels: bytes, width: int, height: int) -> None:
        """Recebe RGBA compacto; a ponte converte para intensidade × alfa."""
    def set_shape_preset(self, preset_id: int) -> None: ...
    def set_brush_height_preset(self, preset_id: int) -> None: ...
    def set_brush_grain_enabled(self, enabled: bool) -> None: ...
    def set_brush_grain_contrast(self, contrast: float) -> None: ...
    def set_brush_grain_scale(self, scale: float) -> None: ...

    # ── Papel & Textura do Canvas ─────────────────────────────────────────

    def set_canvas_paper_state(self, color: Any, visible: bool, preset_id: int = 0, enabled: bool = False, *, reset_texture: bool = True) -> None: ...
    def set_canvas_height_preset(self, preset_id: int) -> None: ...
    def set_canvas_grain_contrast(self, contrast: float) -> None: ...
    def set_canvas_grain_scale(self, scale: float) -> None: ...
    def set_canvas_grain_invert(self, invert: bool) -> None: ...

    # ── Buffers de Prévia (Shape / Altura / Traço) ─────────────────────────

    def render_brush_preview(self, width: int, height: int, brush_state: Optional[Dict[str, Any]] = None) -> Optional[bytes]: return None
    def get_shape_preview_buffer(self) -> Optional[bytes]: return None
    def get_shape_preview_dimensions(self) -> Tuple[int, int]: return (0, 0)
    def get_brush_height_preview_buffer(self) -> Optional[bytes]: return None
    def get_brush_height_preview_dimensions(self) -> Tuple[int, int]: return (0, 0)
    def get_canvas_height_preview_buffer(self) -> Optional[bytes]: return None
    def get_canvas_height_preview_dimensions(self) -> Tuple[int, int]: return (0, 0)

    # ── Camadas & Grupos ──────────────────────────────────────────────────

    def add_layer(self, name: str = "", insert_index: int = -1) -> int: return 0
    def add_group(self, name: str = "Novo Grupo", insert_index: int = -1) -> int: return 0
    def add_filter_layer(self, name: str, filter_type_id: int, insert_index: int = -1) -> int: return 0
    def set_filter_params(self, index: int, params: List[float]) -> None: ...
    def get_filter_params(self, index: int) -> List[float]: return []
    def get_filter_type(self, index: int) -> int: return 0
    def is_filter_layer(self, index: int) -> bool: return False
    def set_layer_document_uid(self, index: int, uid: int) -> bool: return False
    def remove_layer(self, index: int) -> bool: return False
    def duplicate_layer(self, index: int) -> int: return -1
    def select_layer(self, index: int) -> bool: return False
    def reorder_layer(self, from_index: int, to_index: int) -> bool: return False
    def reorder_layers(self, new_order: List[int]) -> bool: return False
    def set_layer_parents(self, parent_indices: List[int]) -> bool: return False
    def set_layer_name(self, index: int, name: str) -> None: ...
    def get_layer_name(self, index: int) -> str: return ""
    def get_layer_info(self, index: int) -> Dict[str, Any]: return {}
    def set_layer_opacity(self, index: int, opacity: float) -> None: ...
    def set_layer_blend_mode(self, index: int, blend_mode_id: int) -> None: ...
    def set_layer_visibility(self, index: int, visible: bool) -> None: ...
    def set_layer_lock(self, index: int, locked: bool) -> None: ...
    def set_layer_alpha_lock(self, index: int, locked: bool) -> None: ...
    def is_layer_alpha_locked(self, index: int) -> bool: return False
    def set_layer_clipping_mask(self, index: int, clipped: bool) -> None: ...
    def is_layer_clipping_mask(self, index: int) -> bool: return False
    def flatten_group(self, index: int) -> bool: return False
    def merge_layer_down(self, index: int) -> bool: return False
    def clear_layer(self, index: int) -> None: ...
    def get_active_layer_index(self) -> int: return 0
    def get_drawing_layer_count(self) -> int: return 1
    def is_group(self, index: int) -> bool: return False
    def get_layer_thumbnail_buffer(self, layer_index: int, thumb_w: int, thumb_h: int) -> Optional[bytes]: return None

    # ── Seleção & Transformação ───────────────────────────────────────────

    def select_rect(self, x: int, y: int, w: int, h: int, mode: int = 0, feather_px: int = 0, corner_radius_px: int = 0) -> bool: return False
    def select_ellipse(self, cx: int, cy: int, rx: int, ry: int, mode: int = 0, anti_aliasing: bool = True, feather_px: int = 0) -> bool: return False
    def select_polygon(self, flat_points: List[int], mode: int = 0, anti_aliasing: bool = True, feather_px: int = 0) -> bool: return False
    def magic_wand_select(self, seed_x: int, seed_y: int, tolerance: int = 20, contiguous: bool = True, expand_px: int = 0, anti_aliasing: bool = True, mode: int = 0, sample_all_layers: bool = True) -> bool: return False
    def clear_selection(self) -> None: ...
    def invert_selection(self) -> None: ...
    def select_all(self) -> None: ...
    def expand_selection(self, radius_px: int) -> bool: return False
    def contract_selection(self, radius_px: int) -> bool: return False
    def feather_selection(self, radius_px: int) -> bool: return False
    def has_selection(self) -> bool: return False
    def get_selection_mask_buffer(self) -> Optional[bytes]: return None
    def set_selection_mask_buffer(self, pixels: bytes) -> bool: return False
    def get_canvas_resource(self) -> Optional[Dict[str, Any]]: return None
    def set_canvas_resource(self, state: Dict[str, Any]) -> bool: return False
    def delete_selection_on_active_layer(self) -> bool: return False
    def fill_selection_on_active_layer(self, fill_color: Any) -> bool: return False
    def get_selection_bounds(self) -> List[int]: return [0, 0, 0, 0]
    def get_selection_contour_loops(self) -> List[List[int]]: return []
    def get_selection_mask_qimage(self) -> Optional[Any]: return None

    def begin_transform(self) -> bool: return False
    def is_transform_active(self) -> bool: return False
    def get_transform_source_bounds(self) -> List[float]: return [0.0, 0.0, 0.0, 0.0]
    def get_transform_pivot(self) -> List[float]: return [0.0, 0.0]
    def commit_transform(self, dx: float, dy: float, scale_x: float, scale_y: float, rotation_deg: float, pivot_x: float, pivot_y: float, flip_h: bool, flip_v: bool, interp_mode: int = 2) -> bool: return False
    def commit_transform_distort(self, corners: List[float], interp_mode: int = 2) -> bool: return False
    def cancel_transform(self) -> bool: return False
    def flip_active_layer(self, horizontal: bool) -> bool: return False
    def rotate_active_layer_90(self, clockwise: bool) -> bool: return False
    def get_transform_source_qimage(self) -> Optional[Any]: return None

    # ── Preenchimento (Flood Fill) & Colagem de Buffers ───────────────────

    def flood_fill(self, seed_x: int, seed_y: int, fill_color: Any, tolerance: int = 20, contiguous: bool = True, expand_px: int = 1, sample_all_layers: bool = True) -> bool: return False
    def fill_area(self, seed_x: int, seed_y: int, fill_color: Any, tolerance: int = 20, contiguous: bool = True, expand_px: int = 1, sample_all_layers: bool = True, *, sample_all: Optional[bool] = None) -> bool:
        if sample_all is not None: sample_all_layers = sample_all
        return self.flood_fill(seed_x, seed_y, fill_color, tolerance, contiguous, expand_px, sample_all_layers)
    def paste_rgba_buffer_on_active_layer(self, x: int, y: int, width: int, height: int, buffer: bytes, blend_mode_id: int = 0, opacity: float = 1.0) -> bool: return False

    # ── Simetria & Guias/Réguas ───────────────────────────────────────────

    def set_symmetry_config(self, mode: int, cx: float, cy: float, angle_rad: float, segments: int, stop_at_center: bool) -> None: ...
    def clear_symmetry(self) -> None: ...
    def set_guide_config(self, type_id: int, p0x: float, p0y: float, p1x: float, p1y: float, p2x: float, p2y: float, p3x: float, p3y: float, vp_ax: float, vp_ay: float, vp_bx: float, vp_by: float, vp_cx: float, vp_cy: float, cx: float, cy: float, fov: float, pitch: float, yaw: float, snap_radius: float) -> None: ...
    def clear_guide(self) -> None: ...
    def snap_point(self, raw_x: float, raw_y: float, last_x: float = 0.0, last_y: float = 0.0, has_last: bool = False) -> List[float]: return [raw_x, raw_y]

    # ── Curvilinear (6P fisheye) — Fase C2b ─────────────────────────────
    # API sem estado: quem chama (GeometryToolController) continua dono do
    # ciclo de vida do traço (curva travada, ponto de início). Defaults
    # seguros para backends sem suporte nativo (retornam "sem candidatas" /
    # "sem trava"), mesma convenção de snap_point acima.
    def set_curvilinear_guide_config(self, base_radius: float = 400.0, density: float = 30.0, show_v: bool = True, show_h: bool = True, show_d: bool = True, show_ground: bool = False, show_ceiling: bool = False, show_ground_verticals: bool = False, show_ceiling_verticals: bool = False, show_straight_verticals: bool = False, snap_mode: int = 0, snap_sensitivity: float = 3.0) -> None: ...
    def get_curvilinear_candidates(self, click_x: float, click_y: float) -> List[float]: return []
    def snap_curvilinear(self, raw_x: float, raw_y: float, start_x: float, start_y: float, candidates: List[float], locked_index: int = -1, is_stroking: bool = False, zoom: float = 1.0) -> List[float]: return [raw_x, raw_y, -1.0]

    # ── Perspectiva (1P/2P/3P/Isometric) ─ Fase C3.1 ─────────────────────────
    # Mesma convenção sem-estado do Curvilinear acima. Retorno de fallback:
    # ponto inalterado, sem trava.
    def snap_perspective(self, raw_x: float, raw_y: float, start_x: float, start_y: float, has_locked_dir: bool = False, locked_dir_x: float = 0.0, locked_dir_y: float = 0.0, zoom: float = 1.0) -> List[float]: return [raw_x, raw_y, 0.0, 0.0, 0.0]

    # ── Telemetria ────────────────────────────────────────────────────────

    def set_telemetry_enabled(self, enabled: bool) -> None: ...
    def is_telemetry_enabled(self) -> bool: return False
    def set_detailed_logging_enabled(self, detailed: bool) -> None: ...
    def is_detailed_logging_enabled(self) -> bool: return False
    def reset_telemetry(self) -> None: ...
    def get_telemetry_snapshot(self) -> TelemetrySnapshot: return TelemetrySnapshot()

    # ── Perfis de Cor & Amostragem ────────────────────────────────────────

    def set_color_profile(self, profile_id: int) -> None: ...
    def get_color_profile(self) -> int: return 0
    def get_color_profile_name(self, profile_id: int) -> str: return "Padrão (sRGB)"
    def get_available_color_profiles(self) -> List[Dict[str, Any]]: return []
    def register_custom_color_profile(self, source: Any, name: Optional[str] = None, profile_id: Optional[int] = None) -> int: return 0
    def set_soft_proofing(self, config: Any) -> None: ...
    def get_soft_proofing(self) -> Any: return None
    def get_active_profile_icc_bytes(self) -> Optional[bytes]: return None
    def transform_rgba_for_profile(self, pixels: bytes, profile_id: int) -> bytes:
        """Transforma uma prévia RGBA pelo mesmo pipeline que alimenta a exibição."""
        return bytes(pixels)
    # TODO: Fase 3 — Amostragem acelerada nativa no motor
    def pick_color_merged(self, x: int, y: int, sample_radius: int = 0) -> Tuple[int, int, int, int]: return (0, 0, 0, 0)
    # TODO: Fase 3 — Amostragem de camada acelerada nativa no motor
    def pick_color_layer(self, layer_index: int, x: int, y: int, sample_radius: int = 0) -> Tuple[int, int, int, int]: return (0, 0, 0, 0)

    # ── Pipeline de Renderização ─────────────────────────────────────────

    def set_render_options(self, low_latency: bool, linear_gamma: bool, deep_color: bool) -> None:
        """Aplica opções de latência, espaço de mistura e precisão no motor."""
        pass

    def get_active_document_context(self) -> Any:
        return None

    def get_render_options(self) -> Dict[str, bool]:
        """Retorna o estado efetivo das opções do pipeline."""
        return {"low_latency": True, "linear_gamma": False, "deep_color": False}

    def export_image(self, path: str) -> bool:
        """Exporta a composição exibida pelo backend para um arquivo de imagem."""
        return False

    # ── Histórico (Undo / Redo) ───────────────────────────────────────────

    def undo(self) -> bool: return False
    def begin_layer_transaction(self) -> bool: return False
    def apply_prepared_geometry(self, prepared_uid: str) -> bool: return False
    def commit_layer_transaction(self) -> int: return 0
    def cancel_layer_transaction(self) -> bool: return False
    def get_undo_step_id(self) -> int: return 0
    def get_redo_step_id(self) -> int: return 0
    def get_history_step_ids(self) -> list[int]: return []
    def redo(self) -> bool: return False
    def get_undo_count(self) -> int: return 0
    def get_redo_count(self) -> int: return 0
    def can_undo(self) -> bool: return False
    def can_redo(self) -> bool: return False
    def set_undo_memory_limit_mb(self, mb: int) -> None: ...
    def get_undo_memory_limit_mb(self) -> int: return 512
    def set_undo_max_steps(self, steps: int) -> None: ...
    def get_undo_max_steps(self) -> int: return 50
    def clear_history(self) -> bool: return False

    # ── Viewport / Câmera ────────────────────────────────────────────────

    @abstractmethod
    def update_view(self, zoom: float, pan_x: float, pan_y: float, rotation: float) -> None:
        """Atualiza a transformação de viewport do motor."""

    @abstractmethod
    def to_canvas(self, screen_x: float, screen_y: float, pressure: float, timestamp: float) -> PointerEvent:
        """Converte coordenadas de tela para o espaço do canvas."""

